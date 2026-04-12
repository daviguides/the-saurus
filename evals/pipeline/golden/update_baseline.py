"""Update the eval baseline from the latest test run.

Reads the most recent eval results and saves them as
the new baseline for regression testing.

Usage:
    uv run python -m pipeline.golden.update_baseline
"""

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent
BASELINE_PATH = GOLDEN_DIR / "baseline.json"
RESULTS_PATH = GOLDEN_DIR / "outputs" / "eval_results.json"


def update():
    """Copy latest eval results as new baseline."""
    if not RESULTS_PATH.exists():
        print(f"No eval results found at {RESULTS_PATH}")
        print("Run evals first: make eval-pipeline")
        return

    results = json.loads(RESULTS_PATH.read_text())
    scores = {k: v for k, v in results.items() if isinstance(v, (int, float))}

    BASELINE_PATH.write_text(json.dumps(scores, indent=2))
    print(f"Baseline updated: {BASELINE_PATH}")
    for name, score in scores.items():
        print(f"  {name}: {score:.3f}")


if __name__ == "__main__":
    update()
