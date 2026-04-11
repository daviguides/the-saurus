"""Multi-collection Qdrant store for pipeline outputs."""

import logging

from agno.knowledge.embedder.google import GeminiEmbedder
from qdrant_client import QdrantClient
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
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self._embedder = GeminiEmbedder(
            id=settings.embedding_model,
            api_key=settings.embedding_api_key or None,
        )

    def _scroll(
        self,
        collection: str,
        scroll_filter: Filter | None = None,
        limit: int = _SCROLL_LIMIT,
    ) -> list[dict]:
        try:
            records, _ = self._client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [r.payload for r in records if r.payload]
        except Exception:
            logger.warning("Qdrant scroll failed for %s", collection, exc_info=True)
            return []

    def _embed(self, text: str) -> list[float]:
        return self._embedder.get_embedding(text)

    def get_paper_themes(self, paper_id: str) -> list[ThemeResult]:
        payloads = self._scroll(
            PAPER_THEMES,
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
        )
        return [ThemeResult.model_validate(p) for p in payloads]

    def get_claims_by_theme(self, theme: str) -> list[ClaimResult]:
        payloads = self._scroll(
            PAPER_CLAIMS,
            scroll_filter=Filter(
                must=[FieldCondition(key="theme_name", match=MatchValue(value=theme))]
            ),
        )
        return [ClaimResult.model_validate(p) for p in payloads]

    def get_theme_map(self) -> list[ThemeMapEntry]:
        payloads = self._scroll(THEME_MAP)
        return [ThemeMapEntry.model_validate(p) for p in payloads]

    def get_theme_review(self, theme: str) -> ThemeReviewResult | None:
        payloads = self._scroll(
            THEME_REVIEWS,
            scroll_filter=Filter(
                must=[FieldCondition(key="label", match=MatchValue(value=theme))]
            ),
            limit=1,
        )
        if not payloads:
            return None
        return ThemeReviewResult.model_validate(payloads[0])

    def get_literature_review(self) -> list[ReviewSection]:
        payloads = self._scroll(LITERATURE_REVIEW)
        return [ReviewSection.model_validate(p) for p in payloads]

    def search_claims(self, query: str, limit: int | None = None) -> list[ClaimSearchResult]:
        top_k = limit or settings.default_top_k
        embedding = self._embed(query)
        try:
            response = self._client.query_points(
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

    def health(self) -> dict:
        collections = {}
        for name in (PAPER_THEMES, PAPER_CLAIMS, THEME_MAP, THEME_REVIEWS, LITERATURE_REVIEW):
            try:
                info = self._client.get_collection(name)
                collections[name] = {"points": info.points_count, "status": info.status.value}
            except Exception:
                collections[name] = {"points": 0, "status": "not_found"}
        return collections


_store: PapersStore | None = None


def get_store() -> PapersStore:
    global _store
    if _store is None:
        _store = PapersStore()
    return _store
