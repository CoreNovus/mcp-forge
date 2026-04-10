"""In-memory provider implementations for local development and testing.

These providers require zero external dependencies — just ``pip install mcp-forge-core``
and start building. They also serve as reference implementations that AI coding assistants
can use as examples when helping you write custom providers.

Example::

    from mcp_forge_core.providers import InMemoryCache, InMemorySession, InMemoryTelemetry

    cache = InMemoryCache()
    session_store = InMemorySession()
    telemetry = InMemoryTelemetry()
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from .cache import BaseCacheProvider
from .session import BaseSessionProvider, Session
from .telemetry import BaseTelemetryProvider

logger = logging.getLogger(__name__)


class InMemoryCache(BaseCacheProvider):
    """Dict-based cache for local development and testing.

    Supports TTL via expiry timestamps. Not thread-safe — suitable for
    single-process dev servers and unit tests.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        data, expires_at = entry
        if expires_at is not None and time.time() > expires_at:
            del self._store[key]
            return None
        return data

    async def put(self, key: str, data: Any, ttl_seconds: int | None = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (data, expires_at)

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove all entries. Useful in test teardown."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class InMemorySession(BaseSessionProvider):
    """Dict-based session store for local development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    async def get(self, session_id: str) -> Session | None:
        return self._store.get(session_id)

    async def save(self, session: Session) -> None:
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self._store[session.session_id] = session

    async def delete(self, session_id: str) -> bool:
        return self._store.pop(session_id, None) is not None

    def clear(self) -> None:
        """Remove all sessions. Useful in test teardown."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class InMemoryTelemetry(BaseTelemetryProvider):
    """Telemetry provider that logs metrics and stores them in memory.

    Useful for local development (metrics appear in logs) and testing
    (inspect ``metrics`` list to verify tool invocations).
    """

    def __init__(self) -> None:
        self.metrics: list[dict] = []

    async def emit_metric(
        self,
        name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
    ) -> None:
        record = {
            "name": name,
            "value": value,
            "unit": unit,
            "dimensions": dimensions or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.metrics.append(record)
        logger.debug("metric: %s=%s %s %s", name, value, unit, dimensions or "")

    def clear(self) -> None:
        """Remove all recorded metrics. Useful in test teardown."""
        self.metrics.clear()

    def __len__(self) -> int:
        return len(self.metrics)
