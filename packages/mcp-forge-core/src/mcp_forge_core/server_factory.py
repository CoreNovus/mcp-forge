"""MCP server factory — the main entry point for creating and running MCP servers.

Handles both HTTP (FastMCP) and stdio modes transparently, with built-in
health checks and provider injection via closures.

**Minimal example:**

    from mcp_forge_core import create_mcp_app

    mcp = create_mcp_app("my-server", "A helpful server")

    @mcp.tool()
    async def hello(name: str) -> str:
        return f"Hello, {name}!"

    if __name__ == "__main__":
        run_server(mcp)

**With providers:**

    from mcp_forge_core import create_mcp_app, run_server, ToolContext
    from mcp_forge_core.providers import InMemoryCache, InMemoryTelemetry

    ctx = ToolContext(cache=InMemoryCache(), telemetry=InMemoryTelemetry())

    def register_tools(mcp):
        @mcp.tool()
        async def search(query: str) -> dict:
            async with ctx.measured("search"):
                return await ctx.cached(ctx.hash_key(query), do_search)

    mcp = create_mcp_app("search-mcp", "Search engine", [register_tools])
    run_server(mcp)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def create_mcp_app(
    server_name: str,
    description: str,
    tool_modules: list[Callable[[FastMCP], None]] | None = None,
    *,
    providers: dict[str, Any] | None = None,
    log_level: str | None = None,
) -> FastMCP:
    """Create a configured FastMCP server instance.

    Tools are registered via callback functions that receive the FastMCP instance
    and can close over any providers they need (the closure pattern).

    Args:
        server_name: Name of the MCP server (shown to clients).
        description: Server description / instructions for the LLM.
        tool_modules: List of callables that register tools on the FastMCP instance.
        providers: Optional dict of provider instances stored on ``mcp.providers``.
        log_level: Logging level. Defaults to ``MCP_LOG_LEVEL`` env var or "INFO".

    Returns:
        A configured FastMCP instance ready to run.
    """
    level = log_level or os.environ.get("MCP_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    mcp = FastMCP(server_name, instructions=description)
    mcp.providers = providers or {}  # type: ignore[attr-defined]

    if tool_modules:
        for register_fn in tool_modules:
            register_fn(mcp)

    return mcp


def run_server(
    mcp: FastMCP,
    *,
    host: str | None = None,
    port: int | None = None,
    mode: str | None = None,
    stateless: bool = True,
) -> None:
    """Run an MCP server in the appropriate mode.

    Reads ``MCP_SERVER_MODE`` env var to determine HTTP vs stdio.
    Eliminates the boilerplate of writing mode-switching code in every server.

    Args:
        mcp: The FastMCP instance from :func:`create_mcp_app`.
        host: HTTP host (default: ``MCP_SERVER_HOST`` or "0.0.0.0").
        port: HTTP port (default: ``MCP_SERVER_PORT`` or 8000).
        mode: "http" or "stdio". Default reads ``MCP_SERVER_MODE`` or "http".
        stateless: If True, HTTP mode uses stateless transport (for Lambda).

    Example::

        mcp = create_mcp_app("my-server", "Description")
        run_server(mcp)               # reads MCP_SERVER_MODE
        run_server(mcp, mode="stdio")  # force stdio
    """
    server_mode = mode or os.environ.get("MCP_SERVER_MODE", "http")

    if server_mode == "stdio":
        logger.info("Starting %s in stdio mode", mcp.name)
        mcp.run(transport="stdio")
    else:
        actual_host = host or os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
        actual_port = port or int(os.environ.get("MCP_SERVER_PORT", "8000"))

        logger.info("Starting %s on %s:%d (stateless=%s)", mcp.name, actual_host, actual_port, stateless)

        app = _get_http_app(mcp, stateless=stateless)

        import uvicorn

        uvicorn.run(app, host=actual_host, port=actual_port)


def get_http_app(
    mcp: FastMCP,
    *,
    stateless: bool = True,
) -> Any:
    """Get the ASGI app from a FastMCP instance (for custom deployment).

    Useful when you need the Starlette app for Lambda handlers,
    custom middleware, or integration with other ASGI frameworks.

    Args:
        mcp: The FastMCP instance.
        stateless: If True, uses stateless HTTP transport.

    Returns:
        A Starlette ASGI application.

    Example::

        mcp = create_mcp_app("my-server", "Description")
        app = get_http_app(mcp)  # pass to Lambda handler, gunicorn, etc.
    """
    return _get_http_app(mcp, stateless=stateless)


def _get_http_app(mcp: FastMCP, *, stateless: bool = True) -> Any:
    """Resolve the correct HTTP app method across MCP SDK versions.

    The MCP SDK uses ``streamable_http_app()`` while the standalone
    fastmcp package uses ``http_app()``. This helper handles both.
    """
    # MCP SDK >= 1.x: streamable_http_app()
    if hasattr(mcp, "streamable_http_app"):
        return mcp.streamable_http_app()

    # Standalone fastmcp package: http_app()
    if hasattr(mcp, "http_app"):
        return mcp.http_app(stateless_http=stateless, json_response=True)

    # Fallback: SSE app
    if hasattr(mcp, "sse_app"):
        return mcp.sse_app()

    raise AttributeError(
        f"FastMCP instance has no HTTP app method. "
        f"Available: {[m for m in dir(mcp) if 'app' in m.lower()]}"
    )
