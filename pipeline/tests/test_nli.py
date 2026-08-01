"""Tests for the DeBERTa Tier 0.5 grounding pre-filter (nli.py)."""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from pipeline.agents.nli import (
    GroundingClassifier,
    GroupEquivalenceVerifier,
    SentenceGroundingResult,
    split_sentences,
)

# --- split_sentences (pure function, no model) ---


class TestSplitSentences:
    """Simple boundary-based sentence splitting, per design doc §5.4."""

    def test_single_sentence(self) -> None:
        assert split_sentences("Exercise improves cognitive function.") == [
            "Exercise improves cognitive function."
        ]

    def test_multiple_sentences(self) -> None:
        text = "Exercise improves cognitive function. Sleep aids memory consolidation."
        assert split_sentences(text) == [
            "Exercise improves cognitive function.",
            "Sleep aids memory consolidation.",
        ]

    def test_question_and_exclamation_boundaries(self) -> None:
        text = "Does exercise help? Yes, it does! Evidence is strong."
        assert split_sentences(text) == [
            "Does exercise help?",
            "Yes, it does!",
            "Evidence is strong.",
        ]

    def test_empty_string(self) -> None:
        assert split_sentences("") == []

    def test_whitespace_only(self) -> None:
        assert split_sentences("   ") == []

    def test_strips_surrounding_whitespace(self) -> None:
        assert split_sentences("  Exercise helps.  ") == ["Exercise helps."]


# --- GroundingClassifier (mocked CrossEncoder — no real model load) ---


def _mock_cross_encoder(predict_return: list[list[float]]) -> MagicMock:
    """Build a mock CrossEncoder with a fixed id2label mapping and predict() output."""
    mock = MagicMock()
    mock.config.id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}
    mock.predict.return_value = predict_return
    return mock


@contextmanager
def _patch_backends(mock_model: MagicMock):
    """Inject fake torch + sentence_transformers into sys.modules so the lazy
    imports inside GroundingClassifier.__init__ resolve to mocks — without ever
    loading the real (130-300s) heavy deps. Yields the fake torch module for
    assertions on torch.set_num_threads."""
    fake_torch = MagicMock()
    fake_st = types.ModuleType("sentence_transformers")
    fake_st.CrossEncoder = MagicMock(return_value=mock_model)  # type: ignore[attr-defined]
    with patch.dict(sys.modules, {"torch": fake_torch, "sentence_transformers": fake_st}):
        yield fake_torch


