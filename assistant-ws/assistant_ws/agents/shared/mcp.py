import asyncio
import logging

from agno.tools.mcp import MCPTools

from assistant_ws.config import settings

logger = logging.getLogger(__name__)

_papers_mcp: MCPTools | None = None
_lock = asyncio.Lock()


async def get_papers_mcp() -> MCPTools:
    global _papers_mcp

    async with _lock:
        if _papers_mcp is not None:
            return _papers_mcp

        max_retries = settings.mcp_max_retries
        delay = 1.0

        for attempt in range(max_retries):
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
                    "Papers MCP connection attempt %d/%d failed, retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)

        raise RuntimeError(f"Failed to connect to papers MCP after {max_retries} attempts")
