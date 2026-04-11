import asyncio
import logging

from agno.tools.mcp import MCPTools

from assistant_ws.config import settings

logger = logging.getLogger(__name__)

_papers_mcp: MCPTools | None = None
_lock = asyncio.Lock()


async def get_papers_mcp() -> MCPTools | None:
    """Connect to papers MCP server. Returns None if unavailable (graceful)."""
    global _papers_mcp

    async with _lock:
        if _papers_mcp is not None:
            return _papers_mcp

        try:
            mcp = MCPTools(
                transport="streamable-http",
                url=settings.mcp_papers_url,
                timeout_seconds=settings.mcp_timeout_seconds,
            )
            await mcp.connect()
            _papers_mcp = mcp
            logger.info("Connected to papers MCP at %s", settings.mcp_papers_url)
            return mcp
        except Exception:
            logger.warning(
                "Papers MCP not available at %s — assistant will work without paper tools",
                settings.mcp_papers_url,
            )
            return None
