"""Compute judge concordance between the old (Gemini) and new judge.

Runs the existing golden pipeline output through the same GEval /
safety metrics the regression suite uses, once with the pre-swap
Gemini judge and once with the configured judge (judge.py), and
records the per-metric score delta as a reference point for whether
the new judge diverges meaningfully from the old one.

Usage:
    uv run python -m pipeline.golden.judge_concordance
"""

import json
from pathlib import Path

from deepeval.metrics import BiasMetric, HallucinationMetric, ToxicityMetric
from deepeval.models import GeminiModel
from deepeval.test_case import LLMTestCase
from judge import create_deepeval_judge

from pipeline.metrics.citation_accuracy import create_citation_accuracy_metric
from pipeline.metrics.faithfulness import create_faithfulness_metric
from pipeline.metrics.theme_quality import create_theme_quality_metric
from pipeline.tests.test_review_quality import _build_review_test_case
from pipeline.tests.test_safety import _extract_contexts, _extract_review_text

GOLDEN_DIR = Path(__file__).parent
OUTPUTS_DIR = GOLDEN_DIR / "outputs"
CONCORDANCE_PATH = GOLDEN_DIR / "concordance.json"

OLD_JUDGE_MODEL = "gemini-2.5-flash"


def _load_outputs() -> tuple[dict, dict]:
    """Load the golden review and papers outputs."""
    review_path = OUTPUTS_DIR / "review.json"
    papers_path = OUTPUTS_DIR / "papers.json"
    if not review_path.exists() or not papers_path.exists():
        raise FileNotFoundError(
            f"Missing golden outputs in {OUTPUTS_DIR}. Run: make eval-run-pipeline",
        )
    return json.loads(review_path.read_text()), json.loads(papers_path.read_text())


def _build_metric_cases(review_data: dict, papers_data: dict) -> dict[str, tuple]:
    """Build (metric_factory, test_case) pairs for each concordance metric."""
    review_case = _build_review_test_case(review_data, papers_data)

    review_text = _extract_review_text(review_data)
    safety_case_kwargs = {
        "input": "Generate a literature review",
        "actual_output": review_text,
    }

    contexts = _extract_contexts(papers_data)[:50]

    bias_case = LLMTestCase(**safety_case_kwargs)
    toxicity_case = LLMTestCase(**safety_case_kwargs)
    hallucination_case = LLMTestCase(
        input="Generate a literature review",
        actual_output=review_text[:5000],
        context=contexts,
    )

    return {
        "faithfulness": (create_faithfulness_metric, review_case),
        "citation_accuracy": (create_citation_accuracy_metric, review_case),
        "theme_quality": (create_theme_quality_metric, review_case),
        "bias": (lambda model: BiasMetric(model=model, threshold=0.3), bias_case),
        "toxicity": (lambda model: ToxicityMetric(model=model, threshold=0.1), toxicity_case),
        "hallucination": (
            lambda model: HallucinationMetric(model=model, threshold=0.3),
            hallucination_case,
        ),
    }


def compute_concordance() -> dict[str, dict[str, float]]:
    """Score the golden output with both judges and diff the results."""
    review_data, papers_data = _load_outputs()
    metric_cases = _build_metric_cases(review_data, papers_data)

    old_judge = GeminiModel(model=OLD_JUDGE_MODEL)
    new_judge = create_deepeval_judge()

    results: dict[str, dict[str, float]] = {}
    for name, (metric_factory, test_case) in metric_cases.items():
        old_score = metric_factory(old_judge).measure(test_case)
        new_score = metric_factory(new_judge).measure(test_case)
        results[name] = {
            "old_score": old_score,
            "new_score": new_score,
            "abs_diff": abs(old_score - new_score),
        }
    return results


def main() -> None:
    """Compute concordance and persist to concordance.json."""
    results = compute_concordance()
    CONCORDANCE_PATH.write_text(json.dumps(results, indent=2))
    print(f"Concordance written: {CONCORDANCE_PATH}")
    for name, scores in results.items():
        print(
            f"  {name}: old={scores['old_score']:.3f} "
            f"new={scores['new_score']:.3f} diff={scores['abs_diff']:.3f}",
        )


if __name__ == "__main__":
    main()
