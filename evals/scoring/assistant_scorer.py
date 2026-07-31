"""Batch scoring for assistant production traces.

Fetches traces from Langfuse, evaluates with RAGAS metrics,
and pushes scores back for dashboarding.

Usage:
    uv run python -m scoring.assistant_scorer
"""

import asyncio
import logging
import random

from judge import create_ragas_embeddings, create_ragas_judge

logger = logging.getLogger(__name__)

SAMPLE_RATE = 0.10


def _extract_retrieved_contexts(trace) -> list:
    """Best-effort retrieval-context extraction from a Langfuse trace.

    No service populates this today (assistant-ws doesn't wire Langfuse
    tracing yet), so this returns [] until that plumbing exists — callers
    skip Faithfulness scoring on an empty result rather than erroring.
    """
    metadata = getattr(trace, "metadata", None)
    if not isinstance(metadata, dict):
        return []
    return metadata.get("retrieved_contexts") or []


async def score_assistant_traces():
    """Fetch assistant traces from Langfuse and score."""
    try:
        from langfuse import get_client
        from ragas.metrics.collections import AnswerRelevancy, Faithfulness
    except ImportError:
        logger.error("Missing dependencies. Run: cd evals && uv sync")
        return

    langfuse = get_client()
    llm = create_ragas_judge()
    embeddings = create_ragas_embeddings()

    traces = langfuse.api.trace.list(name="assistant").data
    if not traces:
        logger.info("No assistant traces found in Langfuse")
        return

    sample_size = max(1, int(len(traces) * SAMPLE_RATE))
    sampled = random.sample(traces, min(sample_size, len(traces)))
    logger.info(
        "Scoring %d/%d assistant traces", len(sampled), len(traces),
    )

    relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
    faithfulness = Faithfulness(llm=llm)

    for trace in sampled:
        input_text = str(trace.input) if trace.input else ""
        output_text = str(trace.output) if trace.output else ""

        if not input_text or not output_text:
            continue

        try:
            result = await relevancy.ascore(user_input=input_text, response=output_text)

            langfuse.create_score(
                name=relevancy.name,
                value=result.value,
                trace_id=trace.id,
            )
            logger.info(
                "Scored trace %s: %s=%.3f",
                trace.id[:8], relevancy.name, result.value,
            )

        except Exception:
            logger.warning(
                "Failed to score trace %s with %s", trace.id[:8], relevancy.name, exc_info=True,
            )

        retrieved_contexts = _extract_retrieved_contexts(trace)
        if not retrieved_contexts:
            logger.info(
                "Skipping %s for trace %s: no retrieved_contexts available",
                faithfulness.name, trace.id[:8],
            )
            continue

        try:
            result = await faithfulness.ascore(
                user_input=input_text,
                response=output_text,
                retrieved_contexts=retrieved_contexts,
            )

            langfuse.create_score(
                name=faithfulness.name,
                value=result.value,
                trace_id=trace.id,
            )
            logger.info(
                "Scored trace %s: %s=%.3f",
                trace.id[:8], faithfulness.name, result.value,
            )

        except Exception:
            logger.warning(
                "Failed to score trace %s with %s", trace.id[:8], faithfulness.name, exc_info=True,
            )

    langfuse.flush()
    logger.info("Assistant scoring complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(score_assistant_traces())
