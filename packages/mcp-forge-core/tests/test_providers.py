"""Tests for provider ABC conformance, InMemory implementations, and adapt utility."""

from __future__ import annotations

import asyncio

import pytest

from mcp_forge_core.providers import (
    BaseCacheProvider,
    BaseEmbeddingProvider,
    BaseLLMProvider,
    BaseSessionProvider,
    BaseTelemetryProvider,
    InMemoryCache,
    InMemorySession,
    InMemoryTelemetry,
    Session,
    adapt,
)
from mcp_forge_core.providers.vision import BaseVisionProvider
from mcp_forge_core.providers.transcribe import BaseTranscribeProvider


# ── ABC Enforcement ──────────────────────────────────────────────────


class TestABCEnforcement:
    """Verify that missing abstract methods raise TypeError at instantiation."""

    def test_cache_missing_delete_raises(self):
        class BadCache(BaseCacheProvider):
            async def get(self, key):
                return None

            async def put(self, key, data, ttl_seconds=None):
                pass

        with pytest.raises(TypeError, match="delete"):
            BadCache()

    def test_session_missing_methods_raises(self):
        class BadSession(BaseSessionProvider):
            async def get(self, session_id):
                return None

        with pytest.raises(TypeError, match="save|delete"):
            BadSession()

    def test_telemetry_only_needs_emit_metric(self):
        """emit_tool_invocation has a default, so only emit_metric is required."""

        class MinimalTelemetry(BaseTelemetryProvider):
            async def emit_metric(self, name, value, unit="Count", dimensions=None):
                pass

        t = MinimalTelemetry()
        assert t is not None

    def test_embedding_needs_dimension_and_embed(self):
        class BadEmbed(BaseEmbeddingProvider):
            async def embed(self, texts):
                return []

        with pytest.raises(TypeError):
            BadEmbed()

    def test_llm_missing_invoke_raises(self):
        with pytest.raises(TypeError):

            class BadLLM(BaseLLMProvider):
                pass

            BadLLM()

    def test_vision_missing_methods_raises(self):
        class PartialVision(BaseVisionProvider):
            async def extract_structured(self, *a, **kw):
                pass

            # missing get_supported_types

        with pytest.raises(TypeError):
            PartialVision()

    def test_transcribe_missing_transcribe_raises(self):
        with pytest.raises(TypeError):

            class BadTranscribe(BaseTranscribeProvider):
                pass

            BadTranscribe()


class TestInMemoryProviderConformance:
    def test_cache_is_subclass(self):
        assert issubclass(InMemoryCache, BaseCacheProvider)
        assert isinstance(InMemoryCache(), BaseCacheProvider)

    def test_session_is_subclass(self):
        assert issubclass(InMemorySession, BaseSessionProvider)

    def test_telemetry_is_subclass(self):
        assert issubclass(InMemoryTelemetry, BaseTelemetryProvider)


# ── InMemoryCache ────────────────────────────────────────────────────


class TestInMemoryCache:
    async def test_put_and_get(self, cache: InMemoryCache):
        await cache.put("k", {"v": 42})
        assert await cache.get("k") == {"v": 42}

    async def test_get_missing_returns_none(self, cache: InMemoryCache):
        assert await cache.get("nonexistent") is None

    async def test_delete_existing(self, cache: InMemoryCache):
        await cache.put("k", {"v": 1})
        assert await cache.delete("k") is True
        assert await cache.get("k") is None

    async def test_delete_nonexistent(self, cache: InMemoryCache):
        assert await cache.delete("nope") is False

    async def test_ttl_expired(self, cache: InMemoryCache):
        await cache.put("k", {"v": 1}, ttl_seconds=-1)
        assert await cache.get("k") is None

    async def test_ttl_not_expired(self, cache: InMemoryCache):
        await cache.put("k", {"v": 1}, ttl_seconds=3600)
        assert await cache.get("k") == {"v": 1}

    async def test_no_ttl_persists(self, cache: InMemoryCache):
        await cache.put("k", {"v": 1}, ttl_seconds=None)
        assert await cache.get("k") == {"v": 1}

    async def test_overwrite_existing_key(self, cache: InMemoryCache):
        await cache.put("k", {"v": 1})
        await cache.put("k", {"v": 2})
        assert await cache.get("k") == {"v": 2}

    async def test_get_or_default_miss(self, cache: InMemoryCache):
        result = await cache.get_or_default("missing", {"default": True})
        assert result == {"default": True}

    async def test_get_or_default_hit(self, cache: InMemoryCache):
        await cache.put("k", {"found": True})
        result = await cache.get_or_default("k", {"default": True})
        assert result == {"found": True}

    async def test_clear(self, cache: InMemoryCache):
        await cache.put("a", {"v": 1})
        await cache.put("b", {"v": 2})
        cache.clear()
        assert len(cache) == 0
        assert await cache.get("a") is None

    async def test_len_reflects_entries(self, cache: InMemoryCache):
        assert len(cache) == 0
        await cache.put("a", {"v": 1})
        assert len(cache) == 1
        await cache.put("b", {"v": 2})
        assert len(cache) == 2
        await cache.delete("a")
        assert len(cache) == 1

    async def test_unicode_keys_and_values(self, cache: InMemoryCache):
        await cache.put("鍵", {"值": "日本語テスト"})
        result = await cache.get("鍵")
        assert result == {"值": "日本語テスト"}

    async def test_empty_string_key(self, cache: InMemoryCache):
        await cache.put("", {"v": 1})
        assert await cache.get("") == {"v": 1}

    async def test_large_value(self, cache: InMemoryCache):
        large = {"items": list(range(10000))}
        await cache.put("big", large)
        assert await cache.get("big") == large


