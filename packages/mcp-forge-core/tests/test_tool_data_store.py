"""Tests for ToolDataStore."""

from __future__ import annotations

from mcp_forge_core.tool_data_store import ToolDataStore
from mcp_forge_core.providers import InMemoryCache


class TestToolDataStore:
    async def test_store_and_retrieve(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache)
        data = {"key": "value", "count": 42}
        ref_id = await store.store(data)
        assert ref_id.startswith("td_")
        result = await store.retrieve(ref_id)
        assert result == data

    async def test_retrieve_nonexistent(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache)
        result = await store.retrieve("td_nonexistent")
        assert result is None

    async def test_delete(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache)
        ref_id = await store.store({"v": 1})
        assert await store.delete(ref_id) is True
        assert await store.retrieve(ref_id) is None

    async def test_custom_prefix(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache, prefix="custom_")
        ref_id = await store.store({"v": 1})
        assert ref_id.startswith("custom_")

    async def test_default_ttl(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache, default_ttl=-1)
        ref_id = await store.store({"v": 1})
        # TTL is negative so it's already expired
        result = await store.retrieve(ref_id)
        assert result is None

    async def test_store_ttl_override(self, cache: InMemoryCache):
        store = ToolDataStore(cache=cache, default_ttl=3600)
        # Override with immediate expiry
        ref_id = await store.store({"v": 1}, ttl_seconds=-1)
        result = await store.retrieve(ref_id)
        assert result is None
