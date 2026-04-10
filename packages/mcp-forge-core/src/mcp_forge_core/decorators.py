"""Composable tool decorators for common MCP patterns.

These decorators solve the three most repetitive patterns in MCP tool code:

1. **@measured** — auto-time every invocation and emit telemetry
2. **@cached_tool** — cache-aside with automatic key hashing
3. **@compacted** — auto-store large results, return compact ref_id

They are designed to compose cleanly::

    @mcp.tool()
    @measured(telemetry)
    @cached_tool(cache, ttl=3600)
    @compacted(store, summary_fn=lambda r: f"Found {len(r['items'])} items")
    async def search_jobs(query: str) -> dict:
        return await llm.invoke(...)

Each decorator is independent — use one, two, or all three.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .providers.cache import BaseCacheProvider
    from .providers.telemetry import BaseTelemetryProvider
    from .tool_data_store import ToolDataStore

logger = logging.getLogger(__name__)


def measured(telemetry: BaseTelemetryProvider) -> Callable:
    """Decorator that auto-times tool execution and emits telemetry.

    Uses the decorated function's ``__name__`` as the tool name.

    Example::

        @mcp.tool()
        @measured(telemetry)
        async def parse_document(content: str) -> dict:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            success = False
            try:
                result = await fn(*args, **kwargs)
                success = True
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                try:
                    await telemetry.emit_tool_invocation(fn.__name__, success, duration_ms)
                except Exception:
                    logger.warning("Telemetry emission failed for %s", fn.__name__)

        return wrapper

    return decorator


def cached_tool(
    cache: BaseCacheProvider,
    *,
    ttl: int | None = None,
    key_params: list[str] | None = None,
) -> Callable:
    """Decorator that adds cache-aside to a tool function.

    Automatically hashes the function arguments to build a cache key.
    On cache hit, returns the cached result with ``_cache_hit: True``.

    Args:
        cache: Cache provider.
        ttl: Optional TTL in seconds.
        key_params: If set, only these parameter names are used for the cache key.
                    Useful when some params (like ``ref_id``) shouldn't affect caching.

    Example::

        @mcp.tool()
        @cached_tool(cache, ttl=3600, key_params=["query", "language"])
        async def analyze(query: str, language: str = "en") -> dict:
            ...  # only called on cache miss
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from specified params or all kwargs
            if key_params:
                key_data = {k: kwargs.get(k) for k in key_params}
            else:
                key_data = kwargs
            raw = json.dumps(
                {"_fn": fn.__name__, **key_data},
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
            cache_key = hashlib.sha256(raw.encode()).hexdigest()

            # Check cache
            hit = await cache.get(cache_key)
            if hit is not None:
                if isinstance(hit, dict):
                    return {**hit, "_cache_hit": True}
                return hit

            # Compute and store
            result = await fn(*args, **kwargs)
            await cache.put(cache_key, result, ttl_seconds=ttl)
            return result

        return wrapper

    return decorator


def compacted(
    store: ToolDataStore,
    *,
    summary_fn: Callable[[dict], str] | None = None,
) -> Callable:
    """Decorator that auto-stores large results and returns a compact ref_id.

    When the tool returns a dict, it is stored in the ToolDataStore and
    replaced with ``{"ref_id": ..., "summary": ...}``.

    Args:
        store: ToolDataStore for result storage.
        summary_fn: Optional function that takes the result dict and returns
                     a summary string. Defaults to a generic message.

    Example::

        @mcp.tool()
        @compacted(store, summary_fn=lambda r: f"Profile: {r.get('name')}")
        async def extract_profile(text: str) -> dict:
            return {"name": "Alice", "skills": [...]}
            # → actually returns {"ref_id": "td_...", "summary": "Profile: Alice"}
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await fn(*args, **kwargs)

            if not isinstance(result, dict):
                return result

            ref_id = await store.store(result)
            summary = summary_fn(result) if summary_fn else f"Stored result ({ref_id})"
            return {"ref_id": ref_id, "summary": summary}

        return wrapper

    return decorator
