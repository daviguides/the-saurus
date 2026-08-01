"""LLM-as-NLI verification for theme_reviewer: §5.2 (consensus/disagreement
labeling) and §5.4's DeBERTa-borderline escalation tier. Distinct from
nli.py's local DeBERTa cross-encoder (Tier 0.5) — this is the LLM escalation
tier, verifying against the theme's full claim set (f-009: consensus/
disagreement entries carry no claim_id linkage to check against instead).
"""

from __future__ import annotations

from typing import Any, Literal

from agno.agent import Agent as AgnoAgent
from pydantic import BaseModel

from pipeline.agents.parsing import run_agent_with_retry


class ConsensusDisagreementVerdict(BaseModel):
    label: Literal["CONSENSUS", "DISAGREEMENT", "NEITHER"]


class EntailmentVerdict(BaseModel):
    label: Literal["ENTAILED", "CONTRADICTED", "NEUTRAL"]


CONSENSUS_NLI_PROMPT = """\
You verify whether a claimed consensus/disagreement is actually supported \
by the given claims. Given a set of claims and a hypothesis sentence, \
decide: do the claims collectively support this as CONSENSUS (they agree), \
DISAGREEMENT (they conflict), or NEITHER (unsupported by these claims)? \
Output only the label."""

ENTAILMENT_NLI_PROMPT = """\
You verify whether a sentence is grounded in the given claims. Given a set \
of claims and a hypothesis sentence, decide: is the sentence ENTAILED by \
at least one claim, CONTRADICTED by a claim, or NEUTRAL (unsupported, \
unrelated, or unverifiable from these claims)? Output only the label."""


def _format_claims(claims: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {c.get('summary', c.get('text', ''))}" for c in claims)


async def verify_consensus_disagreement(
    agent: AgnoAgent,
    claims: list[dict[str, Any]],
    entry: str,
    claimed_as: str,
    *,
    context: dict[str, Any] | None = None,
) -> str:
    """Classify `entry` against the full claim set; returns the produced label."""
    message = (
        f"Claims:\n{_format_claims(claims)}\n\n"
        f"Hypothesis: {entry}\n\n"
        f"This was labeled: {claimed_as}. Does it hold?"
    )
    result = await run_agent_with_retry(
        agent, message, ConsensusDisagreementVerdict, context=context
    )
    return result.label


async def verify_sentence_entailment(
    agent: AgnoAgent,
    claims: list[dict[str, Any]],
    sentence: str,
    *,
    context: dict[str, Any] | None = None,
) -> str:
    """Resolve a DeBERTa-borderline sentence; returns ENTAILED/CONTRADICTED/NEUTRAL."""
    message = f"Claims:\n{_format_claims(claims)}\n\nSentence: {sentence}"
    result = await run_agent_with_retry(agent, message, EntailmentVerdict, context=context)
    return result.label
