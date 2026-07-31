"""Reusable Gemini embedder: standalone, no QdrantIndexer instantiation required."""

from __future__ import annotations

import math

from agno.knowledge.embedder.google import GeminiEmbedder

from pipeline.config import settings

# gemini-embedding-001 default output: 1536 dimensions
EMBEDDING_DIMENSION = 1536


def create_embedder() -> GeminiEmbedder:
    """Create an Agno GeminiEmbedder instance from pipeline settings."""
    return GeminiEmbedder(
        id=settings.qdrant_embedding_model,
        api_key=settings.llm_api_key,
        dimensions=EMBEDDING_DIMENSION,
    )


_embedder = create_embedder()


async def embed_text(text: str) -> list[float]:
    """Embed a single text via the shared Gemini embedder."""
    return await _embedder.async_get_embedding(text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts via the shared Gemini embedder."""
    vectors, _usage = await _embedder.async_get_embeddings_batch_and_usage(texts)
    return vectors


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors. Pure Python — no numpy
    dependency justified for comparisons over 1536-dim vectors at pipeline scale."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
