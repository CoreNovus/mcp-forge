"""Tests for DynamoDBCacheProvider with moto."""

from __future__ import annotations

from mcp_forge_aws import DynamoDBCacheProvider


class TestDynamoDBCacheProvider:
    async def test_put_and_get(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        await cache.put("k1", {"value": 42})
        result = await cache.get("k1")
        assert result == {"value": 42}

    async def test_get_missing_returns_none(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        assert await cache.get("nonexistent") is None

    async def test_delete_existing(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        await cache.put("k1", {"v": 1})
        assert await cache.delete("k1") is True
        assert await cache.get("k1") is None

    async def test_delete_nonexistent(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        # DynamoDB delete_item is idempotent — does not error on missing keys
        result = await cache.delete("nope")
        assert isinstance(result, bool)

    async def test_overwrite(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        await cache.put("k1", {"v": 1})
        await cache.put("k1", {"v": 2})
        assert (await cache.get("k1")) == {"v": 2}

    async def test_unicode_data(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        await cache.put("u", {"name": "日本語テスト"})
        result = await cache.get("u")
        assert result["name"] == "日本語テスト"

    async def test_nested_data(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        data = {"nested": {"deep": {"value": [1, 2, 3]}}}
        await cache.put("n", data)
        assert (await cache.get("n")) == data

    async def test_get_or_default_inherited(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        result = await cache.get_or_default("missing", {"default": True})
        assert result == {"default": True}

    def test_repr(self):
        cache = DynamoDBCacheProvider(table_name="my-table", region="eu-west-1")
        assert "my-table" in repr(cache)

    async def test_large_payload(self, cache_table):
        cache = DynamoDBCacheProvider(table_name="test-cache", region="us-east-1")
        large = {"items": list(range(500))}
        await cache.put("big", large)
        assert (await cache.get("big")) == large
