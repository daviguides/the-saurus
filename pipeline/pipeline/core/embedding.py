"""Reusable Gemini embedder: standalone, no QdrantIndexer instantiation required."""

from __future__ import annotations

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
