# Papers MCP

MCP server exposing RAG tools over pipeline outputs stored in Qdrant. Bridge between the pipeline (producer) and the assistant (consumer).

## Tech

FastMCP, Qdrant client, Gemini embeddings

## Port

8012

## Tools Exposed

| Tool | Description |
|------|-------------|
| `get_paper_themes` | Retrieve themes for a paper |
| `get_claims_by_theme` | Get claims grouped by theme |
| `get_theme_map` | Get the full theme map |
| `get_theme_review` | Get review for a specific theme |
| `get_literature_review` | Get the literature review |
| `search_claims` | Semantic search across claims |

## Qdrant Collections

`paper_themes`, `paper_claims`, `theme_map`, `theme_reviews`, `literature_review`

## Embeddings

Gemini `text-embedding-004` (API, same key as pipeline).

## Config

`.env` with `MCP_` prefix.

Key variables: `MCP_QDRANT_URL`, `MCP_HOST`, `MCP_PORT`

## How It Fits

```
pipeline writes to Qdrant (side-effect)
  -> papers-mcp reads from Qdrant
    -> assistant-ws calls papers-mcp tools via MCP protocol
```

## Structure

```
papers_mcp/
├── server.py              # FastMCP + tool definitions
├── store.py               # Qdrant client
└── schemas/
    └── results.py
```

## Development

```bash
uv run python scripts/run_server.py    # Port 8012
```
