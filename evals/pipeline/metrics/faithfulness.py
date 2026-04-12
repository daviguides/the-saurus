"""Faithfulness metric: do generated claims cite source papers?"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_faithfulness_metric(model, threshold: float = 0.70):
    """Create a faithfulness metric for literature review evaluation.

    Checks that every claim in the review is grounded in
    the source paper content provided as context.
    """
    return GEval(
        name="Faithfulness",
        model=model,
        criteria=(
            "Evaluate whether every factual claim in the review output "
            "is supported by evidence from the source paper contexts. "
            "A faithful review only contains statements that can be "
            "traced back to the provided contexts. Score 1.0 if all "
            "claims are grounded, 0.0 if none are."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
        threshold=threshold,
    )
