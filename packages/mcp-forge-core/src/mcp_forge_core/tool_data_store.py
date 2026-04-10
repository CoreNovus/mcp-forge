"""Tool data store for compacting large tool results.

When an MCP tool produces a large result, store it in the cache and return
a compact reference ID instead. The client can retrieve the full data later.

Uses BaseCacheProvider for storage — inject InMemoryCache for dev,
DynamoDBCacheProvider for production.

Example::

    from mcp_forge_core.tool_data_store import ToolDataStore
    from mcp_forge_core.providers import InMemoryCache

    store = ToolDataStore(cache=InMemoryCache())

    # Store a large result
    ref_id = await store.store({"large": "data", "rows": [...]})

    # Retrieve later
    data = await store.retrieve(ref_id)
"""

from __future__ import annotations

import uuid
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .providers.cache import BaseCacheProvider


class ToolDataStore:
    """Stores and retrieves tool result data via a cache provider.

    Args:
        cache: A BaseCacheProvider implementation for storage.
        prefix: Key prefix for stored data (avoids collisions with other cache users).
        default_ttl: Default TTL in seconds for stored data. None means no expiry.
    """

    def __init__(
        self,
        cache: BaseCacheProvider,
        prefix: str = "td_",
        default_ttl: int | None = None,
    ) -> None:
        self._cache = cache
        self._prefix = prefix
        self._default_ttl = default_ttl

    async def store(self, data: dict[str, Any], ttl_seconds: int | None = None) -> str:
        """Store data and return a reference ID.

        Args:
            data: The dict to store.
            ttl_seconds: Optional TTL override. Uses default_ttl if None.

        Returns:
            A unique reference ID that can be used to retrieve the data.
        """
        ref_id = f"{self._prefix}{uuid.uuid4().hex[:12]}"
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        await self._cache.put(ref_id, data, ttl_seconds=ttl)
        return ref_id

    async def retrieve(self, ref_id: str) -> dict[str, Any] | None:
        """Retrieve stored data by reference ID.

        Args:
            ref_id: The reference ID returned by :meth:`store`.

        Returns:
            The stored dict, or None if not found or expired.
        """
        return await self._cache.get(ref_id)

    async def delete(self, ref_id: str) -> bool:
        """Delete stored data by reference ID.

        Args:
            ref_id: The reference ID returned by :meth:`store`.

        Returns:
            True if the data existed and was deleted.
        """
        return await self._cache.delete(ref_id)
