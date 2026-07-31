"""Builds the Colang topic-gate runtime once and exposes evaluate_topic_gate()."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from nemoguardrails import LLMRails, RailsConfig
from pydantic import BaseModel

from .actions import check_metadata_action, check_quality_action


class TopicGateResult(BaseModel):
    """Outcome of the pre-analysis topic gate."""

    verdict: Literal["accept", "reject"]
    reason: str | None = None


def _build_rails() -> LLMRails:
    config = RailsConfig.from_path(str(Path(__file__).parent))
    rails = LLMRails(config=config, llm=None)
    rails.register_action(check_quality_action, name="CheckQualityAction")
    rails.register_action(check_metadata_action, name="CheckMetadataAction")
    return rails


_rails = _build_rails()


async def evaluate_topic_gate(
    *, content: str, page_count: int, title: str, authors: list[str],
) -> TopicGateResult:
    events = [{
        "type": "TopicGateCheck",
        "content": content,
        "page_count": page_count,
        "title": title,
        "authors": authors,
    }]
    new_events, _state = await _rails.process_events_async(events=events)
    for event in new_events:
        if event.get("type") == "TopicGateRejected":
            return TopicGateResult(verdict="reject", reason=event.get("reason"))
        if event.get("type") == "TopicGateAccepted":
            return TopicGateResult(verdict="accept")
    return TopicGateResult(
        verdict="reject", reason="topic gate flow produced no verdict event",
    )
