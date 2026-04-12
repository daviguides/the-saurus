import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from papers_mcp.store import close_store, get_store

logger = logging.getLogger(__name__)

# Maximum allowed query length for search_claims
_MAX_QUERY_LENGTH = 10_000
# Maximum allowed limit for search_claims
_MAX_SEARCH_LIMIT = 100


@asynccontextmanager
async def app_lifespan(server):
    logger.info("Papers MCP starting")
    try:
        store = await get_store()
        health = await store.health()
        logger.info("Qdrant collections: %s", health)
    except Exception as e:
        logger.error("Qdrant not available at startup: %s", e)
    yield
    # Teardown: close store connections
    await close_store()


mcp = FastMCP("papers-mcp", lifespan=app_lifespan)

# NOTE: This is an internal service intended to run on localhost only.
# It should NOT be exposed to untrusted networks without adding authentication.


@mcp.tool()
async def get_paper_themes(paper_id: str) -> list[dict]:
    """Get themes extracted from a specific paper.

    Args:
        paper_id: The paper identifier to retrieve themes for.
    """
    try:
        store = await get_store()
        return [t.model_dump() for t in await store.get_paper_themes(paper_id)]
    except Exception as e:
        logger.error("get_paper_themes failed: %s", e, exc_info=True)
        return [{"error": f"Failed to retrieve themes: {e}"}]


@mcp.tool()
async def get_claims_by_theme(theme: str) -> list[dict]:
    """Get all claims grouped under a specific theme across all papers.

    Args:
        theme: The theme name to filter claims by.
    """
    try:
        store = await get_store()
        return [c.model_dump() for c in await store.get_claims_by_theme(theme)]
    except Exception as e:
        logger.error("get_claims_by_theme failed: %s", e, exc_info=True)
        return [{"error": f"Failed to retrieve claims: {e}"}]


@mcp.tool()
async def get_theme_map() -> list[dict]:
    """Get the full canonical theme map across all papers.

    Returns the deduplicated themes with their paper associations,
    aliases, and descriptions.
    """
    try:
        store = await get_store()
        return [t.model_dump() for t in await store.get_theme_map()]
    except Exception as e:
        logger.error("get_theme_map failed: %s", e, exc_info=True)
        return [{"error": f"Failed to retrieve theme map: {e}"}]


@mcp.tool()
async def get_theme_review(theme: str) -> dict | None:
    """Get the deep review for a specific theme.

    Args:
        theme: The theme label to retrieve the review for.
    """
    try:
        store = await get_store()
        result = await store.get_theme_review(theme)
        return result.model_dump() if result else None
    except Exception as e:
        logger.error("get_theme_review failed: %s", e, exc_info=True)
        return {"error": f"Failed to retrieve theme review: {e}"}


@mcp.tool()
async def get_literature_review() -> list[dict]:
    """Get the complete literature review with all sections.

    Returns all sections of the aggregated literature review,
    each containing content, theme association, and citation references.
    """
    try:
        store = await get_store()
        return [s.model_dump() for s in await store.get_literature_review()]
    except Exception as e:
        logger.error("get_literature_review failed: %s", e, exc_info=True)
        return [{"error": f"Failed to retrieve literature review: {e}"}]


@mcp.tool()
async def search_claims(query: str, limit: int = 10) -> list[dict]:
    """Semantic search across all extracted claims.

    Embeds the query and finds the most similar claims using vector search.

    Args:
        query: Natural language search query.
        limit: Maximum number of results to return (default 10, max 100).
    """
    if len(query) > _MAX_QUERY_LENGTH:
        return [{"error": f"Query too long ({len(query)} chars). Max is {_MAX_QUERY_LENGTH}."}]
    limit = min(max(limit, 1), _MAX_SEARCH_LIMIT)
    try:
        store = await get_store()
        return [r.model_dump() for r in await store.search_claims(query, limit)]
    except Exception as e:
        logger.error("search_claims failed: %s", e, exc_info=True)
        return [{"error": f"Failed to search claims: {e}"}]
