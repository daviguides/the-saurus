# The Saurus 🦕

_Feed The Saurus your papers._

A literature review pipeline that devours scientific papers and produces comprehensive, citation-backed reviews. Upload a corpus of PDFs, watch the pipeline process them in parallel, and get a structured literature review with thematic analysis and traceable citations.

## What It Does

### Pipeline

1. **Upload** — Drop your scientific PDFs
2. **Analyze** — AI agents extract themes and claims from each paper (parallel, stateless)
3. **Deduplicate** — Semantically equivalent themes are merged across papers
4. **Review** — Deep thematic analysis synthesizes findings across papers
5. **Generate** — Cohesive literature review with inline citations `[N](p.X,§Y)`

Every claim is traceable to its source: paper, page, and paragraph.

### Conversational Assistant

1. **Connect** — Embedded chat panel served as a federated UI (Module Federation 2.0)
2. **Query** — Ask questions about your papers grounded in the actual pipeline outputs
3. **Retrieve** — MCP tools fetch themes, claims, reviews, and citations from Qdrant
4. **Answer** — Agno Team (GPT-4o-mini) synthesizes a response with evidence from your corpus

The assistant only knows what the pipeline extracted, keeping answers traceable and hallucination-resistant.

## Prerequisites

- Python 3.13+
- Node.js 20+ with pnpm
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (for Qdrant, optional)
- Google AI Studio API key ([get one here](https://aistudio.google.com/apikey))

## Setup

```bash
git clone https://github.com/daviguides/the-saurus.git
cd the-saurus
make setup
```

Copy environment files and set your API key:

```bash
cp pipeline/.env.example pipeline/.env
# Edit pipeline/.env and set PIPELINE_LLM_API_KEY

cp assistant-ws/.env.example assistant-ws/.env
# Edit assistant-ws/.env and set OPENAI_API_KEY (for the chat assistant)
```

## Running

### Core (pipeline + app)

The minimum to upload PDFs and generate a literature review:

```bash
# Terminal 1: Pipeline API (port 8002)
make dev-pipeline

# Terminal 2: React app (port 5173)
make dev-app
```

Open [http://localhost:5173](http://localhost:5173) and upload PDFs.

### Conversational assistant (optional)

Adds an embedded chat that can answer questions about your papers using MCP tools over Qdrant:

```bash
# Terminal 3: Qdrant vector database (port 6333)
make dev-qdrant

# Terminal 4: MCP server for RAG queries (port 8012)
make dev-mcp

# Terminal 5: Chat WebSocket backend (port 8001)
make dev-ws

# Terminal 6: Chat UI federated module (port 5174)
make dev-ui
```

### All services at once (Docker Compose)

```bash
make up      # Start all services
make down    # Stop all services
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  app (React 19)                              assistant-ui (MF)  │
│  Upload → Pipeline Trace → Review              Chat Drawer     │
├─────────────────────────────────────────────────────────────────┤
│  pipeline (FastAPI)          │  assistant-ws    │  papers-mcp    │
│  POST /jobs → run_pipeline   │  Socket.IO chat  │  Qdrant RAG    │
│  WS /jobs/{id}/stream        │  Agno Team       │  FastMCP       │
├─────────────────────────────────────────────────────────────────┤
│  Gemini 2.5 Flash (LLM)     │  Qdrant (vectors) │  YAML/NDJSON  │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline

| Stage | Agent | Parallelism | Description |
|-------|-------|-------------|-------------|
| Paper Analysis | PaperAnalyzerAgent | Per paper | Extract themes + claims in one pass |
| Theme Dedup | ThemeDedupAgent | Sequential | Merge semantic synonyms across papers |
| Theme Review | ThemeReviewerAgent | Batched (5/call) | Synthesize claims per theme |
| Aggregation | AggregatorAgent | Sequential | Cohesive review with citations |

All agents use the Agno framework with Pydantic structured output and streaming events. LLM concurrency is controlled by a shared semaphore (configurable via `PIPELINE_LLM_MAX_CONCURRENT`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Rsbuild, Tailwind v4, Module Federation 2.0 |
| Pipeline | Python 3.13+, FastAPI, Agno, Gemini 2.5 Flash |
| Assistant | Agno Team, Socket.IO, GPT-4o-mini |
| RAG | Qdrant, Gemini text-embedding-004, FastMCP |
| Persistence | YAML (state), NDJSON (events), filesystem |
| Design | Literata + Inter + Fira Code, light/dark themes |

## Project Structure

```
the-saurus/
├── app/                    # React desktop app (upload, trace, review)
├── assistant-ui/           # Federated chat UI (Module Federation remote)
├── assistant-ws/           # Chat WebSocket backend (Agno Team)
├── papers-mcp/             # MCP server (6 tools over Qdrant)
├── pipeline/               # Core pipeline engine (multi-agent orchestrator)
├── evals/                  # Evaluation suite (RAGAS + DeepEval + Langfuse)
├── pipeline-test-client/   # CLI for end-to-end pipeline testing
├── assistant-test-client/  # CLI for end-to-end assistant testing
├── shared/                 # Design tokens (CSS variables, light + dark)
├── Makefile                # Dev commands
└── docker-compose.yml
```

## Configuration

| Service | Env file | Key variables |
|---------|----------|---------------|
| Pipeline | `pipeline/.env` | `PIPELINE_LLM_API_KEY`, `PIPELINE_LLM_MAX_CONCURRENT` (default 2, set 10 for paid tier) |
| Assistant | `assistant-ws/.env` | `OPENAI_API_KEY`, `AT_LLM_PROVIDER` (openai/anthropic) |
| MCP | `papers-mcp/.env` | `MCP_QDRANT_URL` (default localhost:6333) |

See each service's `.env.example` for all available settings.

## Testing

```bash
make test    # Run all unit test suites
make lint    # Lint all Python services
```

### Test Clients

Two standalone CLI tools for end-to-end testing against running services. They can be used interactively during development or autonomously by AI coding agents (like Claude Code) to validate changes, diagnose issues, and verify fixes against local or remote environments.

**Pipeline Test Client** (`pipeline-test-client/`): Tests the full pipeline flow over HTTP + WebSocket.

```bash
cd pipeline-test-client

# Upload a PDF and watch the pipeline process it end-to-end
uv run pipeline-test run test-cases/papers/exercise_cognitive_function_brain.pdf

# Run a YAML test case with assertions (paper count, theme count, citations)
uv run pipeline-test test-flow test-cases/cases/basic_flow.yaml

# Individual commands
uv run pipeline-test upload <pdf>        # Upload PDFs, get job_id
uv run pipeline-test stream <job_id>     # Watch live agent events
uv run pipeline-test review <job_id>     # Show generated literature review
uv run pipeline-test papers <job_id>     # Show extracted themes and claims
```

**Assistant Test Client** (`assistant-test-client/`): Tests the conversational assistant over Socket.IO.

```bash
cd assistant-test-client

# Ask a question about the processed papers
uv run assistant-test ask "What are the main themes found across all papers?"

# Interactive chat mode
uv run assistant-test chat

# Run a YAML test case with assertions (content, tools called, step count)
uv run assistant-test test-flow test-cases/cases/theme_query.yaml
```

### Logged Mode (for AI agents)

Services can run in background with logs piped to files, allowing AI coding agents to start services, run test clients, and read logs to diagnose issues autonomously:

```bash
make log-pipeline    # Start pipeline, logs to logs/pipeline.log
make log-ws          # Start assistant, logs to logs/assistant-ws.log
make log-mcp         # Start MCP server, logs to logs/papers-mcp.log
make log-core        # Pipeline + app
make log-all         # All services
make log-stop        # Stop all logged services
```

Agno `debug_mode` is enabled by default, so logs include full prompts sent to the LLM, structured output schemas, streaming events, and response content.

## Evaluation and Observability

Both the pipeline and assistant services have dedicated evaluation suites and observability instrumentation, housed in the `evals/` workspace.

### Observability (Langfuse)

LLM calls from both services are traced via [Langfuse](https://langfuse.com/) (self-hosted), capturing prompts, completions, token usage, latency, and agent lifecycle events. Agno agent calls are auto-instrumented via OpenLIT + OpenTelemetry.

```bash
make eval-langfuse       # Start Langfuse locally (Docker)
# Open http://localhost:3000, create account, copy API keys to evals/.env
```

| Service | What is traced | LLM |
|---------|---------------|-----|
| Pipeline | 4 agents (PaperAnalyzer, ThemeDedup, ThemeReviewer, Aggregator), structured output, streaming events | Gemini 2.5 Flash |
| Assistant | Agno Team coordinator, MCP tool calls to Qdrant, conversation turns | GPT-4o-mini |

### Evaluation (RAGAS + DeepEval)

[RAGAS](https://docs.ragas.io/) generates synthetic test datasets from the golden PDFs and provides RAG-specific metrics. [DeepEval](https://deepeval.com/) runs pytest-native assertions against pipeline and assistant outputs, with Gemini as the LLM judge.

**Pipeline evals:** faithfulness (claims cite sources), citation accuracy ([N] refs resolve to real papers), theme quality (meaningful, non-redundant), schema completeness (structured output has all fields), safety (bias, toxicity, hallucination).

**Assistant evals:** answer relevancy (grounded in pipeline data), tool correctness (right MCP tool selected), safety.

### Prompt Regression Workflow

```bash
# 1. Run the pipeline against golden test PDFs
make eval-run-pipeline

# 2. Evaluate the output
make eval-pipeline

# 3. If scores are good after a prompt change, update the baseline
make eval-update-baseline
```

A CI workflow (`.github/workflows/eval-regression.yml`) runs evals automatically on PRs that touch prompts or agent code.

### Production Scoring

Score a sample of production traces (10% by default) with RAGAS metrics, pushing results back to Langfuse for dashboarding:

```bash
make eval-score-pipeline     # Score pipeline traces
make eval-score-assistant    # Score assistant traces
```

## The Name

A thesaurus connects words that mean the same thing. This pipeline does exactly that for scientific themes across papers: "chronobiology" in one paper and "circadian rhythms" in another become a single canonical theme. **The Saurus**: part thesaurus, part dinosaur.

## License

MIT
