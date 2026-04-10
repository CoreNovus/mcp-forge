"""Tests for server_factory — create_mcp_app, get_http_app."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_forge_core.server_factory import create_mcp_app, get_http_app


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

    def test_multiple_tool_modules(self):
        registered = []

        def register_a(mcp):
            registered.append("a")

        def register_b(mcp):
            registered.append("b")

        create_mcp_app("test", "Test", [register_a, register_b])
        assert registered == ["a", "b"]

    def test_stores_providers_dict(self):
        providers = {"cache": "fake_cache", "llm": "fake_llm"}
        mcp = create_mcp_app("test-server", "Test", providers=providers)
        assert mcp.providers == providers  # type: ignore[attr-defined]

    def test_default_empty_providers(self):
        mcp = create_mcp_app("test-server", "Test")
        assert mcp.providers == {}  # type: ignore[attr-defined]

    def test_no_tool_modules(self):
        mcp = create_mcp_app("test", "Test", tool_modules=None)
        assert isinstance(mcp, FastMCP)


class TestGetHttpApp:
    def test_returns_asgi_app(self):
        mcp = create_mcp_app("test", "Test")
        app = get_http_app(mcp)
        assert app is not None
        # Starlette apps have a __call__ method
        assert callable(app)

    def test_stateless_mode(self):
        mcp = create_mcp_app("test", "Test")
        app = get_http_app(mcp, stateless=True)
        assert app is not None

    def test_stateful_mode(self):
        mcp = create_mcp_app("test", "Test")
        app = get_http_app(mcp, stateless=False)
        assert app is not None
