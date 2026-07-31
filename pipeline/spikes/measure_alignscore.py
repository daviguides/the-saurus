"""AlignScore spike: footprint + CPU latency, whole-synthesis vs evidence input
matching theme_reviewer.py's SingleThemeReview.synthesis + key_claims shape.

Run inside spikes/.venv-alignscore310 (Python 3.10, AlignScore's as-declared pins).
"""

from __future__ import annotations

import json
import resource
import statistics
import time

import torch

torch.set_num_threads(1)  # match the Helm pod's 1-CPU limit

from alignscore import AlignScore
from huggingface_hub import hf_hub_download

CKPT_PATH = hf_hub_download(repo_id="yzha/AlignScore", filename="AlignScore-base.ckpt")

# (evidence, synthesis) pairs — evidence mirrors concatenated key_claims
# summaries, synthesis mirrors SingleThemeReview.synthesis paragraphs.
PAIRS = [
    (
        "A randomized controlled trial with 240 participants found that a "
        "12-week aerobic exercise program significantly improved MoCA scores "
        "compared to standard care (mean difference 2.1 points, p<0.001). "
        "A separate study found elevated BDNF levels following high-intensity "
        "interval training.",
        "Multiple studies converge on the finding that aerobic exercise "
        "improves cognitive function, with one RCT reporting a statistically "
        "significant 2.1-point improvement in MoCA scores after a 12-week "
        "program, plausibly mediated by exercise-induced increases in BDNF.",
    ),
    (
        "A randomized controlled trial with 240 participants found that a "
        "12-week aerobic exercise program significantly improved MoCA scores "
        "compared to standard care (mean difference 2.1 points, p<0.001).",
        "Exercise has been shown to completely reverse Alzheimer's disease "
        "symptoms within weeks, with all participants achieving full cognitive "
        "recovery regardless of baseline severity.",
    ),
    (
        "Chronic stress exposure is associated with shorter telomeres. "
        "Meditation practice is linked to reduced cortisol levels in "
        "healthy adults.",
        "Chronic stress accelerates cellular aging via telomere shortening, "
        "and mindfulness-based interventions may partially counteract this "
        "through their cortisol-lowering effects, though a direct causal "
        "link between meditation and telomere length was not established "
        "in the reviewed evidence.",
    ),
    (
        "Sleep deprivation impairs working memory performance in healthy "
        "adults, as measured by n-back task accuracy.",
        "Sleep deprivation has no measurable effect on any cognitive domain "
        "and is not associated with working memory impairment.",
    ),
]

N_WARMUP = 1
N_REPEAT = 10


def main() -> None:
    scorer = AlignScore(
        model="roberta-base",
        batch_size=4,
        device="cpu",
        ckpt_path=CKPT_PATH,
        evaluation_mode="nli_sp",
    )

    contexts = [p[0] for p in PAIRS]
    claims = [p[1] for p in PAIRS]

    for _ in range(N_WARMUP):
        scorer.score(contexts=contexts, claims=claims)

    batch_latencies_ms: list[float] = []
    for _ in range(N_REPEAT):
        start = time.perf_counter()
        scores = scorer.score(contexts=contexts, claims=claims)
        batch_latencies_ms.append((time.perf_counter() - start) * 1000)

    batch_latencies_ms.sort()
    p50 = statistics.median(batch_latencies_ms)
    p95 = batch_latencies_ms[int(len(batch_latencies_ms) * 0.95)]

    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)

    result = {
        "model": "AlignScore-base",
        "n_pairs": len(PAIRS),
        "n_repeat": N_REPEAT,
        "batch_of_4_latency_ms": {
            "p50": round(p50, 3),
            "p95": round(p95, 3),
        },
        "per_pair_latency_ms_est": round(p50 / len(PAIRS), 3),
        "peak_rss_mb": round(peak_rss_mb, 1),
        "sanity_check_scores": {
            "grounded_synthesis": round(scores[0], 4),
            "fabricated_synthesis": round(scores[1], 4),
            "partially_grounded_synthesis": round(scores[2], 4),
            "contradicted_synthesis": round(scores[3], 4),
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
