"""Assistant RAG quality evaluation tests.

Validates that assistant answers are relevant and grounded
in the pipeline outputs accessed via MCP tools.
"""

import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from assistant.metrics.answer_relevancy import create_answer_relevancy_metric

GOLDEN_DIR = Path(__file__).parents[1] / "golden"


@pytest.fixture(scope="module")
def golden_dataset():
    """Load assistant golden test cases."""
    path = GOLDEN_DIR / "dataset.json"
    if not path.exists():
        pytest.skip("No golden dataset. Run: make eval-generate-assistant")
    return json.loads(path.read_text())


@pytest.mark.eval
class TestAssistantRAGQuality:
    """Evaluate assistant answer quality."""

    def test_answer_relevancy(
        self, golden_dataset, gemini_judge, assistant_baseline,
    ):
        """Assistant answers are relevant to user questions."""
        metric = create_answer_relevancy_metric(
            model=gemini_judge,
            threshold=assistant_baseline["answer_relevancy"] * 0.95,
        )

        # This is a placeholder structure.
        # In a full implementation, you would:
        # 1. Send each question to the assistant via Socket.IO
        # 2. Capture the response
        # 3. Build test cases from real responses
        for case in golden_dataset:
            question = case["turns"][0]["content"]
            # For now, skip if no captured output exists
            pytest.skip(
                "Assistant output capture not yet implemented. "
                "Run the assistant and capture responses first."
            )
