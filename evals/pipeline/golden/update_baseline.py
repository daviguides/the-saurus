"""Update the eval baseline from the latest test run.

Reads deepeval's own test-run artifact — auto-written by every
`deepeval test run` to .deepeval/.latest_test_run.json — and saves
each metric's average score as the new regression baseline.

Usage:
    uv run python -m pipeline.golden.update_baseline
"""

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent
BASELINE_PATH = GOLDEN_DIR / "baseline.json"
EVALS_DIR = GOLDEN_DIR.parent.parent
LATEST_TEST_RUN_PATH = EVALS_DIR / ".deepeval" / ".latest_test_run.json"


def _metric_key(name: str) -> str:
    """Convert a deepeval metric name (e.g. "Citation Accuracy") to a baseline.json key."""
    return name.lower().replace(" ", "_")


def _average_scores(test_run_data: dict) -> dict[str, float]:
    """Average each metric's score across all test cases in a test run."""
    totals: dict[str, list[float]] = {}
    for test_case in test_run_data.get("testCases", []):
        for metric in test_case.get("metricsData") or []:
            score = metric.get("score")
            if score is None:
                continue
            totals.setdefault(_metric_key(metric["name"]), []).append(score)
    return {key: sum(scores) / len(scores) for key, scores in totals.items()}


def update():
    """Fold the latest deepeval test run into the baseline."""
    if not LATEST_TEST_RUN_PATH.exists():
        print(f"No test run found at {LATEST_TEST_RUN_PATH}")
        print("Run evals first: make eval-pipeline")
        return

    data = json.loads(LATEST_TEST_RUN_PATH.read_text())
    scores = _average_scores(data.get("testRunData", data))

    if not scores:
        print(f"No metric scores found in {LATEST_TEST_RUN_PATH}")
        return

    BASELINE_PATH.write_text(json.dumps(scores, indent=2))
    print(f"Baseline updated: {BASELINE_PATH}")
    for name, score in scores.items():
        print(f"  {name}: {score:.3f}")


if __name__ == "__main__":
    update()
