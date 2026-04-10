"""Cosine similarity and semantic matching utilities.

Pure-math implementations with no external dependencies beyond the
BaseEmbeddingProvider interface.

Example::

    from mcp_forge_core.similarity import cosine_similarity, semantic_match

    # Direct vector similarity
    score = cosine_similarity([1.0, 0.0], [0.7, 0.7])

    # Semantic matching with an embedding provider
    results = await semantic_match(
        query="invoice processing",
        candidates=["handle invoices", "send emails", "process payments"],
        embedding_provider=my_embedding_provider,
        top_k=2,
    )
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .providers.embedding import BaseEmbeddingProvider


@dataclass(frozen=True, slots=True)
class ScoredItem:
    """A candidate with its similarity score.

    Attributes:
        text: The original candidate text.
        score: Cosine similarity score (0.0 to 1.0).
        index: Original index in the candidates list.
    """

    text: str
    score: float
    index: int


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector (must be same length as a).

    Returns:
        Cosine similarity in range [-1.0, 1.0]. Returns 0.0 if either vector
        has zero magnitude.

    Raises:
        ValueError: If vectors have different lengths.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return dot / (mag_a * mag_b)


async def semantic_match(
    query: str,
    candidates: list[str],
    embedding_provider: BaseEmbeddingProvider,
    *,
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[ScoredItem]:
    """Find the most semantically similar candidates to a query.

    Embeds the query and all candidates in a single batch call, then ranks
    by cosine similarity.

    Args:
        query: The query text to match against.
        candidates: List of candidate texts.
        embedding_provider: Provider to generate embeddings.
        top_k: Maximum number of results to return.
        threshold: Minimum similarity score to include.

    Returns:
        List of ScoredItem sorted by descending similarity score.
    """
    if not candidates:
        return []

    all_texts = [query] + candidates
    embeddings = await embedding_provider.embed(all_texts)

    query_embedding = embeddings[0]
    candidate_embeddings = embeddings[1:]

    scored = []
    for i, candidate_emb in enumerate(candidate_embeddings):
        score = cosine_similarity(query_embedding, candidate_emb)
        if score >= threshold:
            scored.append(ScoredItem(text=candidates[i], score=score, index=i))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]
