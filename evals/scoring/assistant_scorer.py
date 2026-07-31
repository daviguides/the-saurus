"""Batch scoring for assistant production traces.

Fetches traces from Langfuse, evaluates with RAGAS metrics,
and pushes scores back for dashboarding.

Usage:
    uv run python -m scoring.assistant_scorer
"""

import asyncio
import logging
import random

from judge import create_ragas_judge

logger = logging.getLogger(__name__)

SAMPLE_RATE = 0.10


async def score_assistant_traces():
    """Fetch assistant traces from Langfuse and score."""
    try:
        from langfuse import get_client
        from ragas.metrics.collections import ResponseRelevancy
        from ragas.dataset_schema import SingleTurnSample
    except ImportError:
        logger.error("Missing dependencies. Run: cd evals && uv sync")
        return

    langfuse = get_client()
    llm = create_ragas_judge()

    traces = langfuse.api.trace.list(name="assistant").data
    if not traces:
        logger.info("No assistant traces found in Langfuse")
        return

    sample_size = max(1, int(len(traces) * SAMPLE_RATE))
    sampled = random.sample(traces, min(sample_size, len(traces)))
    logger.info(
        "Scoring %d/%d assistant traces", len(sampled), len(traces),
    )

    metric = ResponseRelevancy(llm=llm)

    for trace in sampled:
        try:
            input_text = str(trace.input) if trace.input else ""
            output_text = str(trace.output) if trace.output else ""

            if not input_text or not output_text:
                continue

            sample = SingleTurnSample(
                user_input=input_text,
                response=output_text,
            )
            result = await metric.single_turn_ascore(sample)

            langfuse.create_score(
                name=metric.name,
                value=result.value if hasattr(result, "value") else float(result),
                trace_id=trace.id,
            )

        except Exception:
            logger.warning(
                "Failed to score trace %s", trace.id[:8], exc_info=True,
            )

    langfuse.flush()
    logger.info("Assistant scoring complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(score_assistant_traces())
