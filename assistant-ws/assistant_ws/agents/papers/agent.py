from agno.agent import Agent
from agno.models.base import Model

from assistant_ws.agents.papers.prompts import PAPERS_INSTRUCTIONS
from assistant_ws.agents.shared.mcp import get_papers_mcp
from assistant_ws.agents.shared.models import create_model


async def build_papers_agent(model: Model | None = None) -> Agent:
    mcp_tools = await get_papers_mcp()

    tools = [mcp_tools] if mcp_tools else []

    return Agent(
        name="PapersAgent",
        model=model or create_model(),
        instructions=PAPERS_INSTRUCTIONS,
        tools=tools,
        store_events=True,
        tool_call_limit=5,
    )
