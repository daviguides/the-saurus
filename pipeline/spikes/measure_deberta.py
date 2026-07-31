"""DeBERTa-v3 MNLI cross-encoder spike: footprint + CPU latency.

Run inside spikes/.venv-deberta (Python 3.14, matches pipeline/Dockerfile).
Inputs mirror theme_dedup.py:66-70's "{name} — {description}" pair format.
"""

from __future__ import annotations

import json
import statistics
import time

import torch
from sentence_transformers import CrossEncoder

torch.set_num_threads(1)  # match the Helm pod's 1-CPU limit

MODEL_NAME = "cross-encoder/nli-deberta-v3-base"

# Representative theme name/description pairs — mix of clear-duplicate and
# clearly-distinct, matching the shape theme_dedup.py builds from real themes.
PAIRS = [
    (
        "Exercise improves cognitive function",
        "Regular physical exercise improves cognitive function",
    ),
    (
        "Circadian rhythm affects memory consolidation",
        "Sleep-wake cycles influence how memories are consolidated",
    ),
    (
        "Aerobic exercise reduces inflammation markers",
        "Cardiovascular exercise is associated with lower systemic inflammation",
    ),
    (
        "Meditation reduces cortisol levels",
        "Mindfulness practice is linked to reduced stress hormone levels",
    ),
    (
        "Exercise improves cognitive function",
        "Circadian rhythm affects memory consolidation",
    ),
    (
        "Aerobic exercise reduces inflammation markers",
        "Meditation reduces cortisol levels",
    ),
    (
        "Sleep deprivation impairs working memory",
        "Lack of sleep negatively affects short-term memory performance",
    ),
    (
        "Sleep deprivation impairs working memory",
        "Exercise improves cognitive function",
    ),
    (
        "High-intensity interval training increases BDNF levels",
        "HIIT protocols elevate brain-derived neurotrophic factor",
    ),
    (
        "High-intensity interval training increases BDNF levels",
        "Meditation reduces cortisol levels",
    ),
    (
        "Chronic stress accelerates telomere shortening",
        "Long-term stress exposure is associated with shorter telomeres",
    ),
    (
        "Chronic stress accelerates telomere shortening",
        "Aerobic exercise reduces inflammation markers",
    ),
    (
        "Omega-3 supplementation improves mood in depression",
        "Fish oil supplements are linked to improved depressive symptoms",
    ),
    (
        "Omega-3 supplementation improves mood in depression",
        "Sleep deprivation impairs working memory",
    ),
    (
        "Gut microbiome diversity correlates with immune resilience",
        "A more diverse gut microbiota is associated with stronger immune response",
    ),
]

N_WARMUP = 3
N_REPEAT = 20


def main() -> None:
    model = CrossEncoder(MODEL_NAME)

    # Warmup — exclude cold-start (weight materialization, kernel dispatch) from latency.
    for _ in range(N_WARMUP):
        model.predict(PAIRS)

    # Both directions per pair (§6.1: entailment isn't guaranteed symmetric).
    forward_pairs = PAIRS
    backward_pairs = [(b, a) for a, b in PAIRS]

    per_pair_latencies_ms: list[float] = []
    for _ in range(N_REPEAT):
        for a, b in forward_pairs + backward_pairs:
            start = time.perf_counter()
            model.predict([(a, b)])
            per_pair_latencies_ms.append((time.perf_counter() - start) * 1000)

    per_pair_latencies_ms.sort()
    p50 = statistics.median(per_pair_latencies_ms)
    p95 = per_pair_latencies_ms[int(len(per_pair_latencies_ms) * 0.95)]

    # Sanity spot-check: near-duplicate pair should score high entailment,
    # clearly-distinct pair should not.
    dup_scores = model.predict([PAIRS[0]])
    distinct_scores = model.predict([PAIRS[4]])

    result = {
        "model": MODEL_NAME,
        "n_pairs_per_direction": len(PAIRS),
        "n_repeat": N_REPEAT,
        "single_pair_latency_ms": {
            "p50": round(p50, 3),
            "p95": round(p95, 3),
            "min": round(min(per_pair_latencies_ms), 3),
            "max": round(max(per_pair_latencies_ms), 3),
        },
        "sanity_check": {
            "near_duplicate_pair_scores": dup_scores.tolist(),
            "clearly_distinct_pair_scores": distinct_scores.tolist(),
            "label_order": "contradiction, entailment, neutral",
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
