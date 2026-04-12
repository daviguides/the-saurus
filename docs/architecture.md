# The Saurus — Architecture

A multi-agent pipeline that transforms a corpus of scientific PDFs into a comprehensive literature review with thematic analysis and traceable citations.

## System Overview

<img src="diagrams/system-overview.png" style="max-height:1140px; width:auto;" />

| Service | Tech | Role |
|---------|------|------|
| **App** :5173 | React 19, Rsbuild, Tailwind v4 | Host UI — upload, trace, review |
| **Assistant UI** :5174 | React 19, Module Federation 2.0 | Federated chat panel (lazy-loaded) |
| **Pipeline** :8002 | FastAPI, Restate, Agno, Gemini 2.5 Flash | PDF ingestion + multi-agent orchestrator |
| **Assistant WS** :8001 | FastAPI, Socket.IO, GPT-4o-mini | Conversational agent with MCP tools |
| **Papers MCP** :8012 | FastMCP | RAG bridge — 6 tools over Qdrant |
| **Restate** :8080 | Restate (Rust) | Durable execution — journals pipeline stages |
| **Qdrant** :6333 | Qdrant (Docker) | Vector search for claims + themes |
| **Langfuse** :3000 | Langfuse + ClickHouse + Redis | LLM observability — traces, costs, evals |

Key decisions:
- **Restate for durable execution** — Each pipeline stage is journaled; crash recovery replays completed stages without re-execution
- **YAML as MVP persistence** — Qdrant writes are graceful side-effects; pipeline works without it
- **Module Federation 2.0** — Assistant UI is a separate build, lazy-loaded with error boundaries
- **MCP as data bridge** — Clean separation between pipeline (writes) and assistant (reads)
- **Opt-in auth** — API key enforcement only when `PIPELINE_API_KEY` is set; zero friction for local dev

## Pipeline Flow

Four stages with explicit sync barriers and controlled parallelism.

<img src="diagrams/pipeline-flow.png" style="max-height:1200px; width:auto;" />

All LLM calls are throttled by a shared `asyncio.Semaphore` (configurable via `PIPELINE_LLM_MAX_CONCURRENT`, default 2 for free tier, 10+ for paid).

### Durable Execution (Restate)

Pipeline stages are orchestrated through a Restate `Workflow`. Each stage is a durable step — its result is journaled by the Restate server. If the process crashes mid-pipeline, Restate replays the journal on restart, returning stored results for completed stages and re-executing only from the point of failure.

```
POST /jobs
  └─> Restate ingress (HTTP, idempotent)
        └─> PipelineWorkflow/{job_id}/run
              ├── ctx.run("paper_analysis")    # journaled
              ├── ctx.run("theme_dedup")       # journaled
              ├── ctx.run("theme_review")      # journaled
              └── ctx.run("aggregation")       # journaled
```

If Restate is not running, the pipeline falls back to in-process `asyncio.create_task` execution — ensuring zero friction for local development.

### Orchestrator Structure

The orchestrator is decomposed into a coordinator and stage functions:

```python
async def run_pipeline(job_id, jobs_dir):
    ctx = await _setup_pipeline(job_id, jobs_dir)    # PipelineContext
    try:
        analysis = await _run_paper_analysis(ctx)     # parallel per paper
        dedup = await _run_theme_dedup(ctx, analysis) # sequential barrier
        reviews = await _run_theme_review(ctx, ...)   # parallel batches
        await _run_aggregation(ctx, ...)              # sequential barrier
        await _finalize_pipeline(ctx)
    except Exception as exc:
        await _handle_pipeline_failure(ctx, exc)
    finally:
        _cleanup(ctx)                                 # release emitter + locks
```

`PipelineContext` is a dataclass holding shared state (job metadata, papers, emitter, tracker, indexer, background tasks).

## Agent Data Flow

What each agent receives and produces as data accumulates through the pipeline.

<img src="diagrams/agent-data-flow.png" style="max-height:1140px; width:auto;" />

All agents use Agno with `structured_outputs=True` and Pydantic `output_schema`. Agent calls go through `run_agent_with_retry`, which provides:
- Semaphore-gated concurrency control
- Exponential backoff with jitter on failure
- Configurable timeout (300s for large papers)
- Streaming events forwarded to the event bridge

### Critical Design Decision: Stateless Paper Analysis

Each paper is analyzed **independently** — no accumulated context from prior papers is passed to the agent. This prevents cross-paper bias where themes found in Paper 1 would prime the extraction in Paper 2.

Theme synonyms (e.g., "chronobiology" in Paper A vs "circadian rhythms" in Paper B) are resolved downstream by the **ThemeDedupAgent**, which sees all themes at once and groups them semantically.

## Theme Deduplication

The core challenge: different papers use different terminology for the same concept.

<img src="diagrams/theme-dedup.png" style="max-height:840px; width:auto;" />

Output: a **theme map** — `{canonical_id → [source_theme_ids]}` — that unifies all downstream processing under canonical names.

## Error Handling

The pipeline uses a custom exception hierarchy rooted in `PipelineError`:

