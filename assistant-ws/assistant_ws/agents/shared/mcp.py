import asyncio
import logging
import time

from agno.tools.mcp import MCPTools

from assistant_ws.config import settings

logger = logging.getLogger(__name__)

_papers_mcp: MCPTools | None = None
_lock = asyncio.Lock()
_connected_at: float = 0.0


async def get_papers_mcp() -> MCPTools | None:
    """Connect to papers MCP server with retry and TTL. Returns None if unavailable."""
    global _papers_mcp, _connected_at

    async with _lock:
        # Check TTL on cached connection
        if _papers_mcp is not None:
            ttl_seconds = settings.mcp_connection_ttl_minutes * 60
            if (time.monotonic() - _connected_at) > ttl_seconds:
                logger.info("MCP connection TTL expired, reconnecting...")
                await _close_mcp_connection()
            else:
                return _papers_mcp

        # Retry connection with configured max_retries
        for attempt in range(1, settings.mcp_max_retries + 1):
            try:
                mcp = MCPTools(
                    transport="streamable-http",
                    url=settings.mcp_papers_url,
                    timeout_seconds=settings.mcp_timeout_seconds,
                )
                await mcp.connect()
                _papers_mcp = mcp
                _connected_at = time.monotonic()
                logger.info(
                    "Connected to papers MCP at %s (attempt %d)",
                    settings.mcp_papers_url,
                    attempt,
                )
                return mcp
            except Exception:
                logger.warning(
                    "Papers MCP connection attempt %d/%d failed at %s",
                    attempt,
                    settings.mcp_max_retries,
                    settings.mcp_papers_url,
                )
                if attempt < settings.mcp_max_retries:
                    await asyncio.sleep(min(2**attempt, 10))

        logger.warning(
            "Papers MCP not available at %s after %d attempts — "
            "assistant will work without paper tools",
            settings.mcp_papers_url,
            settings.mcp_max_retries,
        )
        return None


async def _close_mcp_connection():
    """Close the cached MCP connection."""
    global _papers_mcp, _connected_at
    if _papers_mcp is not None:
        try:
            await _papers_mcp.disconnect()
        except Exception:
            logger.warning("Error closing MCP connection", exc_info=True)
        _papers_mcp = None
        _connected_at = 0.0


async def close_mcp() -> None:
    """Public shutdown helper — call from app lifespan teardown."""
    async with _lock:
        await _close_mcp_connection()
