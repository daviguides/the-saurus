"""Runtime judge-scoring endpoint for the pipeline's post-aggregation gate.

Wraps the EXISTING GEval faithfulness/citation-accuracy metrics
(pipeline.metrics.*) and judge factory (judge.py) behind an HTTP endpoint —
no metric or judge logic is reimplemented here. This exists only because the
pipeline service (a separate uv workspace, built from a Docker context that
never includes this evals/ tree) can't import this code directly without
either adding the full eval-suite dependency set to its production image or
renaming files inside pipeline/pipeline/metrics — see the task's research.md/
plan.md for the full reasoning.

Usage:
    uv run python -m scripts.run_judge_gate_service
"""

import asyncio

from deepeval.metrics import ToxicityMetric
from deepeval.test_case import LLMTestCase
from fastapi import FastAPI
from pydantic import BaseModel

from judge import create_deepeval_judge
from pipeline.metrics.citation_accuracy import create_citation_accuracy_metric
from pipeline.metrics.faithfulness import create_faithfulness_metric

# Matches the threshold already validated against this pipeline's real golden-
# set outputs in evals/pipeline/tests/test_safety.py::test_no_toxicity —
# stricter than ToxicityMetric's own package default (0.5). Lower = stricter
# for this metric (opposite of the GEval metrics above).
TOXICITY_THRESHOLD = 0.1

app = FastAPI(title="the-saurus judge-gate")


class ScoreReviewRequest(BaseModel):
    actual_output: str
    retrieval_context: list[str] = []
    expected_output: str = ""


class MetricResult(BaseModel):
    score: float
    passed: bool


class ScoreReviewResponse(BaseModel):
    faithfulness: MetricResult
    citation_accuracy: MetricResult
    verdict: str  # "pass" | "quarantine"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "judge-gate"}


@app.post("/score-review", response_model=ScoreReviewResponse)
async def score_review(request: ScoreReviewRequest) -> ScoreReviewResponse:
    judge = create_deepeval_judge()

    faithfulness_case = LLMTestCase(
        input="Generate a literature review",
        actual_output=request.actual_output,
        retrieval_context=request.retrieval_context,
    )
    citation_case = LLMTestCase(
        input="Generate a literature review",
        actual_output=request.actual_output,
        expected_output=request.expected_output,
    )

    faithfulness_metric = create_faithfulness_metric(model=judge)
    citation_metric = create_citation_accuracy_metric(model=judge)

    await asyncio.gather(
        asyncio.to_thread(faithfulness_metric.measure, faithfulness_case),
        asyncio.to_thread(citation_metric.measure, citation_case),
    )

    faithfulness_result = MetricResult(
        score=faithfulness_metric.score, passed=bool(faithfulness_metric.success)
    )
    citation_result = MetricResult(
        score=citation_metric.score, passed=bool(citation_metric.success)
    )

    verdict = (
        "pass" if faithfulness_result.passed and citation_result.passed else "quarantine"
    )

    return ScoreReviewResponse(
        faithfulness=faithfulness_result,
        citation_accuracy=citation_result,
        verdict=verdict,
    )


class ScoreToxicityRequest(BaseModel):
    text: str


class ScoreToxicityResponse(BaseModel):
    score: float
    passed: bool


@app.post("/score-toxicity", response_model=ScoreToxicityResponse)
async def score_toxicity(request: ScoreToxicityRequest) -> ScoreToxicityResponse:
    judge = create_deepeval_judge()
    metric = ToxicityMetric(model=judge, threshold=TOXICITY_THRESHOLD)
    test_case = LLMTestCase(input="Generate a literature review", actual_output=request.text)

    await asyncio.to_thread(metric.measure, test_case)

    return ScoreToxicityResponse(score=metric.score, passed=bool(metric.success))
