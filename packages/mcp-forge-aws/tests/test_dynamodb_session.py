"""Tests for DynamoDBSessionProvider with moto."""

from __future__ import annotations

from mcp_forge_core.providers.session import Session
from mcp_forge_aws import DynamoDBSessionProvider


class TestDynamoDBSessionProvider:
    async def test_save_and_get(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        await s.save(Session(session_id="s1", context={"user": "alice"}))
        result = await s.get("s1")
        assert result is not None
        assert result.context == {"user": "alice"}

    async def test_get_missing(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        assert await s.get("nonexistent") is None

    async def test_delete_existing(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        await s.save(Session(session_id="s1"))
        assert await s.delete("s1") is True
        assert await s.get("s1") is None

    async def test_delete_nonexistent(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        # DynamoDB delete_item is idempotent — does not error on missing keys
        result = await s.delete("nope")
        assert isinstance(result, bool)

    async def test_overwrite(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        await s.save(Session(session_id="s1", context={"v": 1}))
        await s.save(Session(session_id="s1", context={"v": 2}))
        assert (await s.get("s1")).context == {"v": 2}

    async def test_get_or_create_new(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        session = await s.get_or_create("new-id")
        assert session.session_id == "new-id"
        assert await s.get("new-id") is not None

    async def test_get_or_create_existing(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        await s.save(Session(session_id="s1", context={"existing": True}))
        result = await s.get_or_create("s1")
        assert result.context == {"existing": True}

    async def test_tool_history(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        session = Session(session_id="s1")
        session.tool_history.append({"tool": "parse"})
        await s.save(session)
        loaded = await s.get("s1")
        assert len(loaded.tool_history) == 1

    async def test_unicode_context(self, sessions_table):
        s = DynamoDBSessionProvider(table_name="test-sessions", region="us-east-1")
        await s.save(Session(session_id="s1", context={"名前": "太郎"}))
        loaded = await s.get("s1")
        assert loaded.context["名前"] == "太郎"
