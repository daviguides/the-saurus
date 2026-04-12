"""Multi-collection Qdrant store for pipeline outputs."""

import asyncio
import logging

from agno.knowledge.embedder.google import GeminiEmbedder
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from papers_mcp.config import (
    LITERATURE_REVIEW,
    PAPER_CLAIMS,
    PAPER_THEMES,
    THEME_MAP,
    THEME_REVIEWS,
    settings,
)
from papers_mcp.schemas.results import (
    ClaimResult,
    ClaimSearchResult,
    ReviewSection,
    ThemeMapEntry,
    ThemeResult,
    ThemeReviewResult,
)

logger = logging.getLogger(__name__)

_SCROLL_LIMIT = 200


class PapersStore:
    def __init__(self) -> None:
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
        self._embedder = GeminiEmbedder(
            id=settings.embedding_model,
            api_key=settings.embedding_api_key or None,
        )

    async def close(self) -> None:
        """Close underlying Qdrant client connection."""
        await self._client.close()

    async def _scroll(
        self,
        collection: str,
        scroll_filter: Filter | None = None,
        limit: int = _SCROLL_LIMIT,
    ) -> list[dict]:
        try:
            records, next_page_offset = await self._client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            if next_page_offset is not None:
                logger.warning(
                    "Scroll results truncated for %s (limit=%d); more records exist",
                    collection,
                    limit,
                )
            return [r.payload for r in records if r.payload]
        except Exception:
            logger.warning("Qdrant scroll failed for %s", collection, exc_info=True)
            return []

    async def _embed(self, text: str) -> list[float]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._embedder.get_embedding, text),
                timeout=settings.embedding_timeout,
            )
        except TimeoutError:
            logger.error("Embedding call timed out after %ss", settings.embedding_timeout)
            raise
        except Exception:
            logger.error("Embedding call failed", exc_info=True)
            raise

    async def get_paper_themes(self, paper_id: str) -> list[ThemeResult]:
        payloads = await self._scroll(
            PAPER_THEMES,
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
        )
        return [ThemeResult.model_validate(p) for p in payloads]

    async def get_claims_by_theme(self, theme: str) -> list[ClaimResult]:
        payloads = await self._scroll(
            PAPER_CLAIMS,
            scroll_filter=Filter(
                must=[FieldCondition(key="theme_name", match=MatchValue(value=theme))]
            ),
        )
        return [ClaimResult.model_validate(p) for p in payloads]

    async def get_theme_map(self) -> list[ThemeMapEntry]:
        payloads = await self._scroll(THEME_MAP)
        return [ThemeMapEntry.model_validate(p) for p in payloads]

    async def get_theme_review(self, theme: str) -> ThemeReviewResult | None:
        payloads = await self._scroll(
            THEME_REVIEWS,
            scroll_filter=Filter(
                must=[FieldCondition(key="label", match=MatchValue(value=theme))]
            ),
            limit=1,
        )
        if not payloads:
            return None
        return ThemeReviewResult.model_validate(payloads[0])

    async def get_literature_review(self) -> list[ReviewSection]:
        payloads = await self._scroll(LITERATURE_REVIEW)
        return [ReviewSection.model_validate(p) for p in payloads]

    async def search_claims(self, query: str, limit: int | None = None) -> list[ClaimSearchResult]:
        top_k = limit if limit is not None else settings.default_top_k
        embedding = await self._embed(query)
        try:
            response = await self._client.query_points(
                collection_name=PAPER_CLAIMS,
                query=embedding,
                limit=top_k,
                score_threshold=settings.min_score_threshold,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            logger.warning("Qdrant query failed for %s", PAPER_CLAIMS, exc_info=True)
            return []

        results = []
        for point in response.points:
            p = point.payload or {}
            claim = ClaimResult.model_validate(p)
            results.append(ClaimSearchResult(claim=claim, score=point.score))
        return results

    async def health(self) -> dict:
        collections = {}
        for name in (PAPER_THEMES, PAPER_CLAIMS, THEME_MAP, THEME_REVIEWS, LITERATURE_REVIEW):
            try:
                info = await self._client.get_collection(name)
                collections[name] = {"points": info.points_count, "status": info.status.value}
            except Exception:
                collections[name] = {"points": 0, "status": "not_found"}
        return collections


_store: PapersStore | None = None
_store_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    """Get or create the singleton lock (must be called within a running event loop)."""
    global _store_lock
    if _store_lock is None:
        _store_lock = asyncio.Lock()
    return _store_lock


async def get_store() -> PapersStore:
    global _store
    if _store is not None:
        return _store
    async with _get_lock():
        if _store is None:
            _store = PapersStore()
    return _store


async def close_store() -> None:
    """Close and discard the singleton store."""
    global _store
    if _store is not None:
        await _store.close()
        _store = None
