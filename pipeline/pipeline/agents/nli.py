"""Local NLI cross-encoder wrappers: DeBERTa-v3 MNLI, two distinct jobs.

`GroundingClassifier` is a cheap, non-LLM pre-filter that scores whether a
theme_reviewer synthesis sentence is entailed by the theme's evidence claims,
ahead of the (costlier) LLM-as-NLI escalation tier. Design doc §5.4; go/no-go
+ checkpoint from the M1-T5 spike (spikes/local_model_viability.md §1) —
repurposes DeBERTa in place of the NO-GO AlignScore (d-017 revises d-004).

`GroupEquivalenceVerifier` verifies whether theme_dedup.py's LLM-proposed
groups are actually semantically equivalent (§6.1) — a genuinely distinct
job from grounding (§5.3), sharing only the underlying checkpoint.

Each caller constructs its own instance — no shared/singleton model load
across call sites (d-019). This module is the reusable *code* (including
the shared lazy-load helper below); instance ownership stays with the
caller (theme_reviewer.py for GroundingClassifier, theme_dedup.py for
GroupEquivalenceVerifier).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MODEL_NAME = "cross-encoder/nli-deberta-v3-base"

# Starting thresholds, not tuned against a labeled dev set — see plan.md.
# Justified by the M1-T5 spike's own grounded-vs-non-grounded separation
# (0.945 vs ~0.000 entailment probability on its 4-pair smoke comparison),
# which leaves wide headroom around 0.7 on both sides.
ENTAILMENT_CONFIDENT = 0.7
CONTRADICTION_CONFIDENT = 0.7

# Flag a theme-dedup group only when BOTH directions predict contradiction
# at/above this — design doc §6.1's parenthetical ("both directions failing
# is the strong signal worth acting on"). Not calibrated against a labeled
# set, same status as ENTAILMENT_CONFIDENT/CONTRADICTION_CONFIDENT above.
GROUP_CONTRADICTION_THRESHOLD = 0.5

# Simple boundary split — the design doc states this check "doesn't need ML"
# (§5.4). Known limitation: doesn't special-case abbreviations (e.g. "Dr.");
# acceptable per the design doc's explicit call for a non-ML splitter here.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences on `.`/`!`/`?` boundaries."""
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


@dataclass
class SentenceGroundingResult:
    """Grounding verdict for one synthesis sentence."""

    sentence: str
    verdict: str  # "grounded" | "contradicted" | "borderline"
    best_claim_id: str | None
    scores: dict[str, float]  # {"contradiction": .., "entailment": .., "neutral": ..}
    resolved_by: str = "deberta"  # "deberta" | "llm_as_nli" — which tier produced `verdict`


def _load_cross_encoder(model_name: str) -> tuple[Any, list[str]]:
    """Load a fresh CrossEncoder + its label order from the model's own config.

    Called once per caller-owned instance (d-019 — no shared/singleton model
    load across call sites; each caller gets its own CrossEncoder object).
    torch + sentence_transformers are imported here, not at module top level:
    `import pipeline.agents.*` must stay cheap for callers that never
    construct a classifier/verifier — a top-level import costs 130-300s
    wall-clock and blew the test budget.
    """
    import torch
    from sentence_transformers import CrossEncoder

    torch.set_num_threads(1)  # match the pod's 1-CPU limit (spike methodology)
    model = CrossEncoder(model_name)
    id2label = model.config.id2label
    label_order = [id2label[i] for i in sorted(id2label)]
    return model, label_order


class GroundingClassifier:
    """Wraps a DeBERTa-v3 MNLI cross-encoder for premise/hypothesis entailment scoring."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self._model, self._label_order = _load_cross_encoder(model_name)

    def _score_pairs(self, pairs: list[tuple[str, str]]) -> list[dict[str, float]]:
        """Run pairs through the model, return softmax probabilities per label."""
        probs = self._model.predict(pairs, apply_softmax=True)
        return [
            {label: float(p) for label, p in zip(self._label_order, row, strict=True)}
            for row in probs
        ]

    def classify_synthesis(
        self,
        synthesis: str,
        claims: list[dict[str, Any]],
    ) -> list[SentenceGroundingResult]:
        """Score each sentence vs every claim (premise=claim, hypothesis=sentence).

        A sentence is grounded if ANY claim entails it (design doc §5.4).
        One batched predict() call for the whole synthesis, not one per pair.
        """
        sentences = split_sentences(synthesis)
        if not sentences or not claims:
            return []

        claim_texts = [c.get("summary", c.get("text", "")) for c in claims]
        pairs = [(claim_text, sentence) for sentence in sentences for claim_text in claim_texts]
        scored = self._score_pairs(pairs)

        results: list[SentenceGroundingResult] = []
        n_claims = len(claims)
        for si, sentence in enumerate(sentences):
            row_scores = scored[si * n_claims : (si + 1) * n_claims]

            # "Grounded" and "contradicted" are independent questions — the
            # claim that most strongly entails a sentence is not necessarily
            # the same claim that most strongly contradicts it, so each is
            # judged against its own best-matching claim, not one shared pick.
            entail_idx = max(range(n_claims), key=lambda i: row_scores[i]["entailment"])
            contra_idx = max(range(n_claims), key=lambda i: row_scores[i]["contradiction"])

            if row_scores[entail_idx]["entailment"] >= ENTAILMENT_CONFIDENT:
                verdict = "grounded"
                best_idx = entail_idx
            elif row_scores[contra_idx]["contradiction"] >= CONTRADICTION_CONFIDENT:
                verdict = "contradicted"
                best_idx = contra_idx
            else:
                verdict = "borderline"
                best_idx = entail_idx

            best = row_scores[best_idx]
            best_claim_id = claims[best_idx].get("id")
            results.append(SentenceGroundingResult(sentence, verdict, best_claim_id, best))

        return results


class GroupEquivalenceVerifier:
    """Wraps a DeBERTa-v3 MNLI cross-encoder for theme-dedup group verification.

    Distinct job from GroundingClassifier (§5.3): verifies whether member
    themes an LLM grouped together are actually semantically equivalent, not
    whether a synthesis is grounded in evidence claims. Own independent
    instance — d-019, no shared/singleton model load with GroundingClassifier.
    """

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self._model, label_order = _load_cross_encoder(model_name)
        self._contradiction_idx = label_order.index("contradiction")

    def contradiction_probs(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Batch-predict P(contradiction) for each (premise, hypothesis) pair.

        One batched predict() call for the whole input, not one per pair.
        """
        if not pairs:
            return []
        probs = self._model.predict(pairs, apply_softmax=True)
        return [float(row[self._contradiction_idx]) for row in probs]
