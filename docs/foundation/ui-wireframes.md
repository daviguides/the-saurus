# UI Wireframes: Literature Review Pipeline

**Date**: 2026-04-10
**Status**: Exploration complete

---

## Layout

Sidebar (mini) + content area. Assistant opens as drawer from header button.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ◉ The Saurus                                         💬 Assistant      │
├─────┬────────────────────────────────────────────────────────────────────┤
│     │                                                                    │
│ ⊕   │  Content area                                                     │
│Upload│  (changes based on selected view)                                 │
│     │                                                                    │
│ 📄  │                                                                    │
│Papers│                                                                    │
│     │                                                                    │
│ 🔬  │                                                                    │
│Review│                                                                    │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

### Sidebar items

| Item | Type | Function |
|------|------|----------|
| **⊕ Upload** | Action | Opens modal/dropzone. Always accessible |
| **📄 Papers** | View | Paper list. States: empty, uploaded, processing, complete |
| **🔬 Review** | View | Literature review output. Disabled until pipeline completes |

### Assistant

Opens as drawer from the right (💬 button in header). Not a sidebar view, overlays/pushes content. Uses papers-mcp to answer about any pipeline output.

---

## Papers View — State: Empty (first visit)

```
┌─────┬────────────────────────────────────────────────────────────────────┐
│     │                                                                    │
│ ⊕   │                                                                    │
│     │                                                                    │
│ 📄  │         ┌─────────────────────────────────────────┐                │
│ ◀━  │         │                                         │                │
│     │         │       Drop your papers here             │                │
│ 🔬  │         │       PDF files · up to 50 papers       │                │
│     │         │                                         │                │
│     │         │         [ Browse files ]                │                │
│     │         │                                         │                │
│     │         └─────────────────────────────────────────┘                │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

---

## Papers View — State: Uploaded

```
┌─────┬────────────────────────────────────────────────────────────────────┐
│     │                                                                    │
│ ⊕   │  Papers (40)                                    [ + Add more ]    │
│     │                                                                    │
│ 📄  │  ☑ Liu, W. et al. — AAV9-mediated CRISPR...            12 pg     │
│ ◀━  │  ☑ Santos, R. et al. — Ex vivo CRISPR...                8 pg     │
│     │  ☑ Nakamura, T. et al. — Challenges in...              14 pg     │
│ 🔬  │  ☑ Kim, H. et al. — LNP-delivered Cas9...              10 pg     │
│     │  ...                                                               │
│     │  ☑ Okonkwo, A. et al. — Global regulatory...            6 pg     │
│     │                                                                    │
│     │  40 papers selected · ~380 pages total                             │
│     │                                                                    │
│     │  ┌───────────────────────────────────────────────────────────┐    │
│     │  │              ▶  Generate Literature Review                │    │
│     │  └───────────────────────────────────────────────────────────┘    │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

---

## Papers View — State: Processing

```
┌─────┬────────────────────────────────────────────────────────────────────┐
│     │                                                                    │
│ ⊕   │  Papers (40)                                    Processing...     │
│     │                                                                    │
│ 📄  │  Pipeline                                         68% · ~3 min   │
│ ◀━  │  ┌──────────────────────────────────────────────────────────┐    │
│     │  │ ██████████████████████████████░░░░░░░░░░░░░░░            │    │
│ 🔬  │  └──────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     │  ✅ Ingestion              40/40 converted                         │
│     │  ✅ Theme Extraction       40/40 · 847 themes raw                  │
│     │  🔄 Claim Extraction       19/40 · 54 claims so far               │
│     │     ├─ Liu, W. — 8 claims                                         │
│     │     ├─ Santos, R. — 5 claims                                      │
│     │     └─ 21 remaining...                                            │
│     │  ⏳ Theme Dedup                                                     │
│     │  ⏳ Theme Reviews                                                   │
│     │  ⏳ Aggregation                                                     │
│     │                                                                    │
│     │  ─ Event Stream ──────────────────────────────── ▾                │
│     │  14:32:01  theme_extracted  Paper [3] — 4 themes                  │
│     │  14:32:03  claim_extracted  Paper [1] — "AAV9 achieves..."        │
│     │  14:32:04  theme_extracted  Paper [4] — 3 themes                  │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

---

## Papers View — State: Complete (per-paper findings)

```
┌─────┬────────────────────────────────────────────────────────────────────┐
│     │                                                                    │
│ ⊕   │  Papers (40)                                       🔍 Filter     │
│     │  14 themes · 127 claims                                           │
│ 📄  │                                                                    │
│ ◀━  │  ┌──────────────────────────────────────────────────────────┐    │
│     │  │ [1] Liu, W. et al. — "AAV9-mediated CRISPR..."    ▾    │    │
│ 🔬  │  │     5 themes · 8 claims                                 │    │
│ ●   │  │                                                         │    │
│     │  │  Themes:                                                │    │
│     │  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐     │    │
│     │  │  │Viral Vectors │ │Cardiac Tissue│ │Dose-Resp.  │     │    │
│     │  │  └──────────────┘ └──────────────┘ └────────────┘     │    │
│     │  │                                                         │    │
│     │  │  Claims:                                                │    │
│     │  │  • "AAV9 achieves therapeutic levels of gene            │    │
│     │  │    expression in cardiac tissue"                        │    │
│     │  │    p.12, §3 · Viral Vectors                            │    │
│     │  │                                                         │    │
│     │  │  • "Capsid-engineered AAV variants show 60%            │    │
│     │  │    reduction in antibody binding"                       │    │
│     │  │    p.18, §1 · Immunogenicity                           │    │
│     │  │  ...                                                    │    │
│     │  └──────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     │  ┌──────────────────────────────────────────────────────────┐    │
│     │  │ [2] Santos, R. et al. — "Ex vivo CRISPR..."      ▸    │    │
│     │  │     3 themes · 5 claims                                 │    │
│     │  └──────────────────────────────────────────────────────────┘    │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

