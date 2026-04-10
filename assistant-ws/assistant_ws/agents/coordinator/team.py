from agno.team import Team

from assistant_ws.agents.coordinator.prompts import COORDINATOR_INSTRUCTIONS
from assistant_ws.agents.papers.agent import build_papers_agent
from assistant_ws.agents.shared.models import create_model


async def build_coordinator_team() -> Team:
    model = create_model()
    papers_agent = await build_papers_agent(model=model)

    return Team(
        name="CoordinatorTeam",
        model=model,
        members=[papers_agent],
        instructions=COORDINATOR_INSTRUCTIONS,
        stream_member_events=True,
        add_history_to_context=True,
    )
