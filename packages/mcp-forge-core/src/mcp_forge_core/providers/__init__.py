"""mcp-forge provider interfaces and built-in implementations.

This module re-exports all provider base classes, data classes, and
in-memory implementations for convenient imports::

    from mcp_forge_core.providers import BaseLLMProvider, LLMMessage, LLMResponse
    from mcp_forge_core.providers import InMemoryCache, InMemorySession
    from mcp_forge_core.providers import adapt
"""

# Base classes (ABC)
from .llm import BaseLLMProvider, LLMMessage, LLMResponse
from .vision import BaseVisionProvider, VisionExtractionResult
from .embedding import BaseEmbeddingProvider
from .cache import BaseCacheProvider
from .session import BaseSessionProvider, Session
from .telemetry import BaseTelemetryProvider
from .transcribe import BaseTranscribeProvider, TranscriptionResult

# In-memory implementations (for dev/testing)
from .in_memory import InMemoryCache, InMemorySession, InMemoryTelemetry

# Adapter utility
from .adapt import adapt

__all__ = [
    # LLM
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    # Vision
    "BaseVisionProvider",
    "VisionExtractionResult",
    # Embedding
    "BaseEmbeddingProvider",
    # Cache
    "BaseCacheProvider",
    # Session
    "BaseSessionProvider",
    "Session",
    # Telemetry
    "BaseTelemetryProvider",
    # Transcribe
    "BaseTranscribeProvider",
    "TranscriptionResult",
    # In-memory
    "InMemoryCache",
    "InMemorySession",
    "InMemoryTelemetry",
    # Utility
    "adapt",
]
