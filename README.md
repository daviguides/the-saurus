# The Saurus 🦕

_Feed The Saurus your papers._

A literature review pipeline that devours scientific papers and produces comprehensive, citation-backed reviews. Upload a corpus of PDFs, watch the pipeline process them in parallel, and get a structured literature review with thematic analysis and traceable citations.

## What It Does

1. **Upload** — Drop your scientific PDFs
2. **Analyze** — AI agents extract themes and claims from each paper (parallel, stateless)
3. **Deduplicate** — Semantically equivalent themes are merged across papers
4. **Review** — Deep thematic analysis synthesizes findings across papers
5. **Generate** — Cohesive literature review with inline citations `[N](p.X,§Y)`

Every claim is traceable to its source: paper, page, and paragraph.

## Quick Start

```bash
# Install dependencies
make setup

# Start pipeline + app (minimum for demo)
make dev-pipeline   # Terminal 1 — port 8002
make dev-app        # Terminal 2 — port 5173

# Optional: assistant chat
make dev-ws         # Terminal 3 — port 8001
make dev-ui         # Terminal 4 — port 5174 (use: pnpm dev:federated)
make dev-qdrant     # Terminal 5 — port 6333
make dev-mcp        # Terminal 6 — port 8012
```

Open [http://localhost:5173](http://localhost:5173) and upload PDFs.

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

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Rsbuild, Tailwind v4, Module Federation |
| Pipeline | Python 3.13+, FastAPI, Agno, Gemini 2.5 Flash |
| Assistant | Agno Team, Socket.IO, OpenAI/Anthropic |
| RAG | Qdrant, Gemini text-embedding-004, FastMCP |
| Persistence | YAML (state), NDJSON (events), filesystem |
| Design | Literata + Inter + Fira Code, light/dark themes |

## Project Structure

```
the-saurus/
├── app/              # React desktop app
├── assistant-ui/     # Federated chat UI
├── assistant-ws/     # Chat WebSocket backend
├── papers-mcp/       # MCP server (Qdrant RAG)
├── pipeline/         # Core pipeline engine
├── shared/           # Design tokens (CSS)
├── docs/             # Design docs & explorations
├── Makefile          # Dev commands
└── docker-compose.yml
```

## Configuration

Copy `pipeline/.env.example` to `pipeline/.env` and set:

```
PIPELINE_LLM_API_KEY=your-google-ai-studio-key
PIPELINE_LLM_MAX_CONCURRENT=10  # paid tier
```

## Origin

Built as a technical demonstration for [AnswerThis](https://answerthis.io/) (YC F25), addressing the gap between their Library (upload PDFs) and literature review engine (search-based). The Saurus bridges that gap: process uploaded papers into a comprehensive review.

**The name**: Born from a comic moment in a technical interview. While discussing theme deduplication across scientific papers — how "chronobiology" and "chronos" refer to the same concept — the word "thesaurus" came up. A thesaurus connects words that mean the same thing. The pipeline does exactly that. **The Saurus**: part thesaurus, part dinosaur.

## License

MIT
