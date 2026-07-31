# Local-Model Viability Spike — DeBERTa-v3 MNLI, AlignScore, spaCy NER

M1-T5 (combined-local-model-viability-spike). Go/no-go gate for M5-T3 (DeBERTa in `theme_dedup.py`), M4-T5 (AlignScore Tier 0.5 in `theme_reviewer.py`), M2-T1/T2 (spaCy NER in Presidio, `extract.py`) before any of the three is added to `pipeline/pyproject.toml`.

**Threshold**: pipeline pod resource limits (`infra/helm/the-saurus/values.yaml:16-22`) — **512Mi request / 1Gi limit memory, 250m request / 1 CPU limit**. All latency measured single-threaded (`torch.set_num_threads(1)`) to match the 1-CPU limit. Runtime target is `python:3.14-slim-bookworm` (`pipeline/Dockerfile:1`).

**Measurement environment caveat**: all numbers below were captured on this dev machine (macOS, Apple Silicon/arm64), not the linux container the pod actually runs. Disk footprint is platform-independent and transfers as-is. Latency numbers are directionally indicative, not exact production numbers — re-verify latency on the actual linux pod once a model reaches integration, but the footprint numbers below are load-bearing for the go/no-go regardless.

Every install below happened in scratch, gitignored venvs under `pipeline/spikes/.venv-*` — `pipeline/pyproject.toml` and `pipeline/uv.lock` are untouched by this spike.

---

## 1. DeBERTa-v3 MNLI cross-encoder (`cross-encoder/nli-deberta-v3-base`) — theme-dedup verification, §6.1

**Install**: `uv venv --python 3.14`, `uv pip install sentence-transformers` — installs cleanly, no wheel gap. Resolved `torch==2.13.0`, `transformers==5.14.1`, `tokenizers==0.22.2`, all with native `cp314` wheels. **This is the actual production target Python version — numbers below transfer directly, no environment caveat needed for this model.**

**Footprint**:
- Disk: venv (torch + transformers + sentence-transformers) = **831MB**; model weights (HF cache) = **714MB**. Total ≈ **1.5GB disk**.
- Peak RSS at inference (load model + 1 prediction): **799MB** (base checkpoint), **1021MB** (xsmall checkpoint). **The smaller checkpoint does not reduce memory** — torch/transformers' own runtime import overhead (~700-1000MB) dominates over the marginal weight-size difference between checkpoint variants. Switching to a smaller DeBERTa checkpoint is not a lever for fitting the memory budget.

**Latency** (single-pair `CrossEncoder.predict`, 15 theme-pairs × both directions × 20 repeats, single-threaded CPU):
- P50: **11.5ms**, P95: **14.1ms**, min **9.1ms**, max 319ms (one cold outlier, excluded from steady-state read).
- xsmall checkpoint: P50 **8.0ms** — modestly faster, not memory-relevant per above.

