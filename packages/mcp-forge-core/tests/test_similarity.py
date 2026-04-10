"""Tests for cosine similarity and semantic matching."""

from __future__ import annotations

import pytest

from mcp_forge_core.similarity import cosine_similarity, semantic_match
from mcp_forge_core.providers import BaseEmbeddingProvider


class FakeEmbedding(BaseEmbeddingProvider):
    """Fake embedding provider that returns predictable vectors."""

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = {
            "invoice processing": [1.0, 0.0, 0.0],
            "handle invoices": [0.9, 0.1, 0.0],
            "send emails": [0.0, 1.0, 0.0],
            "process payments": [0.5, 0.0, 0.5],
        }
        return [vectors.get(t, [0.0, 0.0, 0.0]) for t in texts]


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="mismatch"):
            cosine_similarity([1.0], [1.0, 2.0])


class TestSemanticMatch:
    async def test_basic_matching(self):
        provider = FakeEmbedding()
        results = await semantic_match(
            query="invoice processing",
            candidates=["handle invoices", "send emails", "process payments"],
            embedding_provider=provider,
            top_k=2,
        )
        assert len(results) == 2
        assert results[0].text == "handle invoices"
        assert results[0].score > results[1].score

    async def test_empty_candidates(self):
        provider = FakeEmbedding()
        results = await semantic_match(
            query="anything",
            candidates=[],
            embedding_provider=provider,
        )
        assert results == []

    async def test_threshold_filters(self):
        provider = FakeEmbedding()
        results = await semantic_match(
            query="invoice processing",
            candidates=["handle invoices", "send emails", "process payments"],
            embedding_provider=provider,
            threshold=0.9,
        )
        # Only "handle invoices" should be above 0.9 similarity
        assert all(r.score >= 0.9 for r in results)

    async def test_embed_one_convenience(self):
        provider = FakeEmbedding()
        result = await provider.embed_one("invoice processing")
        assert result == [1.0, 0.0, 0.0]
