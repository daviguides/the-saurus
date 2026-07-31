"""Batch scoring for pipeline production traces.

Fetches traces from Langfuse, evaluates with RAGAS metrics,
and pushes scores back to Langfuse for dashboarding.

Usage:
    uv run python -m scoring.pipeline_scorer
"""

import asyncio
import json
import logging
import random
from pathlib import Path

from judge import create_ragas_judge

logger = logging.getLogger(__name__)

SAMPLE_RATE = 0.10  # eval 10% of traces

# Deliberately independent from evals/pipeline/golden/baseline.json: that
# baseline is DeepEval GEval Faithfulness scored with retrieval_context
# (source-paper claims). Production traces only carry input/output, so
# this is RAGAS single-turn Faithfulness — a different metric family, not
# a looser version of the same one. Don't try to unify the two numbers.
PRODUCTION_FAITHFULNESS_THRESHOLD = 0.70

MISSES_PATH = Path(__file__).parents[1] / "pipeline" / "golden" / "misses.jsonl"


def _flag_miss(trace_id: str, input_text: str, output_text: str, score: float, metric: str) -> None:
    """Append a low-scoring production trace to the triage inbox."""
    MISSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "trace_id": trace_id,
        "input": input_text,
        "output": output_text,
        "score": score,
        "metric": metric,
    }
    with MISSES_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


async def score_pipeline_traces():
    """Fetch pipeline traces from Langfuse and score with RAGAS."""
    try:
        from langfuse import get_client
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics.collections import Faithfulness, ResponseRelevancy
    except ImportError:
        logger.error("Missing dependencies. Run: cd evals && uv sync")
        return

    langfuse = get_client()
    llm = create_ragas_judge()

    # Fetch recent traces
    traces = langfuse.api.trace.list(name="pipeline").data
    if not traces:
        logger.info("No pipeline traces found in Langfuse")
        return

    # Sample
    sample_size = max(1, int(len(traces) * SAMPLE_RATE))
    sampled = random.sample(traces, min(sample_size, len(traces)))
    logger.info(
        "Scoring %d/%d pipeline traces", len(sampled), len(traces),
    )

    metrics = [Faithfulness(llm=llm), ResponseRelevancy(llm=llm)]

    for trace in sampled:
        try:
            # Extract input/output from trace
            input_text = str(trace.input) if trace.input else ""
            output_text = str(trace.output) if trace.output else ""

            if not input_text or not output_text:
                continue

            for metric in metrics:
                sample = SingleTurnSample(
                    user_input=input_text,
                    response=output_text,
                )
                result = await metric.single_turn_ascore(sample)
                score = result.value if hasattr(result, "value") else float(result)

                langfuse.create_score(
                    name=metric.name,
                    value=score,
                    trace_id=trace.id,
                )
                logger.info(
                    "Scored trace %s: %s=%.3f",
                    trace.id[:8], metric.name, score,
                )

                if metric.name == "faithfulness" and score < PRODUCTION_FAITHFULNESS_THRESHOLD:
                    _flag_miss(trace.id, input_text, output_text, score, metric.name)
                    logger.warning(
                        "Flagged miss: trace %s faithfulness=%.3f < %.2f",
                        trace.id[:8], score, PRODUCTION_FAITHFULNESS_THRESHOLD,
                    )

        except Exception:
            logger.warning(
                "Failed to score trace %s", trace.id[:8], exc_info=True,
            )

    langfuse.flush()
    logger.info("Pipeline scoring complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(score_pipeline_traces())