**Sanity check** (softmax over contradiction/entailment/neutral logits, verified against the model's actual `id2label` mapping, not assumed order):
- Near-duplicate theme pair ("Exercise improves cognitive function" vs "Regular physical exercise improves cognitive function"): entailment **1.9%**, neutral **98.1%**. The model does **not** confidently call this pair "entailment" despite near-identical meaning — MNLI-trained cross-encoders are known to under-call entailment on paraphrases with any lexical variation, landing on "neutral" instead. **Real, measured caveat for M5 integration**: `theme_dedup.py:255`'s proposed rule ("flag if predicted label isn't entailment") would misfire on genuine near-duplicates as tested here. The full 3-way probability distribution (not just argmax) needs a tuned threshold, not a bare label check.
- On the grounding-check repurposing task (§3 below) the same model performs cleanly — the paraphrase-sensitivity above is specific to the theme-dedup-style short-pair framing, not a general model weakness.

**Verdict: GO on latency and install-feasibility; footprint is tight (799MB peak RSS alone is 78% of the 1Gi limit, before the FastAPI app's own baseline memory) but workable if this is the only local model loaded in the pod.** The theme-dedup-pair sanity check found a real precision caveat (needs threshold tuning against the full probability distribution, not argmax) — flag for M5 implementation, not a go/no-go blocker.

---

## 2. spaCy NER (`en_core_web_sm`, via Presidio) — PII detection, §3.1/§3.2

**Install-feasibility check, Python 3.14** (the exact scenario research.md flagged as blocked): `uv venv --python 3.14`, `uv pip install spacy` — **succeeded**. Resolved `spacy==3.8.13`, `blis==1.3.3` with native `cp314` wheels. **The wheel gap research.md found (open issue explosion/spaCy#13949, `spacy==3.8.14` missing cp314 wheels) has closed in a patch release since research was written** — `3.8.13` has them. This is exactly why the plan called for a live re-check instead of trusting the research-stage finding: it would have produced a false no-go if skipped.

(One unrelated snag: `python -m spacy download en_core_web_sm` failed with `ModuleNotFoundError: No module named 'click'` — a missing transitive dependency in spaCy's CLI extra, unrelated to the cp314 question. Worked around by installing the model wheel directly via its GitHub release URL, which is how Presidio's own install docs recommend pinning models anyway.)

**Footprint**: venv + model = **107MB total**. By far the lightest of the three.

**Latency** (10 paragraph-length texts mixing bibliographic + PII content, matching `Paragraph.text` granularity, 20 repeats): P50 **4.0ms**, P95 **5.1ms**. Peak RSS: **158MB**.

**Sanity check** (NER on a paragraph with an author name, an org, and an email): correctly tagged `"Jane Rodriguez"` → `PERSON`, `"Northwestern Memorial Hospital"` → `ORG`. **False positive**: also tagged the email address `"j.rodriguez@example.edu"` as `PERSON`. Not a blocker — §3.1's design already routes emails through Presidio's regex recognizer, not the NER model, so this overlap is caught by the higher-confidence regex match regardless; worth confirming during M2 implementation that Presidio's recognizer-priority resolves the conflict as expected rather than double-redacting.

**Verdict: GO.** No install blocker (confirmed live, not assumed), negligible footprint, fast. Cheapest and clearest go of the three.

---

## 3. AlignScore — theme-review grounding pre-filter, M4 Tier 0.5 (not in original design doc; introduced in M4 milestone brief, d-004)

### 3a. As-declared (AlignScore's own `pyproject.toml` pins: `torch>=1.12.1,<2`)

**Install-feasibility check, Python 3.14**: `uv pip install alignscore` — **fails**, real resolver error:
```
Because only the following versions of torch are available:
    torch<=1.12.1, torch==1.13.0, torch==1.13.1, torch>=2
and torch>=1.12.1,<=1.13.1 has no wheels with a matching Python ABI tag (cp314),
we can conclude that torch>=1.12.1,<=1.13.1 cannot be used.
```
Confirms research.md's prediction exactly — and sharpens it: the actual ceiling is **cp311** (Python 3.11), not cp310 as research estimated from PyPI file listings alone; resolver output is more precise than manual file-list inspection.

**Measurement environment**: Python 3.10 (highest cp3x with both a torch wheel and (on this macOS arm64 dev box) actual platform coverage — 3.11's torch wheels are `manylinux1_x86_64`-only, no macOS arm64 build exists for that pin range on this platform).

**Getting it to actually run required three additional live fixes beyond the torch pin**, none anticipated by reading `pyproject.toml` alone:
1. `alignscore`'s loose `transformers>=4.20.1,<5` pin resolves to the newest 4.x by default (5.x isn't out of scope) — but current `transformers==4.57.6` (or the eventual `5.x`) has **removed the `AdamW` export** AlignScore's `model.py` imports at module load time. Fixed by pinning `transformers==4.30.2` explicitly (not expressible in AlignScore's own declared range — it's a real gap in AlignScore's compatibility testing, not a version-string oversight).
2. `pytorch_lightning` (pulled in transitively) needs `pkg_resources`, which modern `setuptools>=81` no longer bundles by default. Fixed with `setuptools<81`.
3. AlignScore's `nli_sp` evaluation mode calls `nltk.sent_tokenize`, which needs the `punkt_tab` corpus — not declared as an install-time dependency, not auto-downloaded; needs `nltk.download('punkt_tab')` as a manual step. (Also corrects research.md's assumption that AlignScore uses spaCy for sentence-splitting — the actual code path exercised here uses NLTK; spaCy is a declared dependency but not on this call path.)

Once all three were fixed, **inference actually ran successfully** — this is a real, working measurement, not a blocked one.

**Footprint**:
- Disk: venv = **850MB**; checkpoint download (`AlignScore-base.ckpt`, the only artifact published — full training checkpoint including optimizer state, not just inference weights) = **1.8GB**. Total ≈ **2.65GB disk**, before even counting the model's own transitive deps overlap with DeBERTa's.
- **Peak RSS: 3.24-3.86GB across runs** — **3.2-3.9× the pod's entire 1Gi memory limit**, on its own, before the FastAPI app or any other process in the pod.

**Latency** (4 synthesis-vs-evidence pairs matching `SingleThemeReview.synthesis` + `key_claims` shape, batched, 10 repeats, single-threaded via `torch.set_num_threads(1)` to match the pod's 1-CPU limit): batch-of-4 P50 **1394.6ms**, ≈**349ms/pair**. **30× slower per call than DeBERTa's 11.5ms.** (An earlier unpinned-thread run measured 150ms/pair — corrected here to match the actual pod constraint; single-threaded is markedly slower, as expected for a 355M-effective-parameter model without multi-core parallelism.)

**Sanity check** (grounded / fabricated / partially-grounded / contradicted synthesis vs the same evidence): scores **0.279 / 0.0015 / 0.0076 / 0.0003**. Real discriminative signal — grounded is ~37-900× higher than the three non-grounded cases — but the absolute "grounded" score (0.28) is far from 1.0, consistent with AlignScore's known calibration (a continuous alignment score needing a tuned threshold, not a probability to read at face value).

**Verdict: NO-GO as declared.** Footprint alone (3.86GB RSS, 1.8GB checkpoint download) is categorically incompatible with the 1Gi pod limit — this isn't a tuning problem, it's ~4× over budget. Even setting footprint aside, getting it running required three undeclared, manually-discovered fixes (old transformers pin, setuptools pin, manual NLTK corpus download) that would all need to be pinned and maintained indefinitely in the pipeline's own dependency tree — a real maintenance burden on top of the resource cost.

### 3b. Override attempt (Python 3.14, `--no-deps` + modern torch/transformers) — is the declared pin actually load-bearing?

Installed `alignscore --no-deps` + `torch==2.13.0` + `transformers==5.14.1` (both with native cp314 wheels) + spacy + jsonlines under Python 3.14.

- The `AdamW` import (finding 3a.1) is fixable with a one-line runtime shim (`transformers.AdamW = torch.optim.AdamW` before import) — confirmed working.
- Past that, model construction fails with a **real, unrelated breaking API change**: `pytorch_lightning>=2` requires `load_from_checkpoint` to be called as a classmethod on the class, not an instance — AlignScore's `inference.py` calls it on an already-constructed instance (valid in `pytorch_lightning 1.x`, explicitly rejected in `2.x`). This is two dependency-compatibility layers deep, not a version-string formality.

**Verdict: override path confirmed genuinely broken, not just conservatively pinned.** Making AlignScore run on modern dependencies would require patching `alignscore/inference.py` directly (forking the package), not just relaxing its declared pins. The as-declared pin is load-bearing evidence that this package is unmaintained against the current PyTorch/transformers ecosystem, which independently supports the footprint-driven no-go above.

### 3c. Precision comparison — does AlignScore earn a distinct job over repurposed DeBERTa? (brief.md scope item 2)

Same 4 synthesis-vs-evidence pairs run through `nli-deberta-v3-base` (evidence = premise, synthesis = hypothesis, entailment probability read as the grounding score):

| Pair | AlignScore | DeBERTa entailment prob | DeBERTa full (contra/entail/neutral) |
|---|---|---|---|
| grounded | 0.279 | **0.945** | 0.000 / 0.945 / 0.055 |
| fabricated (over-claim) | 0.0015 | 0.000 | 0.015 / 0.000 / 0.985 |
| partially-grounded (unsupported causal link) | 0.0076 | 0.000 | 0.000 / 0.000 / 0.999 |
| contradicted (direct negation) | 0.0003 | 0.000 | **1.000** / 0.000 / 0.000 |

Both models cleanly separate the grounded pair from all three non-grounded ones by a wide margin. **DeBERTa additionally distinguishes *why* a synthesis fails grounding** — outright contradiction (1.0 contradiction probability) vs merely-unsupported/fabricated (0.985-0.999 neutral) — a distinction AlignScore's single scalar alignment score doesn't expose, despite the design doc's grounding-cascade use case plausibly caring about that difference (a contradicted claim likely warrants a harder failure than a merely-unembellished one).

**This is a 4-pair smoke comparison, not a benchmark** — not enough to fully settle precision, but the directional evidence, combined with AlignScore's ~4× memory overrun and ~13× latency cost, does not support AlignScore earning a "genuinely distinct job" per the initiative's breadth doctrine (initiative brief.md:22) for this specific whole-synthesis-vs-evidence use case. Repurposing the already-adopted DeBERTa cross-encoder for this same job (premise=evidence, hypothesis=synthesis) is the evidence-backed alternative — a design deviation from M4's d-004, to be decided at M4 planning time with this data in hand, not decided here.

---

## Summary

| Model | Install (target: Python 3.14) | Disk | Peak RSS | Latency | Verdict |
|---|---|---|---|---|---|
| DeBERTa-v3 MNLI (`nli-deberta-v3-base`) | Clean, no blocker | ~1.5GB | 799MB (78% of 1Gi limit) | 11.5ms P50 | **GO** — tight footprint, workable alone in the pod; sanity check surfaced a real threshold-tuning need for M5 |
| spaCy (`en_core_web_sm`) | Clean, no blocker (wheel gap from research.md has since closed — verified live) | 107MB | 158MB | 4.0ms P50 | **GO** — clear win, cheapest of the three |
| AlignScore (as-declared) | **Blocked** on Python 3.14 (confirmed); runs on Python 3.10 after 3 undeclared manual fixes | ~2.65GB | **3.2-3.9GB (320-390% of 1Gi limit)** | 349ms/pair single-threaded (30× DeBERTa) | **NO-GO** |
| AlignScore (override, modern deps) | **Blocked** — real `pytorch_lightning` 2.x API break past the import layer, confirms declared pin is load-bearing | — | — | — | **NO-GO**, would require forking the package |

**No model was added to `pipeline/pyproject.toml` / `pipeline/uv.lock`** — all measurement happened in scratch `pipeline/spikes/.venv-*` environments, gitignored.

**Recommendation carried into M4/M5 planning**: DeBERTa and spaCy proceed to their respective integration tasks (M5-T3, M2-T1/T2). AlignScore does not proceed as specified in M4-T5 — the M4 milestone should revisit d-004 with this evidence: either drop AlignScore and repurpose DeBERTa for the Tier 0.5 grounding pre-filter (§3c), or explicitly accept the footprint/maintenance cost with a resource-limit increase, as a deliberate, informed decision rather than the original assumption.