Note: 🔬 Review shows ● dot indicator when review is ready.

---

## Review View

```
┌─────┬────────────────────────────────────────────────────────────────────┐
│     │                                                                    │
│ ⊕   │  Literature Review: CRISPR Gene Therapy Approaches                │
│     │  40 papers · 14 themes · 127 claims · Generated 2 min ago        │
│ 📄  │                                                                    │
│     │  ───────────────────────────────────────────────────────────      │
│ 🔬  │                                                                    │
│ ◀━  │  1. Introduction                                                  │
│     │                                                                    │
│     │  Gene therapy using CRISPR-Cas9 has emerged as a transformative   │
│     │  approach in treating monogenic disorders. Multiple studies        │
│     │  demonstrate efficacy in ex vivo applications [1][2], while       │
│     │  in vivo delivery remains a significant challenge [3][5].         │
│     │                                                                    │
│     │  2. Thematic Analysis                                              │
│     │                                                                    │
│     │  2.1 Viral Vector Delivery Systems                                │
│     │                                                                    │
│     │  Adeno-associated virus (AAV) vectors remain the dominant         │
│     │  delivery platform, reported in 23 of 40 papers reviewed.         │
│     │  Liu et al. demonstrate that AAV9 achieves therapeutic levels     │
│     │  of gene expression in cardiac tissue [1](p.12,§3), while        │
│     │  Chen et al. report dose-dependent hepatotoxicity at higher       │
│     │  titers [7](p.4,§2).                                             │
│     │                                                                    │
│     │  ...                                                               │
│     │                                                                    │
│     │  ───────────────────────────────────────────────────────────      │
│     │                                                                    │
│     │  References                                                        │
│     │                                                                    │
│     │  [1] Liu, W. et al. (2024). "AAV9-mediated CRISPR correction"    │
│     │      Nature Gene Therapy, 31(4), 412-428.                         │
│     │      ▸ Cited in: §2.1 (p.12,§3), §2.7 (p.3,§1)                 │
│     │                                                                    │
│     │  [2] Santos, R. et al. (2024). "Ex vivo CRISPR editing"          │
│     │      Blood, 143(8), 1102-1115.                                    │
│     │      ▸ Cited in: §1 (p.1,§2), §2.3 (p.6,§4)                    │
│     │                                                                    │
│     │  ...                                                               │
│     │                                                                    │
└─────┴────────────────────────────────────────────────────────────────────┘
```

---

## Review View — With Assistant Drawer Open

```
┌─────┬──────────────────────────────────────────┬─────────────────────────┐
│     │                                          │                         │
│ ⊕   │  Literature Review: CRISPR Gene...      │  Assistant              │
│     │  40 papers · 14 themes · 127 claims     │                         │
│ 📄  │                                          │  Ask about this         │
│     │  ──────────────────────────────────      │  review...              │
│ 🔬  │                                          │                         │
│ ◀━  │  1. Introduction                        │  ┌─────────────────┐   │
│     │                                          │  │  Send            │   │
│     │  Gene therapy using CRISPR-Cas9 has     │  └─────────────────┘   │
│     │  emerged as a transformative approach    │                         │
│     │  in treating monogenic disorders.        │  ──────────────────    │
│     │  Multiple studies demonstrate efficacy   │                         │
│     │  in ex vivo applications [1][2],         │  You:                   │
│     │  while in vivo delivery remains a        │  "Which papers discuss  │
│     │  significant challenge [3][5].           │  AAV toxicity?"         │
│     │                                          │                         │
│     │  2. Thematic Analysis                    │  Bot:                   │
│     │                                          │  "Based on the claims,  │
│     │  2.1 Viral Vector Delivery Systems      │  papers [7], [14], [22] │
│     │                                          │  address AAV toxicity.  │
│     │  AAV vectors remain the dominant         │  Chen et al. [7]        │
│     │  delivery platform, reported in 23       │  reports dose-dependent │
│     │  of 40 papers. Liu et al. demonstrate   │  hepatotoxicity at      │
│     │  that AAV9 achieves therapeutic          │  high titers (p.4,§2)"  │
│     │  levels [1](p.12,§3)...                 │                         │
│     │                                          │                         │
│     │  ──────────────────────────────────      │                         │
│     │  References                              │                         │
│     │  [1] Liu, W. et al. (2024)...           │                         │
│     │                                          │                         │
└─────┴──────────────────────────────────────────┴─────────────────────────┘
```

---

## Citation Interactions

Each `[N](p.X,§Y)` in the review text:
- **Hover**: tooltip with paper title + claim summary
- **Click**: scroll to reference in References section

Each reference entry shows back-references: where in the review it was cited (`▸ Cited in: §2.1, §2.7`).
