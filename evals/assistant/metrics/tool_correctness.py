"""Tool correctness: did the assistant call the right MCP tool?"""

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class ToolCorrectnessMetric(BaseMetric):
    """Validates that the assistant selected the correct MCP tool."""

    def __init__(
        self,
        expected_tool: str,
        threshold: float = 1.0,
    ):
        self.expected_tool = expected_tool
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    @property
    def name(self) -> str:
        return "Tool Correctness"

    @property
    def __name__(self) -> str:
        return "ToolCorrectnessMetric"

    def measure(self, test_case: LLMTestCase) -> float:
        """Check if the expected tool was called."""
        output = test_case.actual_output or ""

        # Look for tool call indicators in the output
        # The assistant emits step events with tool names
        if self.expected_tool.lower() in output.lower():
            self.score = 1.0
            self.reason = (
                f"Correct tool '{self.expected_tool}' was used"
            )
        else:
            self.score = 0.0
            self.reason = (
                f"Expected tool '{self.expected_tool}' not found in output"
            )

        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.score >= self.threshold
