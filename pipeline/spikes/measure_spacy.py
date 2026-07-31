"""spaCy NER spike: footprint + CPU latency, paragraph-granularity input
matching ingestion/extract.py's Paragraph.text (Presidio's NER backend).
"""

from __future__ import annotations

import json
import resource
import statistics
import time

import spacy

MODEL_NAME = "en_core_web_sm"

# Representative paragraph-length texts, mixing bibliographic/author-name
# content (§3.1's non-bibliographic-entity scoping concern) with plain body text.
PARAGRAPHS = [
    "Smith et al. (2023) conducted a randomized controlled trial with 240 "
    "participants recruited from three academic medical centers in Boston, "
    "Massachusetts. Participants were randomized 1:1 to receive either a "
    "12-week structured aerobic exercise program or standard care.",
    "The authors thank Dr. Jane Rodriguez and the clinical staff at Northwestern "
    "Memorial Hospital for their assistance with participant recruitment. "
    "Correspondence should be addressed to j.rodriguez@example.edu.",
    "Cognitive function was assessed using the Montreal Cognitive Assessment "
    "(MoCA) at baseline and at 12-week follow-up. Secondary outcomes included "
    "serum BDNF levels and self-reported sleep quality via the Pittsburgh "
    "Sleep Quality Index.",
    "Results indicated a statistically significant improvement in MoCA scores "
    "in the exercise group compared to controls (mean difference 2.1 points, "
    "95% CI 1.2-3.0, p<0.001), consistent with prior findings from Chen and "
    "Okafor's 2021 meta-analysis.",
    "This work was supported by a grant from the National Institutes of Health "
    "(R01AG012345) awarded to Dr. Michael Tanaka, and by the Alzheimer's "
    "Association (AARF-22-800000).",
    "Limitations of this study include a relatively short follow-up period and "
    "a sample drawn primarily from urban academic medical centers, which may "
    "limit generalizability to broader populations.",
    "Data collection took place between March 2022 and August 2023. All "
    "procedures were approved by the Institutional Review Board (protocol "
    "#2022-0451) and participants provided written informed consent.",
    "The exercise intervention consisted of three 45-minute sessions per week, "
    "supervised by certified exercise physiologists, targeting 65-75% of "
    "age-predicted maximum heart rate.",
    "Please direct all inquiries to the corresponding author at 617-555-0142 "
    "or via the study coordinator's office at Massachusetts General Hospital, "
    "55 Fruit Street, Boston, MA 02114.",
    "Sensitivity analyses excluding participants with baseline MoCA scores "
    "below 24 did not materially change the direction or magnitude of the "
    "primary outcome.",
]

N_WARMUP = 3
N_REPEAT = 20


def main() -> None:
    nlp = spacy.load(MODEL_NAME)

    for _ in range(N_WARMUP):
        for text in PARAGRAPHS:
            nlp(text)

    latencies_ms: list[float] = []
    for _ in range(N_REPEAT):
        for text in PARAGRAPHS:
            start = time.perf_counter()
            nlp(text)
            latencies_ms.append((time.perf_counter() - start) * 1000)

    latencies_ms.sort()
    p50 = statistics.median(latencies_ms)
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]

    # Sanity check: what entity types actually get detected on the
    # PII-relevant + bibliographic-mixed paragraph (index 1).
    doc = nlp(PARAGRAPHS[1])
    entities = [(ent.text, ent.label_) for ent in doc.ents]

    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)

    result = {
        "model": MODEL_NAME,
        "n_paragraphs": len(PARAGRAPHS),
        "n_repeat": N_REPEAT,
        "per_paragraph_latency_ms": {
            "p50": round(p50, 3),
            "p95": round(p95, 3),
            "min": round(min(latencies_ms), 3),
            "max": round(max(latencies_ms), 3),
        },
        "peak_rss_mb": round(peak_rss_mb, 1),
        "sanity_check_entities": entities,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
