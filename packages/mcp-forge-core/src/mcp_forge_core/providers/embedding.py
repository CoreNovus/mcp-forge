"""Embedding provider base class for mcp-forge.

Defines the interface for text embedding generation.
Subclass BaseEmbeddingProvider and implement embed() and dimension.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Base class for embedding backends.

    Subclass and implement :meth:`embed` and the :attr:`dimension` property
    to integrate any embedding model.

    Example::

        class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
            @property
            def dimension(self) -> int:
                return 1536

            async def embed(self, texts):
                response = await openai_client.embeddings.create(input=texts, ...)
                return [item.embedding for item in response.data]
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The dimensionality of the embedding vectors produced by this provider."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Convenience method to embed a single text.

        Calls :meth:`embed` with a single-item list. Override if your backend
        has a more efficient single-text API.
        """
        results = await self.embed([text])
        return results[0]
