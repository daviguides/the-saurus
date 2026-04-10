from papers_mcp.retriever import PapersRetriever, SearchResultWithReference


def _build_response(results: list[SearchResultWithReference]) -> dict:
    return {
        "results": [r.to_result_dict() for r in results],
        "_meta": {
            "references": [r.to_reference_dict() for r in results],
        },
    }


def search_papers_impl(
    retriever: PapersRetriever,
    query: str,
    top_k: int = 5,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> dict:
    results = retriever.search(
        query=query,
        top_k=top_k,
        year_from=year_from,
        year_to=year_to,
        journal=journal,
    )
    return _build_response(results)


def search_by_topic_impl(
    retriever: PapersRetriever,
    topic: str,
    query: str = "",
    top_k: int = 10,
    year_from: int | None = None,
) -> dict:
    results = retriever.search(
        query=query or topic,
        top_k=top_k,
        topic=topic,
        year_from=year_from,
    )
    return _build_response(results)


def find_similar_papers_impl(
    retriever: PapersRetriever,
    abstract: str,
    top_k: int = 5,
) -> dict:
    results = retriever.search(query=abstract, top_k=top_k)
    return _build_response(results)
