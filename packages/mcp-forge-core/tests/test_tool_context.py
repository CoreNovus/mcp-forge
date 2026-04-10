"""Tests for ToolContext — boundary conditions, concurrency, and error paths."""

from __future__ import annotations

import asyncio

import pytest

from mcp_forge_core.tool_context import ToolContext
from mcp_forge_core.tool_data_store import ToolDataStore
from mcp_forge_core.providers import InMemoryCache, InMemorySession, InMemoryTelemetry


@pytest.fixture
def ctx():
    cache = InMemoryCache()
    return ToolContext(
        cache=cache,
        session=InMemorySession(),
        telemetry=InMemoryTelemetry(),
        store=ToolDataStore(cache=InMemoryCache()),
    )


@pytest.fixture
def ctx_minimal():
    """Context with no providers — tests graceful degradation."""
    return ToolContext()


# ── cached ───────────────────────────────────────────────────────────


class TestToolContextCached:
    async def test_cache_miss_calls_fn(self, ctx: ToolContext):
        called = False

        async def compute():
            nonlocal called
            called = True
            return {"answer": 42}

        result = await ctx.cached("key1", compute)
        assert called
        assert result == {"answer": 42}

    async def test_cache_hit_skips_fn(self, ctx: ToolContext):
        await ctx.cached("key1", lambda: _async_dict({"answer": 42}))

        call_count = 0

        async def compute():
            nonlocal call_count
            call_count += 1
            return {"answer": 99}

        result = await ctx.cached("key1", compute)
        assert call_count == 0
        assert result["answer"] == 42
        assert result["_cache_hit"] is True

    async def test_no_cache_always_calls_fn(self, ctx_minimal: ToolContext):
        result = await ctx_minimal.cached("key1", lambda: _async_dict({"v": 1}))
        assert result == {"v": 1}
        assert "_cache_hit" not in result

    async def test_fn_exception_propagates_and_does_not_cache(self, ctx: ToolContext):
        """If the compute fn raises, the exception propagates and nothing is cached."""

        async def failing():
            raise ValueError("compute failed")

        with pytest.raises(ValueError, match="compute failed"):
            await ctx.cached("failing_key", failing)

        # Key should NOT be in cache
        assert await ctx.cache.get("failing_key") is None

    async def test_ttl_respected(self, ctx: ToolContext):
        """Expired entries should trigger a re-compute."""
        await ctx.cached("exp_key", lambda: _async_dict({"v": 1}), ttl_seconds=-1)

        call_count = 0

        async def recompute():
            nonlocal call_count
            call_count += 1
            return {"v": 2}

        result = await ctx.cached("exp_key", recompute)
        assert call_count == 1
        assert result == {"v": 2}

    async def test_concurrent_cache_miss(self, ctx: ToolContext):
        """Multiple concurrent calls to the same uncached key should all succeed."""
        call_count = 0

        async def slow_compute():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"v": call_count}

        results = await asyncio.gather(
            ctx.cached("race_key", slow_compute),
            ctx.cached("race_key", slow_compute),
            ctx.cached("race_key", slow_compute),
        )
        # All should return valid dicts (first writer wins, others may recompute)
        assert all(isinstance(r, dict) for r in results)

    async def test_empty_dict_is_cached(self, ctx: ToolContext):
        """An empty dict {} is a valid result and should be cached (not treated as miss)."""
        call_count = 0

        async def returns_empty():
            nonlocal call_count
            call_count += 1
            return {}

        await ctx.cached("empty_key", returns_empty)
        await ctx.cached("empty_key", returns_empty)
        # Empty dict is truthy for cache check (get returns {} which is not None)
        # So second call should be a hit
        assert call_count == 1


# ── compacted ────────────────────────────────────────────────────────


class TestToolContextCompacted:
    async def test_compacted_returns_ref_id(self, ctx: ToolContext):
        result = await ctx.compacted({"big": "data"}, summary="Stored big data")
        assert "ref_id" in result
        assert result["summary"] == "Stored big data"

    async def test_compacted_without_store_returns_raw(self, ctx_minimal: ToolContext):
        data = {"big": "data"}
        result = await ctx_minimal.compacted(data, summary="test")
        assert result is data  # exact same object, no copy

    async def test_compacted_empty_summary_generates_default(self, ctx: ToolContext):
        result = await ctx.compacted({"v": 1})
        assert result["ref_id"] in result["summary"]  # default includes ref_id

    async def test_compacted_preserves_data_integrity(self, ctx: ToolContext):
        """Full round-trip: compact → resolve → verify identical."""
        original = {
            "nested": {"deep": [1, 2, 3]},
            "unicode": "日本語テスト",
            "empty_list": [],
            "null_val": None,
        }
        compacted = await ctx.compacted(original, summary="test")
        resolved = await ctx.resolve(compacted["ref_id"])
        assert resolved == original


