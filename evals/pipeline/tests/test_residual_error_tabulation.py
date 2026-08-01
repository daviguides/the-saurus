"""Unit tests for residual-error tabulation (evals/pipeline/golden/residual_error.py).

Pure YAML-parsing logic, no LLM calls, no fixtures/credentials required —
runs standalone with `uv run pytest evals/pipeline/tests/test_residual_error_tabulation.py -v`.
"""

from pathlib import Path

import yaml

from pipeline.golden.residual_error import tabulate_residual_error


def _write_theme_review(dir_path: Path, theme_id: str, data: dict) -> None:
    (dir_path / f"{theme_id}.yaml").write_text(yaml.safe_dump({"theme_id": theme_id, **data}))


class TestTabulateResidualError:
    def test_all_grounded_is_no_go(self, tmp_path: Path) -> None:
        """All-grounded synthesis, no NLI downgrades -> zero counts, NO-GO."""
        _write_theme_review(
            tmp_path,
            "t1",
            {
                "synthesis_grounding": [
                    {"sentence": "A.", "verdict": "grounded", "resolved_by": "deberta"},
                    {"sentence": "B.", "verdict": "grounded", "resolved_by": "llm_as_nli"},
                ],
                "gaps": ["Neither paper examines X."],
            },
        )

        result = tabulate_residual_error(tmp_path)

        assert result["total_sentences"] == 2
        assert result["total_grounded"] == 2
        assert result["total_contradicted"] == 0
        assert result["total_nli_downgrades"] == 0
        assert result["verdict"] == "NO-GO"

    def test_contradicted_sentence_triggers_go(self, tmp_path: Path) -> None:
        """A single surviving contradicted sentence flips the verdict to GO."""
        _write_theme_review(
            tmp_path,
            "t1",
            {
                "synthesis_grounding": [
                    {"sentence": "A.", "verdict": "grounded", "resolved_by": "deberta"},
                    {"sentence": "B.", "verdict": "contradicted", "resolved_by": "llm_as_nli"},
                ],
                "gaps": [],
            },
        )

        result = tabulate_residual_error(tmp_path)

        assert result["total_contradicted"] == 1
        assert result["contradicted_rate"] == 0.5
        assert result["verdict"] == "GO"

    def test_nli_downgrade_triggers_go(self, tmp_path: Path) -> None:
        """A consensus/disagreement NLI downgrade alone also justifies GO."""
        _write_theme_review(
            tmp_path,
            "t1",
            {
                "synthesis_grounding": [
                    {"sentence": "A.", "verdict": "grounded", "resolved_by": "deberta"},
                ],
                "gaps": ["Not verified as consensus: Three papers agree on Z."],
            },
        )

        result = tabulate_residual_error(tmp_path)

        assert result["total_contradicted"] == 0
        assert result["total_nli_downgrades"] == 1
        assert result["verdict"] == "GO"

    def test_empty_synthesis_grounding_does_not_crash(self, tmp_path: Path) -> None:
        """A theme with no claims has an empty synthesis_grounding list (theme_reviewer.py:108-109)."""
        _write_theme_review(tmp_path, "t1", {"synthesis_grounding": [], "gaps": []})

        result = tabulate_residual_error(tmp_path)

        assert result["total_sentences"] == 0
        assert result["contradicted_rate"] == 0.0
        assert result["verdict"] == "NO-GO"

    def test_missing_fields_default_to_empty(self, tmp_path: Path) -> None:
        """A theme review dict missing synthesis_grounding/gaps keys entirely is tolerated."""
        _write_theme_review(tmp_path, "t1", {})

        result = tabulate_residual_error(tmp_path)

        assert result["total_sentences"] == 0
        assert result["total_nli_downgrades"] == 0
        assert result["verdict"] == "NO-GO"

    def test_aggregates_across_multiple_themes(self, tmp_path: Path) -> None:
        """Per-theme breakdown and aggregate totals both reflect all files in the dir."""
        _write_theme_review(
            tmp_path,
            "t1",
            {"synthesis_grounding": [{"sentence": "A.", "verdict": "grounded"}], "gaps": []},
        )
        _write_theme_review(
            tmp_path,
            "t2",
            {"synthesis_grounding": [{"sentence": "B.", "verdict": "contradicted"}], "gaps": []},
        )

        result = tabulate_residual_error(tmp_path)

        assert result["themes_measured"] == 2
        assert result["total_sentences"] == 2
        assert result["total_grounded"] == 1
        assert result["total_contradicted"] == 1
        assert result["verdict"] == "GO"

    def test_missing_directory_returns_empty_result(self, tmp_path: Path) -> None:
        """A nonexistent theme_reviews dir tabulates as zero, not a crash."""
        result = tabulate_residual_error(tmp_path / "does_not_exist")

        assert result["themes_measured"] == 0
        assert result["verdict"] == "NO-GO"
