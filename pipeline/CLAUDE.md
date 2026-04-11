# The Saurus — Pipeline

Multi-agent pipeline engine for literature review generation. Ingests scientific PDFs, extracts themes and claims via LLM agents, deduplicates themes across papers, reviews each theme with cross-paper evidence, and aggregates into a cohesive literature review with traceable citations.

## Tech Stack

- **Framework**: FastAPI (async)
- **LLM**: Agno framework + Gemini 2.5 Flash (google-genai)
- **Vector DB**: Qdrant (fire-and-forget side-effect writes, graceful disable if unavailable)
- **Embeddings**: Gemini text-embedding-004 (via google-genai API)
- **Persistence**: YAML + NDJSON on filesystem
- **Config**: pydantic-settings with `PIPELINE_` env prefix
- **Port**: 8002

## Pipeline Stages

```
Upload PDFs → Paper Analysis → Theme Dedup → Theme Review → Aggregation
```

| Stage | Agent | Description |
|-------|-------|-------------|
| Paper Analysis | `PaperAnalyzerAgent` | Extracts themes + claims per paper (parallel across papers) |
| Theme Dedup | `ThemeDedupAgent` | Semantic deduplication of themes across all papers |
| Theme Review | `ThemeReviewerAgent` | Synthesizes claims across papers per theme (batched, 5 themes per LLM call) |
| Aggregation | `AggregatorAgent` | Produces cohesive literature review with citations from all theme reviews |

## Structure

```
pipeline/
├── __init__.py
├── __main__.py
├── app.py                            # FastAPI app, lifespan, CORS, orphan recovery
├── config.py                         # Settings (pydantic-settings, PIPELINE_ prefix)
├── api/
│   ├── routes.py                     # REST endpoints + background pipeline launch
│   └── schemas.py                    # Pydantic response models
├── ws/
│   └── stream.py                     # WebSocket /jobs/{id}/stream for live events
├── engine/
│   ├── orchestrator.py               # Runs stages in order, parallel per-paper, sync barriers
│   ├── stages.py                     # Stage enum (paper_analysis, theme_dedup, theme_review, aggregation)
│   └── progress.py                   # Progress tracking across stages
├── agents/
│   ├── protocol.py                   # Agent Protocol (async run(input) → dict)
│   ├── models.py                     # LLM model factory (Gemini) + llm_semaphore
│   ├── parsing.py                    # run_agent_with_retry: retry logic, observability logging
│   ├── paper_analyzer.py             # PaperAnalyzerAgent (themes + claims per paper)
│   ├── theme_dedup.py                # ThemeDedupAgent (cross-paper dedup)
│   ├── theme_reviewer.py             # ThemeReviewerAgent (batched, BATCH_SIZE=5)
│   ├── aggregator.py                 # AggregatorAgent (final review)
│   ├── theme_extractor.py            # Legacy (replaced by PaperAnalyzerAgent)
│   ├── claim_extractor.py            # Legacy (replaced by PaperAnalyzerAgent)
│   ├── stubs.py                      # Stub agents for testing
│   └── prompts/
│       ├── paper_analyzer.py
│       ├── theme_dedup.py
│       ├── theme_reviewer.py
│       ├── aggregator.py
│       ├── theme_extractor.py        # Legacy
│       └── claim_extractor.py        # Legacy
├── core/
│   ├── models.py                     # JobStatus, JobState, PaperEntry, EventType
│   ├── persistence.py                # read_yaml, write_yaml, read_status, write_status, read_events
│   ├── events.py                     # EventEmitter (NDJSON append + WebSocket broadcast)
│   └── qdrant.py                     # Qdrant indexer (fire-and-forget, graceful disable)
├── ingestion/
│   ├── extract.py                    # PDF → text extraction (pdfplumber + pymupdf)
│   └── models.py                     # IngestionResult model
scripts/
│   └── run_server.py                 # uvicorn launcher with logging config
tests/
│   └── ...                           # pytest + pytest-asyncio
```

