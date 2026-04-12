"""Generate golden evaluation dataset for the assistant.

Creates conversational test cases that exercise the
MCP tools and validate answer quality.

Usage:
    uv run python -m assistant.golden.generate
"""

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent
OUTPUT_PATH = GOLDEN_DIR / "dataset.json"


def generate():
    """Generate conversational golden test cases."""
    dataset = [
        {
            "turns": [
                {
                    "role": "user",
                    "content": "What are the main themes found across all papers?",
                },
            ],
            "expected": {
                "tool_expected": "get_theme_map",
                "content_contains": ["theme"],
                "min_length": 100,
            },
        },
        {
            "turns": [
                {
                    "role": "user",
                    "content": "What do the papers agree on?",
                },
            ],
            "expected": {
                "tool_expected": "get_theme_review",
                "content_contains": ["consensus"],
                "min_length": 50,
            },
        },
        {
            "turns": [
                {
                    "role": "user",
                    "content": "Are there any contradictions between papers?",
                },
            ],
            "expected": {
                "tool_expected": "get_theme_review",
                "content_contains": ["disagree", "contradict", "differ"],
                "min_length": 50,
            },
        },
        {
            "turns": [
                {
                    "role": "user",
                    "content": "What research gaps were identified?",
                },
            ],
            "expected": {
                "tool_expected": "get_theme_review",
                "content_contains": ["gap", "future", "research"],
                "min_length": 50,
            },
        },
        {
            "turns": [
                {
                    "role": "user",
                    "content": "Give me a summary of the generated review.",
                },
            ],
            "expected": {
                "tool_expected": "get_literature_review",
                "content_contains": ["review", "paper"],
                "min_length": 100,
            },
        },
        {
            "turns": [
                {
                    "role": "user",
                    "content": "Search for claims about gene expression.",
                },
            ],
            "expected": {
                "tool_expected": "search_claims",
                "min_length": 30,
            },
        },
    ]

    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
    print(f"Generated {len(dataset)} assistant test cases -> {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
