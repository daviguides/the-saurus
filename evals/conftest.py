"""Shared fixtures for pipeline and assistant evals."""

import json
import os
from pathlib import Path

import pytest
from deepeval.models import GeminiModel

EVALS_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def gemini_judge():
    """Gemini model used as LLM judge for all evals."""
    return GeminiModel(
        model="gemini-2.5-flash",
        api_key=os.environ.get("GOOGLE_API_KEY", os.environ.get("PIPELINE_LLM_API_KEY", "")),
    )


@pytest.fixture(scope="session")
def pipeline_baseline():
    """Load pipeline eval baseline scores."""
    path = EVALS_DIR / "pipeline" / "golden" / "baseline.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "faithfulness": 0.70,
        "citation_accuracy": 0.70,
        "schema_completeness": 0.90,
        "theme_quality": 0.70,
    }


@pytest.fixture(scope="session")
def assistant_baseline():
    """Load assistant eval baseline scores."""
    path = EVALS_DIR / "assistant" / "golden" / "baseline.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "answer_relevancy": 0.70,
        "tool_correctness": 0.80,
        "knowledge_retention": 0.70,
    }


def load_golden_dataset(service: str) -> list[dict]:
    """Load golden dataset for a service."""
    path = EVALS_DIR / service / "golden" / "dataset.json"
    if path.exists():
        return json.loads(path.read_text())
    return []