class TestGroundingClassifier:
    """classify_synthesis: label order, best-claim selection, thresholds, batching."""

    def test_label_order_read_from_config_not_hardcoded(self) -> None:
        """Label order comes from the model's own id2label, not an assumed order."""
        mock_model = _mock_cross_encoder([[0.05, 0.9, 0.05]])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        assert clf._label_order == ["contradiction", "entailment", "neutral"]

    def test_single_claim_grounded(self) -> None:
        """High entailment probability -> verdict 'grounded'."""
        mock_model = _mock_cross_encoder([[0.02, 0.9, 0.08]])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise improves memory.",
            [{"id": "c1", "summary": "Regular exercise improves memory function."}],
        )

        assert len(results) == 1
        assert results[0] == SentenceGroundingResult(
            sentence="Exercise improves memory.",
            verdict="grounded",
            best_claim_id="c1",
            scores={"contradiction": 0.02, "entailment": 0.9, "neutral": 0.08},
        )

    def test_single_claim_contradicted(self) -> None:
        """High contradiction probability -> verdict 'contradicted'."""
        mock_model = _mock_cross_encoder([[0.9, 0.03, 0.07]])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise has no effect on memory.",
            [{"id": "c1", "summary": "Regular exercise improves memory function."}],
        )

        assert results[0].verdict == "contradicted"
        assert results[0].best_claim_id == "c1"

    def test_ambiguous_score_is_borderline(self) -> None:
        """Neither entailment nor contradiction crosses the confidence threshold -> 'borderline'."""
        mock_model = _mock_cross_encoder([[0.3, 0.4, 0.3]])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise may relate to memory.",
            [{"id": "c1", "summary": "Regular exercise improves memory function."}],
        )

        assert results[0].verdict == "borderline"

    def test_threshold_boundary_exactly_0_7_is_confident(self) -> None:
        """Entailment probability exactly at the threshold counts as confident."""
        mock_model = _mock_cross_encoder([[0.1, 0.7, 0.2]])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise improves memory.",
            [{"id": "c1", "summary": "Exercise improves memory."}],
        )

        assert results[0].verdict == "grounded"

    def test_best_claim_selected_across_multiple_claims(self) -> None:
        """When multiple claims are given, the highest-entailment claim wins."""
        # Two claims for one sentence -> predict() returns 2 rows.
        mock_model = _mock_cross_encoder(
            [
                [0.6, 0.1, 0.3],  # claim c1: low entailment
                [0.02, 0.95, 0.03],  # claim c2: high entailment
            ]
        )
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise improves memory.",
            [
                {"id": "c1", "summary": "Unrelated claim."},
                {"id": "c2", "summary": "Exercise clearly improves memory."},
            ],
        )

        assert len(results) == 1
        assert results[0].best_claim_id == "c2"
        assert results[0].verdict == "grounded"

    def test_multi_sentence_multi_claim_reshaping(self) -> None:
        """Flat pairs-list result reshapes correctly back into per-sentence groups."""
        # 2 sentences x 2 claims = 4 pairs, in sentence-major order:
        # (claim1, sent1), (claim2, sent1), (claim1, sent2), (claim2, sent2)
        mock_model = _mock_cross_encoder(
            [
                [0.02, 0.9, 0.08],  # sent1 vs claim1: grounded
                [0.05, 0.4, 0.55],  # sent1 vs claim2: weaker
                [0.85, 0.05, 0.10],  # sent2 vs claim1: contradicted
                [0.1, 0.2, 0.7],  # sent2 vs claim2: borderline
            ]
        )
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis(
            "Exercise improves memory. Exercise has no cardiovascular benefit.",
            [
                {"id": "c1", "summary": "Claim one."},
                {"id": "c2", "summary": "Claim two."},
            ],
        )

        assert len(results) == 2
        assert results[0].sentence == "Exercise improves memory."
        assert results[0].verdict == "grounded"
        assert results[0].best_claim_id == "c1"

        assert results[1].sentence == "Exercise has no cardiovascular benefit."
        assert results[1].verdict == "contradicted"
        assert results[1].best_claim_id == "c1"

    def test_empty_claims_returns_empty(self) -> None:
        """No claims available -> no pairs to score, empty result."""
        mock_model = _mock_cross_encoder([])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis("Exercise improves memory.", [])

        assert results == []
        mock_model.predict.assert_not_called()

    def test_empty_synthesis_returns_empty(self) -> None:
        """No sentences to check -> empty result, no model call."""
        mock_model = _mock_cross_encoder([])
        with _patch_backends(mock_model):
            clf = GroundingClassifier()

        results = clf.classify_synthesis("", [{"id": "c1", "summary": "Claim."}])

        assert results == []
        mock_model.predict.assert_not_called()

    def test_single_threaded_torch_set(self) -> None:
        """Constructor pins torch to single-threaded, matching the pod's 1-CPU limit."""
        mock_model = _mock_cross_encoder([])
        with _patch_backends(mock_model) as fake_torch:
            GroundingClassifier()

        fake_torch.set_num_threads.assert_called_once_with(1)


# --- GroupEquivalenceVerifier (mocked CrossEncoder — no real model load) ---


class TestGroupEquivalenceVerifier:
    """contradiction_probs: label-order lookup, batching, empty short-circuit."""

    def test_empty_pairs_returns_empty_without_model_call(self) -> None:
        mock_model = _mock_cross_encoder([])
        with _patch_backends(mock_model):
            verifier = GroupEquivalenceVerifier()
            result = verifier.contradiction_probs([])

        assert result == []
        mock_model.predict.assert_not_called()

    def test_extracts_contradiction_index_from_config_label_order(self) -> None:
        mock_model = _mock_cross_encoder([[0.7, 0.2, 0.1], [0.05, 0.9, 0.05]])
        with _patch_backends(mock_model):
            verifier = GroupEquivalenceVerifier()
            result = verifier.contradiction_probs(
                [("theme a", "theme b"), ("theme b", "theme a")]
            )

        assert result == [0.7, 0.05]
        mock_model.predict.assert_called_once_with(
            [("theme a", "theme b"), ("theme b", "theme a")],
            apply_softmax=True,
        )

    def test_label_order_not_hardcoded(self) -> None:
        """Even if id2label order differs, contradiction is read from config."""
        mock_model = MagicMock()
        mock_model.config.id2label = {0: "entailment", 1: "neutral", 2: "contradiction"}
        mock_model.predict.return_value = [[0.1, 0.2, 0.9]]

        with _patch_backends(mock_model):
            verifier = GroupEquivalenceVerifier()
            result = verifier.contradiction_probs([("a", "b")])

        assert result == [0.9]
