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
