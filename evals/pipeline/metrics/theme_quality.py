"""Theme quality: are extracted themes meaningful and non-redundant?"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_theme_quality_metric(model, threshold: float = 0.70):
    """Create a theme quality metric.

    Evaluates whether extracted themes are meaningful,
    distinct, and representative of the source papers.
    """
    return GEval(
        name="Theme Quality",
        model=model,
        criteria=(
            "Evaluate the quality of extracted themes from scientific papers. "
            "Good themes are: (1) meaningful and specific to the research domain, "
            "(2) distinct from each other with no semantic overlap, "
            "(3) representative of the major topics in the source papers, "
            "(4) neither too broad (e.g., 'science') nor too narrow "
            "(e.g., a single sentence). "
            "Score 1.0 for excellent theme extraction, 0.0 for poor."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
        threshold=threshold,
    )
