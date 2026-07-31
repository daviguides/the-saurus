# Evals

Evaluation and observability suite for The Saurus pipeline and assistant services.

## Stack

- **Langfuse** - tracing and observability (self-hosted via Docker)
- **RAGAS** - synthetic test generation and RAG evaluation metrics
- **DeepEval** - pytest-native LLM evaluation with regression testing

## Setup

```bash
cd evals
uv sync

# Start Langfuse locally
docker compose up -d

# Create account at http://localhost:3000
# Copy API keys to .env
cp .env.example .env
```

## Workflow: Prompt Regression Testing

```bash
# 1. Add test PDFs to evals/pipeline/golden/papers/

# 2. Run the pipeline against golden PDFs
make eval-run-pipeline

# 3. Run evals against the output
make eval-pipeline

# 4. If scores are good, update baseline
make eval-update-baseline
```

## Services

| Directory | Service | What it evaluates |
|-----------|---------|-------------------|
| `pipeline/` | Pipeline | Theme extraction, review quality, citations |
| `assistant/` | Assistant | Answer relevancy, tool selection, safety |

## Scoring Production Traffic

```bash
# Score 10% of pipeline traces in Langfuse
make eval-score-pipeline

# Score 10% of assistant traces in Langfuse
make eval-score-assistant
```

## Closing the Loop: Production Misses → Golden Set

`make eval-score-pipeline` flags traces scoring below `PRODUCTION_FAITHFULNESS_THRESHOLD`
(see `scoring/pipeline_scorer.py`) into `evals/pipeline/golden/misses.jsonl` — one JSON
line per miss (`trace_id`, `input`, `output`, `score`, `metric`). This file is gitignored;
it's a transient triage inbox, not a checked-in fixture.

To grow the golden set from these misses:

1. Review `evals/pipeline/golden/misses.jsonl`.
2. For each entry, judge: is this a failure mode not already represented by the papers in
   `evals/pipeline/golden/papers/`?
3. If yes — add the source paper (or a repro PDF) to `evals/pipeline/golden/papers/`, then:
   ```bash
   make eval-run-pipeline
   make eval-pipeline
   make eval-update-baseline
   ```
4. If no (already covered, or noise) — discard the line, no action needed.

This step is intentionally manual: judging "is this genuinely new" isn't something to
automate blindly, since a wrong call either bloats the golden set with near-duplicates or
misses a real gap.