## Agent Architecture

Each agent wraps `agno.agent.Agent` and satisfies `pipeline.agents.protocol.Agent`:

```python
@runtime_checkable
class Agent(Protocol):
    async def run(self, input: dict[str, Any]) -> dict[str, Any]: ...
```

### Observability

`run_agent_with_retry` (in `parsing.py`) wraps every LLM call with:
- Input character count, estimated tokens
- Response type and length
- Elapsed time
- Retry count (with exponential backoff for 429s)
- Structured logging at INFO level

### Rate Limiting

`llm_semaphore` (in `models.py`) is an `asyncio.Semaphore` controlling concurrent LLM calls across all agents. Configurable via `PIPELINE_LLM_MAX_CONCURRENT` (default 2 for free tier, increase for paid).

## Persistence

Jobs are stored under `jobs/{job_id}/`:

```
jobs/{job_id}/
├── status.yaml          # JobStatus (state, stage, progress, error)
├── papers.yaml          # List of ingested papers (paper_id, title, authors, pages)
├── events.ndjson        # Append-only event stream
├── themes/
│   └── {paper_id}.yaml  # Extracted themes per paper
├── claims/
│   └── {paper_id}.yaml  # Extracted claims per paper
├── theme_map.yaml       # Deduplicated theme mapping
├── theme_reviews/
│   └── {theme_id}.yaml  # Per-theme review with cross-paper evidence
└── review.yaml          # Final aggregated literature review
```

## Qdrant Integration

Fire-and-forget side-effect writes using Gemini text-embedding-004. Themes, claims, and review sections are embedded and indexed. If Qdrant is unavailable, the pipeline continues without vector indexing (graceful disable).

## Orphan Recovery

On startup (`app.py` lifespan), scans `jobs/` directory and marks any jobs stuck in `running` or `pending` state as `failed`. Prevents ghost jobs after server restarts.

## REST API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs` | Upload PDFs, create job, launch pipeline |
| GET | `/jobs/{id}/status` | Job status (state, stage, progress) |
| GET | `/jobs/{id}/papers` | Enriched papers with themes + claims |
| GET | `/jobs/{id}/review` | Final literature review |
| GET | `/jobs/{id}/events` | All pipeline events (NDJSON parsed) |
| GET | `/health` | Health check |

## WebSocket

`/jobs/{job_id}/stream` — live pipeline events. Replays past events on connect, then streams new events in real time.

## Configuration

`.env` file in `pipeline/` directory with `PIPELINE_` prefix:

| Setting | Default | Description |
|---------|---------|-------------|
| `PIPELINE_LLM_API_KEY` | — | Google AI Studio API key (Gemini) |
| `PIPELINE_LLM_MODEL_ID` | `gemini-2.5-flash` | LLM model identifier |
| `PIPELINE_LLM_MAX_CONCURRENT` | `2` | Max concurrent LLM calls (semaphore) |
| `PIPELINE_LLM_RETRY_DELAY` | `15.0` | Base retry delay in seconds |
| `PIPELINE_LLM_MAX_RETRIES` | `5` | Max retries per agent call |
| `PIPELINE_JOBS_DIR` | `./jobs` | Job persistence directory |
| `PIPELINE_QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `PIPELINE_QDRANT_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `PIPELINE_HOST` | `0.0.0.0` | Server bind host |
| `PIPELINE_PORT` | `8002` | Server port |

## Development

```bash
uv run python scripts/run_server.py    # Start server on :8002 with hot-reload
uv run pytest tests/ -v                 # Run tests
uv run ruff check pipeline/            # Lint
uv run ruff format pipeline/           # Format
```

## Conventions

- Python 3.13+, ruff for lint/format, pytest + pytest-asyncio for tests
- Agents use Agno framework with Pydantic structured output
- All agents satisfy `pipeline.agents.protocol.Agent` Protocol
- YAML for structured data, NDJSON for event streams (append-only)
- Conventional commits (`feat`, `fix`, `refactor`, `chore`)
