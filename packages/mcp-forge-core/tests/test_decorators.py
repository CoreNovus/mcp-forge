"""Tests for composable tool decorators — edge cases, composition, and error paths."""

from __future__ import annotations

import pytest

from mcp_forge_core.decorators import measured, cached_tool, compacted
from mcp_forge_core.providers import InMemoryCache, InMemoryTelemetry
from mcp_forge_core.tool_data_store import ToolDataStore


# ── @measured ────────────────────────────────────────────────────────


class TestMeasured:
    async def test_emits_on_success(self):
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def my_tool(x: int) -> dict:
            return {"result": x * 2}

        result = await my_tool(x=5)
        assert result == {"result": 10}
        assert len(telemetry) >= 2
        assert telemetry.metrics[0]["dimensions"]["success"] == "true"

    async def test_emits_on_failure(self):
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def failing() -> dict:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing()

        assert telemetry.metrics[0]["dimensions"]["success"] == "false"

    async def test_preserves_function_name(self):
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def specific_name() -> dict:
            return {}

        await specific_name()
        assert telemetry.metrics[0]["dimensions"]["tool_name"] == "specific_name"

    async def test_preserves_docstring(self):
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def documented() -> dict:
            """This is the docstring."""
            return {}

        assert documented.__doc__ == "This is the docstring."

    async def test_duration_recorded(self):
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def slow():
            import asyncio
            await asyncio.sleep(0.01)
            return {}

        await slow()
        duration = next(m for m in telemetry.metrics if m["name"] == "tool.duration_ms")
        assert duration["value"] > 0


# ── @cached_tool ─────────────────────────────────────────────────────


class TestCachedTool:
    async def test_caches_result(self):
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache)
        async def expensive(query: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"data": query.upper()}

        r1 = await expensive(query="hello")
        r2 = await expensive(query="hello")

        assert call_count == 1
        assert r1 == {"data": "HELLO"}
        assert r2["_cache_hit"] is True

    async def test_different_args_different_cache(self):
        cache = InMemoryCache()

        @cached_tool(cache)
        async def search(query: str) -> dict:
            return {"q": query}

        r1 = await search(query="a")
        r2 = await search(query="b")
        assert "_cache_hit" not in r1
        assert "_cache_hit" not in r2
        assert r1["q"] == "a"
        assert r2["q"] == "b"

    async def test_key_params_selective(self):
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache, key_params=["query"])
        async def search(query: str, debug: bool = False) -> dict:
            nonlocal call_count
            call_count += 1
            return {"q": query}

        await search(query="hello", debug=False)
        await search(query="hello", debug=True)
        assert call_count == 1  # debug param ignored in key

    async def test_ttl_expiry(self):
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache, ttl=-1)  # immediate expiry
        async def expiring(x: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"x": x}

        await expiring(x="a")
        await expiring(x="a")
        assert call_count == 2  # both calls computed because TTL expired

    async def test_non_dict_result_is_cached(self):
        """Non-dict return values are also cached (cache accepts Any)."""
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache)
        async def returns_string(x: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result: {x}"

        r1 = await returns_string(x="a")
        r2 = await returns_string(x="a")
        assert r1 == "result: a"
        assert r2 == "result: a"
        assert call_count == 1  # second call served from cache

    async def test_exception_not_cached(self):
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache)
        async def flaky(x: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first call fails")
            return {"x": x}

        with pytest.raises(ValueError):
            await flaky(x="a")

        result = await flaky(x="a")
        assert result == {"x": "a"}
        assert call_count == 2  # second call recomputed

    async def test_empty_kwargs_produce_stable_key(self):
        """Calling with no kwargs should produce a consistent cache key."""
        cache = InMemoryCache()
        call_count = 0

        @cached_tool(cache)
        async def no_args() -> dict:
            nonlocal call_count
            call_count += 1
            return {"v": 1}

        await no_args()
        await no_args()
        assert call_count == 1


# ── @compacted ───────────────────────────────────────────────────────


class TestCompacted:
    async def test_stores_and_returns_ref(self):
        store = ToolDataStore(cache=InMemoryCache())

        @compacted(store)
        async def big_result() -> dict:
            return {"items": list(range(1000))}

        result = await big_result()
        assert "ref_id" in result
        data = await store.retrieve(result["ref_id"])
        assert len(data["items"]) == 1000

    async def test_custom_summary_fn(self):
        store = ToolDataStore(cache=InMemoryCache())

        @compacted(store, summary_fn=lambda r: f"Got {r['count']} items")
        async def counted() -> dict:
            return {"count": 42}

        result = await counted()
        assert result["summary"] == "Got 42 items"

    async def test_non_dict_passes_through(self):
        """Non-dict results should pass through without compaction."""
        store = ToolDataStore(cache=InMemoryCache())

        @compacted(store)
        async def returns_string() -> str:
            return "plain text"

        result = await returns_string()
        assert result == "plain text"

    async def test_exception_propagates(self):
        store = ToolDataStore(cache=InMemoryCache())

        @compacted(store)
        async def fails() -> dict:
            raise RuntimeError("broken")

        with pytest.raises(RuntimeError, match="broken"):
            await fails()

    async def test_unique_ref_ids(self):
        """Each call should produce a unique ref_id."""
        store = ToolDataStore(cache=InMemoryCache())

        @compacted(store)
        async def make_data() -> dict:
            return {"v": 1}

        r1 = await make_data()
        r2 = await make_data()
        assert r1["ref_id"] != r2["ref_id"]


# ── Composition ──────────────────────────────────────────────────────


class TestComposedDecorators:
    async def test_measured_then_cached_then_compacted(self):
        """Full stack: telemetry → cache → compaction."""
        cache = InMemoryCache()
        telemetry = InMemoryTelemetry()
        store = ToolDataStore(cache=InMemoryCache())

        @measured(telemetry)
        @cached_tool(cache, ttl=60)
        @compacted(store, summary_fn=lambda r: f"Name: {r['name']}")
        async def extract(text: str) -> dict:
            return {"name": "Alice", "skills": ["python"]}

        r1 = await extract(text="resume")
        assert "ref_id" in r1
        assert r1["summary"] == "Name: Alice"
        assert len(telemetry) >= 2

        # Second call — cache hit returns the compacted {ref_id, summary}
        telemetry.clear()
        r2 = await extract(text="resume")
        assert r2["_cache_hit"] is True
        assert len(telemetry) >= 2  # measured still fires

    async def test_measured_catches_exception_from_inner(self):
        """measured should record failure even when inner decorator raises."""
        telemetry = InMemoryTelemetry()

        @measured(telemetry)
        async def boom() -> dict:
            raise ConnectionError("network down")

        with pytest.raises(ConnectionError):
            await boom()

        assert telemetry.metrics[0]["dimensions"]["success"] == "false"