# ── resolve ──────────────────────────────────────────────────────────


class TestToolContextResolve:
    async def test_resolve_stored_data(self, ctx: ToolContext):
        original = {"name": "Alice", "skills": ["python"]}
        compacted = await ctx.compacted(original, summary="Profile")
        resolved = await ctx.resolve(compacted["ref_id"])
        assert resolved == original

    async def test_resolve_without_store_raises(self, ctx_minimal: ToolContext):
        with pytest.raises(RuntimeError, match="no ToolDataStore"):
            await ctx_minimal.resolve("td_abc123")

    async def test_resolve_expired_returns_none(self, ctx: ToolContext):
        """Resolving a ref_id that was never stored returns None."""
        result = await ctx.resolve("td_nonexistent")
        assert result is None


# ── measured ─────────────────────────────────────────────────────────


class TestToolContextMeasured:
    async def test_measured_emits_telemetry(self, ctx: ToolContext):
        async with ctx.measured("test_tool") as m:
            m["success"] = True

        assert len(ctx.telemetry) >= 2  # invocation + duration

    async def test_measured_without_telemetry_is_noop(self, ctx_minimal: ToolContext):
        async with ctx_minimal.measured("test_tool") as m:
            m["success"] = True

    async def test_measured_records_failure_on_exception(self, ctx: ToolContext):
        with pytest.raises(ValueError):
            async with ctx.measured("failing_tool"):
                raise ValueError("boom")

        # Should have recorded failure
        invocation = ctx.telemetry.metrics[0]
        assert invocation["dimensions"]["success"] == "false"

    async def test_measured_duration_is_positive(self, ctx: ToolContext):
        async with ctx.measured("timed_tool") as m:
            await asyncio.sleep(0.01)
            m["success"] = True

        duration_metric = next(
            m for m in ctx.telemetry.metrics if m["name"] == "tool.duration_ms"
        )
        assert duration_metric["value"] > 0

    async def test_telemetry_failure_does_not_propagate(self, ctx: ToolContext):
        """If telemetry emission itself fails, the tool should still succeed."""

        class BrokenTelemetry(InMemoryTelemetry):
            async def emit_metric(self, *args, **kwargs):
                raise ConnectionError("telemetry down")

        ctx_broken = ToolContext(telemetry=BrokenTelemetry())

        # Should NOT raise despite broken telemetry
        async with ctx_broken.measured("safe_tool") as m:
            m["success"] = True


# ── hash_key ─────────────────────────────────────────────────────────


class TestToolContextHashKey:
    def test_deterministic(self):
        k1 = ToolContext.hash_key("hello", 42, {"nested": True})
        k2 = ToolContext.hash_key("hello", 42, {"nested": True})
        assert k1 == k2

    def test_different_inputs_different_keys(self):
        k1 = ToolContext.hash_key("hello")
        k2 = ToolContext.hash_key("world")
        assert k1 != k2

    def test_order_insensitive_for_dicts(self):
        """Dict keys should be sorted, so order doesn't matter."""
        k1 = ToolContext.hash_key({"a": 1, "b": 2})
        k2 = ToolContext.hash_key({"b": 2, "a": 1})
        assert k1 == k2

    def test_handles_non_json_types(self):
        """Non-JSON-serializable types should use default=str fallback."""
        from datetime import datetime

        k = ToolContext.hash_key(datetime(2024, 1, 1))
        assert isinstance(k, str) and len(k) == 64  # SHA-256 hex

    def test_empty_produces_valid_hash(self):
        k = ToolContext.hash_key()
        assert isinstance(k, str) and len(k) == 64


# ── extra providers ──────────────────────────────────────────────────


class TestToolContextExtraProviders:
    def test_access_extra_provider(self):
        ctx = ToolContext(llm="fake_llm", vision="fake_vision")
        assert ctx.llm == "fake_llm"
        assert ctx.vision == "fake_vision"

    def test_missing_extra_raises_helpful_error(self):
        ctx = ToolContext(cache=InMemoryCache(), llm="x")
        with pytest.raises(AttributeError, match="no provider 'db'") as exc_info:
            _ = ctx.db
        # Error message should list available extras
        assert "llm" in str(exc_info.value)

    def test_repr_shows_configured_providers(self):
        ctx = ToolContext(cache=InMemoryCache(), llm="x", vision="y")
        r = repr(ctx)
        assert "cache" in r
        assert "llm" in r
        assert "vision" in r

    def test_repr_minimal(self):
        ctx = ToolContext()
        assert "ToolContext" in repr(ctx)


# ── Helper ───────────────────────────────────────────────────────────


async def _async_dict(d: dict) -> dict:
    return d