# ── InMemorySession ──────────────────────────────────────────────────


class TestInMemorySession:
    async def test_save_and_get(self, session_store: InMemorySession):
        session = Session(session_id="s1", context={"user": "alice"})
        await session_store.save(session)
        result = await session_store.get("s1")
        assert result is not None
        assert result.context == {"user": "alice"}

    async def test_get_missing(self, session_store: InMemorySession):
        assert await session_store.get("nope") is None

    async def test_delete_existing(self, session_store: InMemorySession):
        await session_store.save(Session(session_id="s1"))
        assert await session_store.delete("s1") is True
        assert await session_store.get("s1") is None

    async def test_delete_nonexistent(self, session_store: InMemorySession):
        assert await session_store.delete("nope") is False

    async def test_save_overwrites(self, session_store: InMemorySession):
        await session_store.save(Session(session_id="s1", context={"v": 1}))
        await session_store.save(Session(session_id="s1", context={"v": 2}))
        result = await session_store.get("s1")
        assert result.context == {"v": 2}

    async def test_get_or_create_new(self, session_store: InMemorySession):
        session = await session_store.get_or_create()
        assert session.session_id is not None
        assert await session_store.get(session.session_id) is not None

    async def test_get_or_create_existing(self, session_store: InMemorySession):
        original = Session(session_id="s1", context={"existing": True})
        await session_store.save(original)
        result = await session_store.get_or_create("s1")
        assert result.context == {"existing": True}

    async def test_get_or_create_with_explicit_id(self, session_store: InMemorySession):
        """get_or_create with a new ID should create and persist."""
        session = await session_store.get_or_create("explicit-id")
        assert session.session_id == "explicit-id"
        assert await session_store.get("explicit-id") is not None

    async def test_session_updated_at_changes_on_save(self, session_store: InMemorySession):
        session = Session(session_id="s1")
        original_ts = session.updated_at
        await asyncio.sleep(0.01)
        await session_store.save(session)
        assert session.updated_at != original_ts

    async def test_tool_history_mutable(self, session_store: InMemorySession):
        session = Session(session_id="s1")
        session.tool_history.append({"tool": "parse", "ts": "2024-01-01"})
        await session_store.save(session)
        loaded = await session_store.get("s1")
        assert len(loaded.tool_history) == 1


# ── InMemoryTelemetry ────────────────────────────────────────────────


class TestInMemoryTelemetry:
    async def test_emit_metric(self, telemetry: InMemoryTelemetry):
        await telemetry.emit_metric("test.metric", 42.0, "Count")
        assert len(telemetry) == 1
        assert telemetry.metrics[0]["name"] == "test.metric"

    async def test_emit_tool_invocation_default(self, telemetry: InMemoryTelemetry):
        await telemetry.emit_tool_invocation("my_tool", True, 150.0)
        assert len(telemetry) == 2  # count + duration

    async def test_measure_tool_success(self, telemetry: InMemoryTelemetry):
        async with telemetry.measure_tool("test") as ctx:
            ctx["success"] = True
        assert any(
            m["dimensions"]["success"] == "true" for m in telemetry.metrics
        )

    async def test_measure_tool_failure(self, telemetry: InMemoryTelemetry):
        with pytest.raises(ValueError):
            async with telemetry.measure_tool("test"):
                raise ValueError("fail")
        assert any(
            m["dimensions"]["success"] == "false" for m in telemetry.metrics
        )

    async def test_measure_tool_duration_positive(self, telemetry: InMemoryTelemetry):
        async with telemetry.measure_tool("timed") as ctx:
            await asyncio.sleep(0.01)
            ctx["success"] = True
        duration = next(m for m in telemetry.metrics if "duration" in m["name"])
        assert duration["value"] > 0

    async def test_clear(self, telemetry: InMemoryTelemetry):
        await telemetry.emit_metric("m", 1.0)
        telemetry.clear()
        assert len(telemetry) == 0

    async def test_dimensions_default_empty(self, telemetry: InMemoryTelemetry):
        await telemetry.emit_metric("m", 1.0)
        assert telemetry.metrics[0]["dimensions"] == {}


# ── adapt() ──────────────────────────────────────────────────────────


class TestAdapt:
    def test_adapt_valid_object(self):
        class FakeCache:
            async def get(self, key):
                return None

            async def put(self, key, data, ttl_seconds=None):
                pass

            async def delete(self, key):
                return False

        adapted = adapt(FakeCache(), BaseCacheProvider)
        assert adapted is not None

    def test_adapt_missing_method_raises_with_details(self):
        class Incomplete:
            async def get(self, key):
                return None

        with pytest.raises(TypeError, match="Cannot adapt.*missing"):
            adapt(Incomplete(), BaseCacheProvider)

    def test_adapt_non_callable_raises(self):
        class BadAttr:
            get = "not a function"
            put = "not a function"
            delete = "not a function"

        with pytest.raises(TypeError, match="not callable"):
            adapt(BadAttr(), BaseCacheProvider)

    def test_adapt_returns_same_object(self):
        class FullCache:
            async def get(self, key):
                return None

            async def put(self, key, data, ttl_seconds=None):
                pass

            async def delete(self, key):
                return False

        obj = FullCache()
        assert adapt(obj, BaseCacheProvider) is obj
