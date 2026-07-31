"""Pipeline review quality evaluation tests.

Runs DeepEval metrics against the latest pipeline output
to validate review quality and catch regressions.
"""

import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from pipeline.metrics.faithfulness import create_faithfulness_metric
from pipeline.metrics.citation_accuracy import create_citation_accuracy_metric
from pipeline.metrics.theme_quality import create_theme_quality_metric
from pipeline.metrics.schema_completeness import SchemaCompletenessMetric

OUTPUTS_DIR = Path(__file__).parents[1] / "golden" / "outputs"


@pytest.fixture(scope="module")
def review_output():
    """Load latest pipeline review output."""
    path = OUTPUTS_DIR / "review.json"
    if not path.exists():
        pytest.skip("No pipeline output. Run: make eval-run-pipeline")
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def papers_output():
    """Load latest pipeline papers output."""
    path = OUTPUTS_DIR / "papers.json"
    if not path.exists():
        pytest.skip("No pipeline output. Run: make eval-run-pipeline")
    return json.loads(path.read_text())


def _build_review_test_case(
    review_data: dict,
    papers_data: dict,
) -> LLMTestCase:
    """Build a test case from pipeline outputs."""
    review = review_data.get("review", review_data)
    sections_text = "\n\n".join(
        f"## {s.get('label', '')}\n{s.get('content', '')}"
        for s in review.get("sections", [])
    )
    # Build references section
    references_text = ""
    references = review.get("references", [])
    if references:
        refs = "\n".join(
            f"[{r.get('ref_number', i+1)}] {r.get('paper_title', '')}"
            for i, r in enumerate(references)
        )
        references_text = f"\n\n## References\n{refs}"

    full_review = (
        f"# {review.get('title', '')}\n\n"
        f"{review.get('abstract', '')}\n\n"
        f"{sections_text}"
        f"{references_text}"
    )

    # Build context from paper claims
    contexts = []
    for paper in papers_data.get("papers", []):
        claims = paper.get("claims", [])
        for claim in claims:
            contexts.append(
                f"[{paper.get('title', '')}] {claim.get('text', '')}",
            )

    return LLMTestCase(
        input="Generate a comprehensive literature review",
        actual_output=full_review,
        retrieval_context=contexts,
        expected_output=json.dumps(review),
    )


@pytest.mark.eval
class TestReviewQuality:
    """Evaluate pipeline review output quality."""

    def test_faithfulness(
        self, review_output, papers_output, eval_judge, pipeline_baseline,
    ):
        """Review claims are grounded in source papers."""
        metric = create_faithfulness_metric(
            model=eval_judge,
            threshold=pipeline_baseline["faithfulness"] * 0.95,
        )
        test_case = _build_review_test_case(review_output, papers_output)
        assert_test(test_case, [metric])

    def test_citation_accuracy(
        self, review_output, papers_output, eval_judge, pipeline_baseline,
    ):
        """Inline citations resolve to real papers."""
        metric = create_citation_accuracy_metric(
            model=eval_judge,
            threshold=pipeline_baseline["citation_accuracy"] * 0.95,
        )
        test_case = _build_review_test_case(review_output, papers_output)
        assert_test(test_case, [metric])

    def test_theme_quality(
        self, review_output, papers_output, eval_judge, pipeline_baseline,
    ):
        """Themes are meaningful and non-redundant."""
        metric = create_theme_quality_metric(
            model=eval_judge,
            threshold=pipeline_baseline["theme_quality"] * 0.95,
        )
        test_case = _build_review_test_case(review_output, papers_output)
        assert_test(test_case, [metric])

    def test_schema_completeness(
        self, review_output, papers_output, pipeline_baseline,
    ):
        """Review JSON has all required fields."""
        review = review_output.get("review", review_output)
        test_case = LLMTestCase(
            input="Generate a literature review",
            actual_output=json.dumps(review),
        )
        metric = SchemaCompletenessMetric(
            threshold=pipeline_baseline["schema_completeness"] * 0.95,
        )
        assert_test(test_case, [metric])
