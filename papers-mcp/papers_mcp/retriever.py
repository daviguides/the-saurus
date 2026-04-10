import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from papers_mcp.config import settings
from papers_mcp.schemas.results import SearchResultWithReference

logger = logging.getLogger(__name__)


class PapersRetriever:
    def __init__(self):
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self._encoder = SentenceTransformer(settings.embedding_model)
        self._collection = settings.qdrant_collection

    def search(
        self,
        query: str,
        top_k: int = 5,
        year_from: int | None = None,
        year_to: int | None = None,
        journal: str | None = None,
        topic: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResultWithReference]:
        embedding = self._encoder.encode(query).tolist()

        conditions = []
        if journal:
            conditions.append(FieldCondition(key="journal", match=MatchValue(value=journal)))
        if topic:
            conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))

        query_filter = Filter(must=conditions) if conditions else None

        results = self._client.query_points(
            collection_name=self._collection,
            query=embedding,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=min_score or settings.min_score_threshold,
        )

        items = []
        for point in results.points:
            payload = point.payload or {}

            if year_from and payload.get("year", 9999) < year_from:
                continue
            if year_to and payload.get("year", 0) > year_to:
                continue

            items.append(
                SearchResultWithReference(
                    content=payload.get("content", ""),
                    score=point.score,
                    rank=len(items) + 1,
                    title=payload.get("title", ""),
                    authors=payload.get("authors", []),
                    year=payload.get("year"),
                    doi=payload.get("doi"),
                    journal=payload.get("journal"),
                    abstract=payload.get("abstract", ""),
                    section_title=payload.get("section_title"),
                )
            )

        return items

    def stats(self) -> dict:
        info = self._client.get_collection(self._collection)
        return {
            "collection": self._collection,
            "points_count": info.points_count,
            "status": info.status.value,
        }


_retriever: PapersRetriever | None = None


def get_retriever() -> PapersRetriever:
    global _retriever
    if _retriever is None:
        _retriever = PapersRetriever()
    return _retriever
