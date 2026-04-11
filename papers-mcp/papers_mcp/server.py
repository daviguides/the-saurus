import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from papers_mcp.store import get_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server):
    logger.info("Papers MCP starting")
    try:
        store = get_store()
        health = store.health()
        logger.info("Qdrant collections: %s", health)
    except Exception as e:
        logger.warning("Qdrant not available at startup: %s", e)
    yield


mcp = FastMCP("papers-mcp", lifespan=app_lifespan)


@mcp.tool()
def get_paper_themes(paper_id: str) -> list[dict]:
    """Get themes extracted from a specific paper.

    Args:
        paper_id: The paper identifier to retrieve themes for.
    """
    store = get_store()
    return [t.model_dump() for t in store.get_paper_themes(paper_id)]


@mcp.tool()
def get_claims_by_theme(theme: str) -> list[dict]:
    """Get all claims grouped under a specific theme across all papers.

    Args:
        theme: The theme name to filter claims by.
    """
    store = get_store()
    return [c.model_dump() for c in store.get_claims_by_theme(theme)]


@mcp.tool()
def get_theme_map() -> list[dict]:
    """Get the full canonical theme map across all papers.

    Returns the deduplicated themes with their paper associations,
    aliases, and descriptions.
    """
    store = get_store()
    return [t.model_dump() for t in store.get_theme_map()]


@mcp.tool()
def get_theme_review(theme: str) -> dict | None:
    """Get the deep review for a specific theme.

    Args:
        theme: The theme label to retrieve the review for.
    """
    store = get_store()
    result = store.get_theme_review(theme)
    return result.model_dump() if result else None


@mcp.tool()
def get_literature_review() -> list[dict]:
    """Get the complete literature review with all sections.

    Returns all sections of the aggregated literature review,
    each containing content, theme association, and citation references.
    """
    store = get_store()
    return [s.model_dump() for s in store.get_literature_review()]


@mcp.tool()
def search_claims(query: str, limit: int = 10) -> list[dict]:
    """Semantic search across all extracted claims.

    Embeds the query and finds the most similar claims using vector search.

    Args:
        query: Natural language search query.
        limit: Maximum number of results to return (default 10).
    """
    store = get_store()
    return [r.model_dump() for r in store.search_claims(query, limit)]
