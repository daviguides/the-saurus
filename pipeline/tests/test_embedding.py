"""Tests for the standalone embedding module (no QdrantIndexer required)."""

from unittest.mock import AsyncMock, patch

from pipeline.config import settings
from pipeline.core.embedding import (
    EMBEDDING_DIMENSION,
    cosine_similarity,
    create_embedder,
    embed_batch,
    embed_text,
)

SAMPLE_TEXT = "A single paragraph to embed."
SAMPLE_TEXTS = ["First paragraph.", "Second paragraph."]
SAMPLE_VECTOR = [0.1, 0.2, 0.3]
SAMPLE_VECTORS = [[0.1, 0.2], [0.3, 0.4]]
SAMPLE_USAGE = [{"billable_character_count": 10}, {"billable_character_count": 12}]


def test_create_embedder_uses_settings() -> None:
    embedder = create_embedder()

    assert embedder.id == settings.qdrant_embedding_model
    assert embedder.api_key == settings.llm_api_key
    assert embedder.dimensions == EMBEDDING_DIMENSION


async def test_embed_text_delegates_to_embedder() -> None:
    mock_embedder = AsyncMock()
    mock_embedder.async_get_embedding.return_value = SAMPLE_VECTOR

    with patch("pipeline.core.embedding._embedder", mock_embedder):
        result = await embed_text(SAMPLE_TEXT)

    assert result == SAMPLE_VECTOR
    mock_embedder.async_get_embedding.assert_awaited_once_with(SAMPLE_TEXT)


async def test_embed_batch_delegates_and_discards_usage() -> None:
    mock_embedder = AsyncMock()
    mock_embedder.async_get_embeddings_batch_and_usage.return_value = (
        SAMPLE_VECTORS,
        SAMPLE_USAGE,
    )

    with patch("pipeline.core.embedding._embedder", mock_embedder):
        result = await embed_batch(SAMPLE_TEXTS)

    assert result == SAMPLE_VECTORS
    mock_embedder.async_get_embeddings_batch_and_usage.assert_awaited_once_with(SAMPLE_TEXTS)


def test_cosine_similarity_identical_vectors_returns_one() -> None:
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors_returns_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_opposite_vectors_returns_negative_one() -> None:
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0


def test_cosine_similarity_zero_vector_returns_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
