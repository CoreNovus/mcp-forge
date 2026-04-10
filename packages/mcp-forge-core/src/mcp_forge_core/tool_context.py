"""Tool execution context — the central convenience for writing MCP tools.

ToolContext bundles providers, telemetry, caching, and compaction into a single
object that tools receive. It eliminates the boilerplate found in every tool:

**Before (typical MCP tool without ToolContext):**

    @mcp.tool()
    async def analyze(query: str) -> dict:
        cache_key = hashlib.sha256(query.encode()).hexdigest()
        cached = await cache.get(cache_key)
        if cached:
            return cached
        start = time.perf_counter()
        try:
            result = await llm.invoke(PROMPT, query)
            duration = (time.perf_counter() - start) * 1000
            telemetry.emit_tool_invocation("analyze", True, duration)
        except Exception:
            duration = (time.perf_counter() - start) * 1000
            telemetry.emit_tool_invocation("analyze", False, duration)
            raise
        await cache.put(cache_key, result)
        if store:
            ref_id = await store.store(result)
            return {"ref_id": ref_id, "summary": "..."}
        return result

**After (with ToolContext):**

    @mcp.tool()
    async def analyze(query: str) -> dict:
        async with ctx.measured("analyze"):
            result = await ctx.cached(
                key=ctx.hash_key(query),
                fn=lambda: llm.invoke(PROMPT, query),
            )
            return await ctx.compacted(result, summary=f"Found {len(result['items'])} results")
"""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .providers.cache import BaseCacheProvider
    from .providers.session import BaseSessionProvider
    from .providers.telemetry import BaseTelemetryProvider
    from .tool_data_store import ToolDataStore

logger = logging.getLogger(__name__)


class ToolContext:
    """Execution context for MCP tools — bundles providers and common patterns.

    Created once per server and shared across all tools. Provides three
    patterns that cover 90% of tool boilerplate:

    - :meth:`measured` — auto-time and record tool invocations
    - :meth:`cached` — cache-aside with one line
    - :meth:`compacted` — store large results, return compact ref_id

    Args:
        cache: Optional cache provider for caching.
        session: Optional session provider.
        telemetry: Optional telemetry provider for metrics.
        store: Optional ToolDataStore for result compaction.
        extra: Arbitrary extra providers (e.g. ``llm=my_llm``).

    Example::

        ctx = ToolContext(
            cache=InMemoryCache(),
            telemetry=InMemoryTelemetry(),
            store=ToolDataStore(cache=InMemoryCache()),
        )

        # In a tool function:
        result = await ctx.cached("query:abc123", compute_result)
        return await ctx.compacted(result, summary="Found 10 items")
    """

    __slots__ = ("cache", "session", "telemetry", "store", "_extra")

    def __init__(
        self,
        *,
        cache: BaseCacheProvider | None = None,
        session: BaseSessionProvider | None = None,
        telemetry: BaseTelemetryProvider | None = None,
        store: ToolDataStore | None = None,
        **extra: Any,
    ) -> None:
        self.cache = cache
        self.session = session
        self.telemetry = telemetry
        self.store = store
        self._extra = extra

    def __getattr__(self, name: str) -> Any:
        """Access extra providers by name: ``ctx.llm``, ``ctx.vision``, etc."""
        try:
            return self._extra[name]
        except KeyError:
            raise AttributeError(
                f"ToolContext has no provider '{name}'. "
                f"Available: {', '.join(self._extra) or '(none)'}"
            ) from None

    def __repr__(self) -> str:
        parts = []
        for name in ("cache", "session", "telemetry", "store"):
            if getattr(self, name) is not None:
                parts.append(name)
        parts.extend(self._extra)
        return f"<ToolContext [{', '.join(parts)}]>"

    # ── measured: auto-timing ────────────────────────────────────────

    def measured(self, tool_name: str):
        """Async context manager that auto-times a tool invocation.

        Delegates to ``telemetry.measure_tool()``. If no telemetry provider
        is configured, returns a no-op context.

        Example::

            async with ctx.measured("my_tool") as m:
                result = await do_work()
                m["success"] = True
        """
        if self.telemetry is not None:
            return self.telemetry.measure_tool(tool_name)
        return _noop_measure()

    # ── cached: cache-aside pattern ──────────────────────────────────

    async def cached(
        self,
        key: str,
        fn: Callable[[], Awaitable[dict[str, Any]]],
        *,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Cache-aside pattern in one call.

        Checks cache first, calls ``fn()`` on miss, stores the result.
        If no cache provider is configured, always calls ``fn()``.

        Args:
            key: Cache key.
            fn: Async callable that produces the value on cache miss.
            ttl_seconds: Optional TTL override.

        Returns:
            The cached or freshly computed dict.

        Example::

            result = await ctx.cached(
                key=ctx.hash_key(raw_text),
                fn=lambda: llm.invoke(prompt, messages),
                ttl_seconds=3600,
            )
        """
        if self.cache is not None:
            hit = await self.cache.get(key)
            if hit is not None:
                return {**hit, "_cache_hit": True}

        result = await fn()

        if self.cache is not None:
            await self.cache.put(key, result, ttl_seconds=ttl_seconds)

        return result

    # ── compacted: result compaction ─────────────────────────────────

    async def compacted(
        self,
        data: dict[str, Any],
        *,
        summary: str = "",
    ) -> dict[str, Any]:
        """Store a large result and return a compact reference.

        If a ToolDataStore is configured, stores the full data and returns
        ``{"ref_id": ..., "summary": ...}``. Otherwise returns data as-is.

        Args:
            data: The full result dict.
            summary: Human-readable summary for the LLM.

        Returns:
            Compact ``{ref_id, summary}`` dict, or the original data.

        Example::

            return await ctx.compacted(
                result_data,
                summary=f"Processed {len(result_data.get('items', []))} items",
            )
        """
        if self.store is None:
            return data
        ref_id = await self.store.store(data)
        return {"ref_id": ref_id, "summary": summary or f"Stored ({ref_id})"}

    # ── resolve: fetch compacted data back ───────────────────────────

    async def resolve(self, ref_id: str) -> dict[str, Any] | None:
        """Resolve a ref_id back to its full data.

        Useful when one tool needs the output of a previous tool
        that was compacted via :meth:`compacted`.

        Args:
            ref_id: Reference ID from a previous compacted result.

        Returns:
            The full data dict, or None if not found/expired.

        Raises:
            RuntimeError: If no ToolDataStore is configured.
        """
        if self.store is None:
            raise RuntimeError("Cannot resolve ref_id: no ToolDataStore configured")
        return await self.store.retrieve(ref_id)

    # ── hash_key: deterministic cache key ────────────────────────────

    @staticmethod
    def hash_key(*parts: Any) -> str:
        """Compute a deterministic SHA-256 cache key from arbitrary inputs.

        Serializes all parts to a canonical JSON string, then hashes.
        Useful for building cache keys from tool arguments.

        Example::

            key = ctx.hash_key(raw_text, extraction_type, language)
        """
        payload = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


# ── No-op context manager when telemetry is not configured ───────────


@asynccontextmanager
async def _noop_measure() -> AsyncIterator[dict[str, Any]]:
    yield {"success": False}
