"""Tests for server_factory.create_mcp_app."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_forge_core.server_factory import create_mcp_app


class TestCreateMCPApp:
    def test_returns_fastmcp_instance(self):
        mcp = create_mcp_app("test-server", "A test server")
        assert isinstance(mcp, FastMCP)

    def test_registers_tools_via_callback(self):
        tool_registered = False

        def register(mcp: FastMCP):
            nonlocal tool_registered

            @mcp.tool()
            def hello(name: str) -> str:
                return f"Hello, {name}!"

            tool_registered = True

        create_mcp_app("test-server", "A test server", [register])
        assert tool_registered

    def test_stores_providers_dict(self):
        providers = {"cache": "fake_cache", "llm": "fake_llm"}
        mcp = create_mcp_app("test-server", "Test", providers=providers)
        assert mcp.providers == providers  # type: ignore[attr-defined]

    def test_default_empty_providers(self):
        mcp = create_mcp_app("test-server", "Test")
        assert mcp.providers == {}  # type: ignore[attr-defined]
