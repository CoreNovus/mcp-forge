"""Amazon Bedrock Embedding provider for mcp-forge.

Async text embedding via Amazon Titan Embeddings V2.
Reuses a single aioboto3 Session for connection pooling.

Example::

    embedder = BedrockEmbeddingProvider()
    vectors = await embedder.embed(["hello world", "foo bar"])
    single = await embedder.embed_one("hello world")
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aioboto3

from mcp_forge_core.providers.embedding import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class BedrockEmbeddingProvider(BaseEmbeddingProvider):
    """Amazon Titan Embeddings V2 provider.

    Args:
        model_id: Bedrock embedding model ID.
        region: AWS region.
        endpoint_url: Optional endpoint (for LocalStack).
        dimensions: Embedding vector dimensions (default: 1024).
        session: Optional shared aioboto3.Session.
    """

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        dimensions: int = 1024,
        session: aioboto3.Session | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._endpoint_url = endpoint_url
        self._dimensions = dimensions
        self._session = session or aioboto3.Session()

    @property
    def dimension(self) -> int:
        return self._dimensions

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, reusing a single Bedrock client connection.

        More efficient than calling embed_one() in a loop because the
        HTTP connection pool is shared across all calls.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        async with self._session.client(
            "bedrock-runtime", **self._client_kwargs()
        ) as bedrock:
            for text in texts:
                response = await bedrock.invoke_model(
                    modelId=self._model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps({
                        "inputText": text,
                        "dimensions": self._dimensions,
                        "normalize": True,
                    }),
                )
                body = json.loads(await response["body"].read())
                results.append(body["embedding"])

        return results

    def __repr__(self) -> str:
        return f"<BedrockEmbeddingProvider model={self._model_id!r} dim={self._dimensions}>"
