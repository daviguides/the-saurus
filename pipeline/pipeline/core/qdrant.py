"""Qdrant vector indexer: fire-and-forget writes for pipeline outputs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from pipeline.config import settings

from .embedding import EMBEDDING_DIMENSION, embed_batch, embed_text

logger = logging.getLogger(__name__)

# Collection names — must match papers-mcp consumer expectations.
PAPER_THEMES = "paper_themes"
PAPER_CLAIMS = "paper_claims"
THEME_MAP = "theme_map"
THEME_REVIEWS = "theme_reviews"
LITERATURE_REVIEW = "literature_review"

ALL_COLLECTIONS = [PAPER_THEMES, PAPER_CLAIMS, THEME_MAP, THEME_REVIEWS, LITERATURE_REVIEW]


class QdrantIndexer:
    """Embeds pipeline outputs and upserts to Qdrant collections.

    Uses Agno GeminiEmbedder for embeddings via Gemini API.
    All methods are async and safe to call via asyncio.create_task().
    Failures are logged but never raised — Qdrant is a secondary index.
    """

    def __init__(self) -> None:
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self._dimension = EMBEDDING_DIMENSION

    def close(self) -> None:
        """Close the Qdrant client connection."""
        try:
            self._client.close()
        except Exception:
            logger.debug("Error closing Qdrant client", exc_info=True)

    async def ensure_collections(self) -> None:
        """Create all collections if they don't exist."""

        def _sync() -> None:
            for name in ALL_COLLECTIONS:
                if not self._client.collection_exists(name):
                    self._client.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(
                            size=self._dimension,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info("Created Qdrant collection: %s", name)

        await asyncio.to_thread(_sync)

    async def _embed(self, text: str) -> list[float]:
        """Embed a single text via the shared embedding module."""
        return await embed_text(text)

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts via the shared embedding module."""
        return await embed_batch(texts)

    async def _upsert(self, collection: str, points: list[PointStruct]) -> None:
        """Upsert points to a collection in a thread."""
        await asyncio.to_thread(self._client.upsert, collection_name=collection, points=points)

    async def index_themes(self, job_id: str, paper_id: str, result: dict[str, Any]) -> None:
        """Index per-paper themes to paper_themes collection."""
        themes = result.get("themes", [])
        if not themes:
            return

        texts = [f"{t['name']}: {t.get('description', '')}" for t in themes]
        vectors = await self._embed_batch(texts)

        points = [
            PointStruct(
                id=theme["id"],
                vector=vector,
                payload={
                    "job_id": job_id,
                    "paper_id": paper_id,
                    "name": theme["name"],
                    "description": theme.get("description", ""),
                    "positions": theme.get("positions", []),
                },
            )
            for theme, vector in zip(themes, vectors)
        ]
        await self._upsert(PAPER_THEMES, points)

    async def index_claims(self, job_id: str, paper_id: str, result: dict[str, Any]) -> None:
        """Index per-paper claims to paper_claims collection."""
        claims = result.get("claims", [])
        if not claims:
            return

        texts = [c["text"] for c in claims]
        vectors = await self._embed_batch(texts)

        points = [
            PointStruct(
                id=claim["id"],
                vector=vector,
                payload={
                    "job_id": job_id,
                    "paper_id": paper_id,
                    "theme_id": claim.get("theme_id", ""),
                    "theme_name": claim.get("theme_name", ""),
                    "text": claim["text"],
                    "page": claim.get("page", 0),
                    "paragraph": claim.get("paragraph", 0),
                    "deep": claim.get("deep", ""),
                    "summary": claim.get("summary", ""),
                    "source": claim.get("source", {}),
                },
            )
            for claim, vector in zip(claims, vectors)
        ]
        await self._upsert(PAPER_CLAIMS, points)

    async def index_theme_map(self, job_id: str, result: dict[str, Any]) -> None:
        """Index canonical themes to theme_map collection."""
        themes = result.get("themes", [])
        if not themes:
            return

        texts = [f"{t['name']}: {t.get('description', '')}" for t in themes]
        vectors = await self._embed_batch(texts)

        points = [
            PointStruct(
                id=theme["id"],
                vector=vector,
                payload={
                    "job_id": job_id,
                    "name": theme["name"],
                    "description": theme.get("description", ""),
                    "paper_ids": theme.get("paper_ids", []),
                    "aliases": theme.get("aliases", []),
                    "source_theme_ids": theme.get("source_theme_ids", []),
                },
            )
            for theme, vector in zip(themes, vectors)
        ]
        await self._upsert(THEME_MAP, points)

    async def index_theme_review(self, job_id: str, result: dict[str, Any]) -> None:
        """Index a single theme review to theme_reviews collection."""
        theme_id = result.get("theme_id", "")
        review_text = result.get("review", "")
        if not theme_id or not review_text:
            return

        vector = await self._embed(review_text)

        point = PointStruct(
            id=_safe_point_id(theme_id),
            vector=vector,
            payload={
                "job_id": job_id,
                "theme_id": theme_id,
                "label": result.get("label", ""),
                "review": review_text,
                "consensus": result.get("consensus", []),
                "disagreements": result.get("disagreements", []),
                "gaps": result.get("gaps", []),
                "claim_ids": result.get("claim_ids", []),
                "key_claims": result.get("key_claims", []),
            },
        )
        await self._upsert(THEME_REVIEWS, [point])

    async def index_review(self, job_id: str, result: dict[str, Any]) -> None:
        """Index literature review sections to literature_review collection."""
        sections = result.get("sections", [])
        if not sections:
            return

        texts = [s.get("content", "") for s in sections]
        vectors = await self._embed_batch(texts)

        citations = result.get("citations", [])
        references = result.get("references", [])

        points = [
            PointStruct(
                id=_safe_point_id(section.get("theme_id", "")),
                vector=vector,
                payload={
                    "job_id": job_id,
                    "title": result.get("title", ""),
                    "abstract": result.get("abstract", ""),
                    "theme_id": section.get("theme_id", ""),
                    "label": section.get("label", ""),
                    "content": section.get("content", ""),
                    "claim_ids": section.get("claim_ids", []),
                    "citation_refs": section.get("citation_refs", []),
                    "citations": citations,
                    "references": references,
                },
            )
            for section, vector in zip(sections, vectors)
        ]
        await self._upsert(LITERATURE_REVIEW, points)


def _safe_point_id(value: str) -> str:
    """Ensure value is a valid Qdrant point ID (UUID). Generate one if not."""
    try:
        UUID(value)
        return value
    except (ValueError, AttributeError):
        return str(uuid4())


_indexer: QdrantIndexer | None = None


def get_indexer() -> QdrantIndexer | None:
    """Return singleton QdrantIndexer, or None if init fails.

    Qdrant is a secondary index — if it's not available, the pipeline
    continues with YAML persistence as the source of truth.
    """
    global _indexer
    if _indexer is None:
        try:
            _indexer = QdrantIndexer()
        except Exception:
            logger.warning("Qdrant indexer init failed — indexing disabled for this session")
            return None
    return _indexer


def close_indexer() -> None:
    """Close and discard the singleton QdrantIndexer."""
    global _indexer
    if _indexer is not None:
        _indexer.close()
        _indexer = None
