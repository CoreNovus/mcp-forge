"""mcp-forge-core — Framework for building MCP servers with swappable providers.

Quick start::

    from mcp_forge_core import create_mcp_app, run_server

    mcp = create_mcp_app("my-server", "A helpful MCP server")

    @mcp.tool()
    async def hello(name: str) -> str:
        return f"Hello, {name}!"

    run_server(mcp)

With providers::

    from mcp_forge_core import create_mcp_app, run_server, ToolContext
    from mcp_forge_core.providers import InMemoryCache, InMemoryTelemetry

    ctx = ToolContext(cache=InMemoryCache(), telemetry=InMemoryTelemetry())

Provider interfaces (subclass these)::

    from mcp_forge_core.providers import (
        BaseLLMProvider,
        BaseCacheProvider,
        BaseSessionProvider,
        BaseTelemetryProvider,
        ...
    )

Composable decorators::

    from mcp_forge_core.decorators import measured, cached_tool, compacted
"""

from .config import MCPServerConfig, get_mcp_config
from .server_factory import create_mcp_app, run_server, get_http_app
from .circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
from .retry import RetryConfig, retry, with_retry
from .models import MCPError, MCPToolResult, MCPProgressEvent
from .tool_data_store import ToolDataStore
from .tool_context import ToolContext
from .similarity import cosine_similarity, semantic_match, ScoredItem

__version__ = "0.1.0"

__all__ = [
    # Config
    "MCPServerConfig",
    "get_mcp_config",
    # Server factory
    "create_mcp_app",
    "run_server",
    "get_http_app",
    # Context
    "ToolContext",
    # Resilience
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "RetryConfig",
    "retry",
    "with_retry",
    # Models
    "MCPError",
    "MCPToolResult",
    "MCPProgressEvent",
    # Tool data
    "ToolDataStore",
    # Similarity
    "cosine_similarity",
    "semantic_match",
    "ScoredItem",
]
