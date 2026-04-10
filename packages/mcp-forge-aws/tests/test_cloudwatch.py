"""Tests for CloudWatchTelemetryProvider with moto."""

from __future__ import annotations

import pytest

from mcp_forge_aws import CloudWatchTelemetryProvider


class TestCloudWatchTelemetryProvider:
    async def test_emit_metric(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test/MCP", server_name="test", region="us-east-1")
        await t.emit_metric("test.count", 1.0, "Count")

    async def test_emit_with_dimensions(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test/MCP", server_name="test", region="us-east-1")
        await t.emit_metric("tool.invocation", 1.0, "Count", {"tool": "parse"})

    async def test_emit_tool_invocation_default(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test/MCP", server_name="test", region="us-east-1")
        await t.emit_tool_invocation("my_tool", True, 150.0)

    async def test_measure_tool_success(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test/MCP", server_name="test", region="us-east-1")
        async with t.measure_tool("measured") as ctx:
            ctx["success"] = True

    async def test_measure_tool_failure(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test/MCP", server_name="test", region="us-east-1")
        with pytest.raises(ValueError):
            async with t.measure_tool("failing"):
                raise ValueError("boom")

    def test_repr(self):
        t = CloudWatchTelemetryProvider(namespace="MyNS", server_name="my-srv")
        assert "MyNS" in repr(t)

    def test_lazy_client(self):
        t = CloudWatchTelemetryProvider()
        assert t._client is None

    async def test_client_created_after_emit(self, moto_env):
        t = CloudWatchTelemetryProvider(namespace="Test", server_name="t", region="us-east-1")
        assert t._client is None
        await t.emit_metric("trigger", 1.0)
        assert t._client is not None