```
PipelineError
├── StageError(stage: str)         # failure in a specific pipeline stage
├── AgentError(agent_name: str)    # LLM agent failure
│   └── AgentResponseError         # invalid or empty LLM response
├── PersistenceError               # YAML read/write failure
└── IngestionError                 # PDF extraction failure
```

Partial failure is tolerated: if some papers fail analysis but not all, the pipeline continues with successful results and logs warnings. Only a total failure raises.

Error messages exposed to clients are sanitized (stage context without internal details). Full stack traces remain server-side only.

## Persistence Model (MVP)

Filesystem-based for rapid prototyping and debuggability. The persistence interface is isolated in `core/persistence.py`, making a database swap straightforward.

```
jobs/{job_id}/
├── status.yaml                    # JobStatus (state, stage, progress)
├── papers.yaml                    # list[PaperEntry] (metadata)
├── events.ndjson                  # append-only event stream (fsync per write)
├── {paper_id}.md                  # annotated markdown ([p.X,section-Y])
├── themes/
│   └── {paper_id}.yaml            # per-paper extracted themes
├── claims/
│   └── {paper_id}.yaml            # per-paper extracted claims
├── theme_map.yaml                 # canonical themes + aliases
├── theme_reviews/
│   └── {theme_id}.yaml            # per-theme synthesis
├── review.yaml                    # final literature review
└── raw/                           # debug: raw LLM responses
```

**YAML** for structured state (human-readable, git-diffable). **NDJSON** for append-only event streams (crash-safe with `os.fsync`, replayable).

## Real-Time Event Architecture

<img src="diagrams/event-architecture.png" style="max-height:400px; width:auto;" />

Events flow through three channels simultaneously:
1. **NDJSON file** — durable append-only log with `fsync` per write
2. **In-memory listeners** — broadcast to connected WebSocket clients
3. **Agno event bridge** — maps 6 Agno lifecycle events (RunStarted, ToolCall, ToolResult, Content, Completed, Error) to pipeline event types with human-readable and technical messages

Event lifecycle: `job_created` → `stage_started` → `agent_started` → `agent_completed` → `stage_completed` → `job_completed`. On reconnect, the client replays from `events.ndjson` (supports `?after_event_id=` for delta sync).

## Conversational Assistant

<img src="diagrams/assistant.png" style="max-height:600px; width:auto;" />

**6 MCP tools**: `get_paper_themes`, `get_claims_by_theme`, `get_theme_map`, `get_theme_review`, `get_literature_review`, `search_claims` (semantic vector search).

The assistant only knows what the pipeline extracted, keeping answers traceable and hallucination-resistant.

## Citation Traceability

Every claim in the final review traces back to a specific location in the source PDF.

<img src="diagrams/citation-traceability.png" style="max-height:480px; width:auto;" />

Post-processing resolves `[N]` references into `[N](p.X, paragraph Y)` with full paper-level back-references, making every statement in the review verifiable against the source material.

## Security

Authentication is opt-in via `PIPELINE_API_KEY` environment variable:
- **Unset (dev)**: all endpoints are open, zero friction
- **Set (prod)**: REST endpoints require `X-Api-Key` header, WebSocket requires `token` query parameter

Additional hardening:
- Path traversal protection on job IDs (`is_relative_to` check)
- PDF upload: filename sanitization, magic bytes validation, 50MB size limit, 50 file count limit
- Error messages sanitized (no internal details exposed to clients)
- `yaml.safe_load` / `yaml.safe_dump` only (no unsafe deserialization)

## Infrastructure

### Terraform (AWS)

Provisions cloud infrastructure across three environments (dev/staging/prod):

| Module | Resource | Purpose |
|--------|----------|---------|
| `vpc` | VPC + subnets | Network isolation (public/private, 2 AZs) |
| `eks` | EKS cluster | Kubernetes with managed node groups, KMS-encrypted secrets |
| `aurora` | Aurora Serverless v2 | PostgreSQL for Langfuse (environment-aware scaling) |
| `elasticache` | Redis 7.x | Langfuse queue + Socket.IO horizontal scaling |
| `s3` | S3 buckets | Langfuse storage + pipeline artifacts |

### Helm (Kubernetes)

Deploys all services with autoscaling, health probes, and secrets management:

| Component | Type | Notes |
|-----------|------|-------|
| Pipeline | Deployment + HPA | 2-10 replicas, CPU-based autoscaling |
| Assistant WS | Deployment + HPA | Sticky sessions, Redis adapter |
| App | Deployment | Static frontend via nginx |
| Papers MCP | Deployment | Qdrant URL from ConfigMap |
| Qdrant | StatefulSet + PVC | 10Gi dev, 50Gi prod |
| Restate | Deployment + PVC | Durable journal (5Gi dev, 20Gi prod) |
| Langfuse | Web + Worker | Observability platform |
| ClickHouse | StatefulSet + PVC | Analytics for Langfuse (20Gi dev, 100Gi prod) |

Values files: `values.yaml` (dev defaults) and `values-prod.yaml` (production overrides with ALB ingress, TLS, and larger resources).
