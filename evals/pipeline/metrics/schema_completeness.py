"""Schema completeness: does structured output have all required fields?"""

import json

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class SchemaCompletenessMetric(BaseMetric):
    """Validates that pipeline structured output contains all required fields."""

    def __init__(self, threshold: float = 0.90):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    @property
    def name(self) -> str:
        return "Schema Completeness"

    @property
    def __name__(self) -> str:
        return "SchemaCompletenessMetric"

    def measure(self, test_case: LLMTestCase) -> float:
        """Check if output JSON has all required fields."""
        try:
            data = json.loads(test_case.actual_output)
        except (json.JSONDecodeError, TypeError):
            self.score = 0.0
            self.reason = "Output is not valid JSON"
            return self.score

        required_review_fields = [
            "title", "abstract", "sections", "citations", "references",
        ]
        required_section_fields = ["theme_id", "label", "content"]

        present = 0
        total = len(required_review_fields)

        for field in required_review_fields:
            if field in data and data[field]:
                present += 1

        # Check sections structure
        sections = data.get("sections", [])
        if sections:
            section_scores = []
            for section in sections:
                section_present = sum(
                    1 for f in required_section_fields
                    if f in section and section[f]
                )
                section_scores.append(
                    section_present / len(required_section_fields),
                )
            avg_section = (
                sum(section_scores) / len(section_scores)
                if section_scores else 0
            )
            self.score = (present / total * 0.6) + (avg_section * 0.4)
        else:
            self.score = present / total * 0.6

        missing = [
            f for f in required_review_fields
            if f not in data or not data[f]
        ]
        if missing:
            self.reason = f"Missing fields: {', '.join(missing)}"
        else:
            self.reason = "All required fields present"

        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.score >= self.threshold
