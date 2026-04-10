import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from papers_mcp.config import settings
from papers_mcp.retriever import get_retriever
from papers_mcp.tools.search import (
    find_similar_papers_impl,
    search_by_topic_impl,
    search_papers_impl,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server):
    logger.info("Papers MCP starting — collection: %s", settings.qdrant_collection)
    try:
        retriever = get_retriever()
        stats = retriever.stats()
        logger.info("Qdrant connected: %s", stats)
    except Exception as e:
        logger.warning("Qdrant not available at startup: %s", e)
    yield


mcp = FastMCP("papers-mcp", lifespan=app_lifespan)


@mcp.tool()
def search_papers(
    query: str,
    top_k: int = 5,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> dict:
    """Search scientific papers by natural language query.

    Args:
        query: Natural language search query (e.g. "transformer attention mechanisms")
        top_k: Number of results to return (default 5)
        year_from: Filter papers published after this year
        year_to: Filter papers published before this year
        journal: Filter by journal name
    """
    retriever = get_retriever()
    return search_papers_impl(retriever, query, top_k, year_from, year_to, journal)


@mcp.tool()
def search_by_topic(
    topic: str,
    query: str = "",
    top_k: int = 10,
    year_from: int | None = None,
) -> dict:
    """Search papers within a specific research topic.

    Args:
        topic: Research topic/field (e.g. "machine learning", "genomics")
        query: Optional additional query to narrow results
        top_k: Number of results to return (default 10)
        year_from: Filter papers published after this year
    """
    retriever = get_retriever()
    return search_by_topic_impl(retriever, topic, query, top_k, year_from)


@mcp.tool()
def find_similar_papers(
    abstract: str,
    top_k: int = 5,
) -> dict:
    """Find papers similar to a given abstract or text passage.

    Args:
        abstract: Abstract or text to find similar papers for
        top_k: Number of results to return (default 5)
    """
    retriever = get_retriever()
    return find_similar_papers_impl(retriever, abstract, top_k)
