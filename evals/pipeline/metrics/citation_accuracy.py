"""Citation accuracy: do [N] refs resolve to real papers?"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_citation_accuracy_metric(model, threshold: float = 0.70):
    """Create a citation accuracy metric.

    Checks that every inline citation [N] in the review
    corresponds to a valid paper in the references section,
    and that the cited content matches the source.
    """
    return GEval(
        name="Citation Accuracy",
        model=model,
        criteria=(
            "Check that every inline citation [N] in the review text "
            "corresponds to a paper listed in the references section. "
            "Verify that the citation number is consistent and that "
            "the cited claim relates to the referenced paper. "
            "Score 1.0 if all citations are valid and accurate, "
            "0.0 if citations are missing, incorrect, or fabricated."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
    )
