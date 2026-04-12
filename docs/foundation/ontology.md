# The Saurus: Ontology

_Entities, relationships, and lifecycle._

---

## Core Entities

```
JOB (lifecycle — one per pipeline run)
│  A processing session. Created on upload, runs the pipeline, produces outputs.
│  • Status: uploading → processing → completed | failed
│  • Papers: the uploaded corpus
│  • Events: NDJSON stream of everything that happened
│
│  contains ↓
│
PAPER (input — one per uploaded PDF)
│  A scientific paper in the corpus.
│  • Source PDF + converted Markdown (with page/paragraph metadata)
│  • Themes found in this paper (post-extraction)
│  • Claims extracted from this paper (post-extraction)
│
│  produces ↓
│
THEME (intermediate — extracted per paper, deduplicated across corpus)
│  A thematic concept found across papers.
│  • Canonical name (post-dedup): "Viral Vector Delivery Systems"
│  • Aliases (pre-dedup): ["Viral Vectors", "AAV Delivery", "Vector Systems"]
│  • Papers that discuss this theme
│  • Positions in each paper (page, paragraph)
│
│  contains ↓
│
CLAIM (intermediate — extracted per theme per paper)
│  A specific assertion made in a paper about a theme.
│  • The claim text
│  • Source position: paper_id + page + paragraph
│  • Deep version (full extracted context)
│  • Summary version (one-line)
│
│  referenced by ↓
│
CITATION (output — traceable reference in the review)
│  A pointer from the review text back to a source.
│  • Citation ID (sequential: [1], [2], ...)
│  • Paper reference (author, year, title, journal)
│  • Positions cited: list of (section, page, paragraph)
│
│  composed into ↓
│
REVIEW (output — the final literature review)
   The comprehensive synthesis of all papers.
   • Sections organized by theme
   • Inline citations [N](p.X,§Y)
   • References table with back-references
```

## Relationships

```
Job ──── 1:N ──── Paper (a job processes many papers)
Paper ── 1:N ──── Theme (a paper contains many themes)
Theme ── N:M ──── Paper (a theme spans many papers, via theme_map)
Paper ── 1:N ──── Claim (a paper produces many claims)
Theme ── 1:N ──── Claim (a theme has many claims across papers)
Claim ── 1:1 ──── Citation position (each claim maps to page/paragraph)
Review ─ 1:N ──── Citation (review references many citations)
Citation 1:1 ──── Paper (each citation points to one paper)
```

## Job Lifecycle

```
UPLOADING ──→ PROCESSING ──→ COMPLETED
                  │
                  └──→ FAILED
```

### Processing substages

```
PROCESSING
├── ingestion        (parallel per paper: PDF → Markdown)
├── theme_extraction (parallel per paper: Markdown → themes)
├── claim_extraction (parallel per paper: themes → claims)
├── theme_dedup      (sequential: all themes → unified map)
├── theme_review     (parallel per theme: claims → deep review)
└── aggregation      (sequential: all reviews → final text)
```

## Persistence

```
jobs/{job_id}/
├── status.yaml          # job status + metadata
├── papers.yaml          # paper list with metadata
├── events.ndjson        # append-only event stream
├── themes/
│   └── paper_{id}.yaml  # themes per paper
├── claims/
│   └── paper_{id}.yaml  # claims per paper
├── theme_map.yaml       # deduplicated themes
├── theme_reviews/
│   └── theme_{id}.yaml  # review per theme
└── review.yaml          # final output
```

YAML for structured state. NDJSON for event stream (append-only).

## Qdrant (queryable mirror)

The pipeline writes to both disk (persistence) and Qdrant (queryability). Same data, two purposes:

| Storage | Purpose | Consumer |
|---------|---------|----------|
| Disk (YAML/NDJSON) | Durability, recovery, API responses | Pipeline, REST API |
| Qdrant | Semantic search, assistant queries | papers-mcp → assistant |
