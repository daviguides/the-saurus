# The Saurus — App

React 19 desktop application for the literature review pipeline. Upload scientific PDFs, watch the multi-agent pipeline process them in real time, and read the generated review with traceable citations.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Bundler**: Rsbuild + Module Federation (host)
- **Styling**: Tailwind v4
- **Realtime**: native WebSocket (pipeline events), Socket.IO (assistant chat via federated remote)
- **Port**: 5173

## Structure

```
src/
├── main.tsx                          # Entry point, router setup
├── index.css                         # Tailwind + shared tokens + keyframes
├── core/
│   ├── types/
│   │   ├── pipeline.ts               # Pipeline event types
│   │   ├── paper.ts                  # Paper models
│   │   ├── review.ts                 # Review models
│   │   └── remotes.d.ts              # Module Federation remote types
│   ├── hooks/
│   │   ├── useUpload.ts              # File upload + job creation (POST /jobs)
│   │   ├── useReview.ts              # Fetch review data (GET /jobs/{id}/review)
│   │   ├── usePapers.ts              # Fetch enriched papers (GET /jobs/{id}/papers)
│   │   ├── usePipelineTrace.ts       # WebSocket event stream + stage tracking
│   │   ├── useJobId.ts               # localStorage-backed job_id (useSyncExternalStore)
│   │   └── useTheme.ts              # Light/dark theme toggle
│   ├── context/
│   │   └── AssistantContext.tsx       # Socket.IO context for federated assistant
│   ├── constants/
│   │   └── theme-colors.ts           # Theme color mapping for pipeline stages
│   ├── transforms/
│   │   ├── review.ts                 # Review data transforms
│   │   └── papers.ts                 # Paper data transforms
│   └── services/
│       └── api.ts                    # REST client (PIPELINE_API_URL = :8002)
├── ui/
│   ├── views/
│   │   ├── UploadView.tsx            # Mascot + dropzone (landing page)
│   │   ├── PapersView.tsx            # Per-paper themes and claims
│   │   └── ReviewView.tsx            # Literature review + citations
│   ├── layout/
│   │   ├── AppLayout.tsx             # Shell: header + sidebar + content
│   │   ├── Header.tsx                # Top bar with theme toggle
│   │   └── Sidebar.tsx               # Navigation (upload, papers, review)
│   ├── pipeline/
│   │   ├── PipelineTrace.tsx         # Live stage-by-stage progress
│   │   ├── EventStream.tsx           # Scrolling event log
│   │   ├── StageItem.tsx             # Individual stage row
│   │   ├── PaperSubItem.tsx          # Per-paper progress within a stage
│   │   └── ProgressBar.tsx           # Animated progress bar
│   ├── papers/
│   │   ├── PaperList.tsx             # Paper list container
│   │   ├── PaperListItem.tsx         # Single paper row
│   │   ├── PaperCards.tsx            # Card layout for papers
│   │   ├── ThemeChip.tsx             # Theme tag chip
│   │   ├── EmptyState.tsx            # No papers yet
│   │   └── UploadModal.tsx           # Upload new papers modal
│   ├── review/
│   │   ├── ReviewBody.tsx            # Markdown-rendered review text
│   │   ├── StatsHeader.tsx           # Paper/theme/claim counts
│   │   ├── CitationLink.tsx          # Inline citation [1] with tooltip
│   │   ├── ReferencesSection.tsx     # References list at bottom
│   │   └── slugify.ts               # Reference anchor generation
│   ├── assistant/
│   │   └── FederatedAssistant.tsx    # Module Federation wrapper for chat UI
│   └── shared/
│       ├── TheSaurusMascot.tsx       # SVG dinosaur mascot
│       ├── Tooltip.tsx               # Floating UI tooltip
│       └── Toast.tsx                 # Notification toast
└── mocks/
    ├── pipeline-events.ts            # Mock pipeline event stream
    ├── review.ts                     # Mock review data
    └── papers.ts                     # Mock paper data
```

## Key Hooks

| Hook | Purpose |
|------|---------|
| `useUpload` | Manages file upload lifecycle (idle → uploading → processing → error), calls POST /jobs, stores job_id in localStorage |
| `useJobId` | Reads `thesaurus:job_id` from localStorage via `useSyncExternalStore`, cross-tab aware |
| `usePipelineTrace` | Opens WebSocket to `ws://:8002/jobs/{id}/stream`, accumulates events, tracks stage progress |
| `useReview` | Fetches review YAML from GET /jobs/{id}/review |
| `usePapers` | Fetches enriched papers (themes + claims) from GET /jobs/{id}/papers |
| `useTheme` | Reads/writes `thesaurus:theme` in localStorage, toggles `dark` class on `<html>` |

## Module Federation

Host app (`theSaurusApp`) imports the `theSaurusAssistant` remote from `http://localhost:5174/remoteEntry.js`. Shared singletons: `react`, `react-dom`, `socket.io-client`.

## Design Tokens

Imported from `../../shared/tokens.css`. Light theme by default, dark theme via `class="dark"` on `<html>`. The inline script in `rsbuild.config.ts` applies the dark class before first paint to prevent flash.

## State Management

No external state library. State flows through:
- `localStorage` for persistence: `thesaurus:job_id` (active job), `thesaurus:theme` (light/dark)
- React hooks for runtime state (upload status, pipeline events, review data)
- `useSyncExternalStore` for cross-tab localStorage sync

## Pipeline WebSocket

Connects to `ws://localhost:8002/jobs/{job_id}/stream` for live NDJSON events during pipeline execution. Events drive the PipelineTrace UI (stage progress, per-paper status, completion).

## Animations

Defined in `index.css`:
- `breathe` — mascot idle pulse (opacity 0.8 → 1)
- `tick` — counter number change (scale + opacity pop)
- `fadeIn` — generic fade-in for loading states
- `scaleIn` — review dot appearance in sidebar
- `viewFadeIn` — route transition fade
- `highlight-fade` — citation scroll-to highlight (accent bg → transparent)

## Development

```bash
pnpm dev          # Dev server on :5173 with hot-reload
pnpm build        # Type-check (tsc) + production build
pnpm lint         # ESLint on src/
pnpm preview      # Preview production build
```
