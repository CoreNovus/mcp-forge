"""mcp-forge provider interfaces and built-in implementations.

Top-level exports include infrastructure providers (any server may need)
and common AI capability examples (LLM, Embedding)::

    from mcp_forge_core.providers import BaseCacheProvider, InMemoryCache
    from mcp_forge_core.providers import BaseLLMProvider, LLMMessage

Additional capability providers are available via direct import
when your server needs them::

    from mcp_forge_core.providers.vision import BaseVisionProvider
    from mcp_forge_core.providers.transcribe import BaseTranscribeProvider
"""

# ── Infrastructure providers (any MCP server may need these) ─────────

from .cache import BaseCacheProvider
from .session import BaseSessionProvider, Session
from .telemetry import BaseTelemetryProvider

# ── In-memory implementations (for dev/testing) ─────────────────────

from .in_memory import InMemoryCache, InMemorySession, InMemoryTelemetry

# ── Common AI capability examples ───────────────────────────────────
#    Kept at top level as extension pattern references.
#    Shows how to define a capability provider ABC.

from .llm import BaseLLMProvider, LLMMessage, LLMResponse
from .embedding import BaseEmbeddingProvider

# ── Adapter utility ─────────────────────────────────────────────────

from .adapt import adapt

__all__ = [
    # Infrastructure
    "BaseCacheProvider",
    "BaseSessionProvider",
    "Session",
    "BaseTelemetryProvider",
    # In-memory
    "InMemoryCache",
    "InMemorySession",
    "InMemoryTelemetry",
    # AI capabilities (extension examples)
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "BaseEmbeddingProvider",
    # Utility
    "adapt",
]

# Note: BaseVisionProvider, BaseTranscribeProvider, and their data classes
# are available via direct import:
#   from mcp_forge_core.providers.vision import BaseVisionProvider
#   from mcp_forge_core.providers.transcribe import BaseTranscribeProvider
