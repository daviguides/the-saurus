"""Measure residual error after theme_reviewer's Tiers 0-2 hallucination
cascade (reask -> DeBERTa Tier 0.5 -> LLM-as-NLI escalation, M4-T1..T8),
to decide whether the §5.7 Validator Agent (evidence-gated, d-011) is
justified.

Reads per-theme review output already persisted by the pipeline
(`jobs/{job_id}/theme_reviews/*.yaml`) and tabulates two residual-error
signals that are already computed by Tiers 0-2 but never counted:

- `synthesis_grounding` verdicts: a `contradicted` entry means a synthesis
  sentence survived reask, DeBERTa, AND (if borderline) the LLM-as-NLI
  escalation still flagging it as contradicted.
- `gaps` entries prefixed "Not verified as " (theme_reviewer.py:347): a
  consensus/disagreement claim the model asserted that the §5.2 LLM-as-NLI
  check could not confirm.

No LLM calls are made here — this script only reads YAML a prior live
pipeline run already wrote to disk. The credential cost lives entirely in
producing that prior run (`make eval-run-pipeline`), not in this script.

Usage:
    uv run python -m pipeline.golden.residual_error [job_id]

If job_id is omitted, the most-recently-modified subdirectory of the jobs
directory is used. This assumes no concurrent unrelated jobs are running
at measurement time — run this immediately after a fresh
`make eval-run-pipeline`, not against a shared/long-lived jobs directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

GOLDEN_DIR = Path(__file__).parent
DEFAULT_JOBS_DIR = GOLDEN_DIR.parents[2] / "pipeline" / "jobs"

NLI_DOWNGRADE_PREFIX = "Not verified as "


def _find_latest_job(jobs_dir: Path) -> Path:
    """Return the most-recently-modified job subdirectory under jobs_dir."""
    if not jobs_dir.exists():
        raise FileNotFoundError(
            f"No jobs directory at {jobs_dir}. Run: make eval-run-pipeline"
        )
    job_dirs = [p for p in jobs_dir.iterdir() if p.is_dir()]
    if not job_dirs:
        raise FileNotFoundError(
            f"No jobs found in {jobs_dir}. Run: make eval-run-pipeline"
        )
    return max(job_dirs, key=lambda p: p.stat().st_mtime)


def tabulate_residual_error(theme_reviews_dir: Path) -> dict[str, Any]:
    """Tabulate residual grounding/NLI-downgrade error across a job's theme reviews.

    Returns per-theme breakdown, aggregate counts/rates, and a GO/NO-GO
    verdict against the zero-tolerance threshold: any survivor past the
    full Tiers 0-2 cascade justifies the Validator Agent (see plan.md for
    the reasoning — Tiers 0-2 exist specifically to drive these to zero
    within their own failure signature).
    """
    per_theme: list[dict[str, Any]] = []
    total_sentences = 0
    total_grounded = 0
    total_contradicted = 0
    resolved_by_counts: dict[str, int] = {"deberta": 0, "llm_as_nli": 0}
    total_nli_downgrades = 0

    yaml_paths = sorted(theme_reviews_dir.glob("*.yaml")) if theme_reviews_dir.exists() else []

    for path in yaml_paths:
        review = yaml.safe_load(path.read_text()) or {}
        theme_id = review.get("theme_id", path.stem)

        grounding = review.get("synthesis_grounding") or []
        theme_grounded = sum(1 for g in grounding if g.get("verdict") == "grounded")
        theme_contradicted = sum(1 for g in grounding if g.get("verdict") == "contradicted")
        for g in grounding:
            resolved_by = g.get("resolved_by")
            if resolved_by in resolved_by_counts:
                resolved_by_counts[resolved_by] += 1

        gaps = review.get("gaps") or []
        theme_downgrades = sum(1 for entry in gaps if entry.startswith(NLI_DOWNGRADE_PREFIX))

        per_theme.append({
            "theme_id": theme_id,
            "sentences": len(grounding),
            "grounded": theme_grounded,
            "contradicted": theme_contradicted,
            "nli_downgrades": theme_downgrades,
        })

        total_sentences += len(grounding)
        total_grounded += theme_grounded
        total_contradicted += theme_contradicted
        total_nli_downgrades += theme_downgrades

    contradicted_rate = total_contradicted / total_sentences if total_sentences else 0.0
    verdict = "GO" if (total_contradicted > 0 or total_nli_downgrades > 0) else "NO-GO"

    return {
        "themes_measured": len(per_theme),
        "per_theme": per_theme,
        "total_sentences": total_sentences,
        "total_grounded": total_grounded,
        "total_contradicted": total_contradicted,
        "contradicted_rate": contradicted_rate,
        "resolved_by": resolved_by_counts,
        "total_nli_downgrades": total_nli_downgrades,
        "verdict": verdict,
    }


def main(argv: list[str]) -> None:
    """CLI entry: measure residual error for a job, print a summary."""
    jobs_dir = DEFAULT_JOBS_DIR
    if len(argv) > 1:
        job_dir = jobs_dir / argv[1]
        if not job_dir.exists():
            raise FileNotFoundError(f"No job {argv[1]!r} in {jobs_dir}")
    else:
        job_dir = _find_latest_job(jobs_dir)

    result = tabulate_residual_error(job_dir / "theme_reviews")

    print(f"Job: {job_dir.name}")
    print(f"Themes measured: {result['themes_measured']}")
    print(
        f"Sentences: {result['total_sentences']} total, "
        f"{result['total_grounded']} grounded, "
        f"{result['total_contradicted']} contradicted "
        f"(rate={result['contradicted_rate']:.3f})"
    )
    print(f"Resolved by: {result['resolved_by']}")
    print(f"Consensus/disagreement NLI downgrades: {result['total_nli_downgrades']}")
    print(f"Verdict: {result['verdict']}")
    print()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(sys.argv)
