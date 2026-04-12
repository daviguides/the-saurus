# The Saurus: Design System

_Academic warmth meets pipeline clarity._

---

## 1) Design Philosophy

### Core Principles

**Academic, not corporate**
This is a research tool. The UI should feel like a well-organized research notebook — warm paper tones, clean typography, structured information. Not a SaaS dashboard with KPIs.

**Transparent, not magical**
The pipeline is visible. The user sees each stage, each paper being processed, each theme found. The UI communicates "I'm working on this" at all times. No black box.

**Calm density**
Scientific papers are dense. The UI must handle density without feeling cluttered. Clear hierarchy, generous whitespace within sections, compact between items.

### What This Is NOT

- **Not Compass** (maritime/nautical) — different product, different metaphor
- **Not Continuum** (dark tunnel) — this is light, academic, paper-like
- **Not a chat app** — the pipeline is the core, not conversation

### The Mascot

The Saurus — a friendly dinosaur that devours papers. Appears in:
- Empty state ("Feed The Saurus your papers")
- Loading/processing states (subtle animation)
- Error states ("The Saurus choked on that one")

Style: minimal line art, not cartoon. Think scientific illustration meets playful.

---

## 2) Color Palette

### Light theme (primary — academic paper feel)

```css
/* Backgrounds — warm paper, not cold white */
--saurus-paper:           #FAFAF7;     /* main background */
--saurus-surface:         #F5F5F0;     /* cards, elevated surfaces */
--saurus-sidebar:         #F0F0EB;     /* sidebar background */

/* Text — ink on paper */
--saurus-ink:             #1C1C1E;     /* primary text */
--saurus-ink-secondary:   #6B7280;     /* secondary text, metadata */
--saurus-ink-muted:       #9CA3AF;     /* timestamps, hints */

/* Primary — deep academic blue-green */
--saurus-primary:         #2D6A4F;     /* actions, links, active states */
--saurus-primary-hover:   #40916C;     /* hover */
--saurus-primary-bg:      rgba(45, 106, 79, 0.08);  /* subtle backgrounds */

/* Accent — amber/gold for highlights */
--saurus-accent:          #D4AF37;     /* CTA, important indicators */
--saurus-accent-bg:       rgba(212, 175, 55, 0.10);

/* Status — pipeline stages */
--saurus-success:         #40916C;     /* completed stages */
--saurus-active:          #2D6A4F;     /* processing */
--saurus-pending:         #9CA3AF;     /* waiting */
--saurus-error:           #DC2626;     /* failed */

/* Theme chips — muted academic colors */
--saurus-chip-1:          #EDE9FE;     /* lavender */
--saurus-chip-2:          #DBEAFE;     /* sky */
--saurus-chip-3:          #D1FAE5;     /* mint */
--saurus-chip-4:          #FEF3C7;     /* cream */
--saurus-chip-5:          #FCE7F3;     /* rose */
--saurus-chip-6:          #E0E7FF;     /* indigo */
```

### Dark theme (warm dark — aged paper under candlelight)

```css
/* Backgrounds — warm charcoal, never pure black */
--saurus-paper:           #1A1D1E;     /* main background */
--saurus-surface:         #242728;     /* cards, elevated surfaces */
--saurus-sidebar:         #161819;     /* sidebar background */

/* Text — warm off-white on dark */
--saurus-ink:             #E8E4DD;     /* primary text (warm off-white) */
--saurus-ink-secondary:   #9CA3AF;     /* secondary text, metadata */
--saurus-ink-muted:       #6B7280;     /* timestamps, hints */

/* Primary — lightened green for contrast on dark */
--saurus-primary:         #5BAB8A;     /* actions, links, active states */
--saurus-primary-hover:   #7CC4A5;     /* hover */
--saurus-primary-bg:      rgba(91, 171, 138, 0.10);  /* subtle backgrounds */

/* Accent — slightly brighter gold */
--saurus-accent:          #E5C349;     /* CTA, important indicators */
--saurus-accent-bg:       rgba(229, 195, 73, 0.10);

/* Status — pipeline stages */
--saurus-success:         #5BAB8A;     /* completed stages */
--saurus-active:          #5BAB8A;     /* processing */
--saurus-pending:         #6B7280;     /* waiting */
--saurus-error:           #F87171;     /* failed (softened red) */

/* Theme chips — muted dark academic colors */
--saurus-chip-1:          #2D2640;     /* lavender dark */
--saurus-chip-2:          #1E2D3D;     /* sky dark */
--saurus-chip-3:          #1A2E26;     /* mint dark */
--saurus-chip-4:          #2E2A1A;     /* cream dark */
--saurus-chip-5:          #2E1A24;     /* rose dark */
--saurus-chip-6:          #1E2240;     /* indigo dark */
```

### Semantic token mapping (for Tailwind/CSS)

Both themes use the same semantic names. The `class="dark"` on `<html>` toggles between them.

```css
/* Semantic tokens used in components */
--color-bg              → --saurus-paper
--color-surface         → --saurus-surface
--color-sidebar         → --saurus-sidebar
--color-border          → light: #E8E5DE / dark: #353838
--color-primary         → --saurus-primary
--color-primary-hover   → --saurus-primary-hover
--color-primary-bg      → --saurus-primary-bg
--color-accent          → --saurus-accent
--color-accent-bg       → --saurus-accent-bg
--color-text-primary    → --saurus-ink
--color-text-secondary  → --saurus-ink-secondary
--color-text-muted      → --saurus-ink-muted
--color-success         → --saurus-success
--color-error           → --saurus-error
--color-pending         → --saurus-pending
```

### Shadows (per theme)

```css
/* Light */
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.04);
--shadow-md:  0 2px 8px rgba(0, 0, 0, 0.06);

/* Dark */
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.20);
--shadow-md:  0 2px 8px rgba(0, 0, 0, 0.30);
```

### Theme rationale

Light is the default for the academic audience. Dark exists for extended use (developer comfort). Both maintain warmth — the dark theme is "aged paper under candlelight", not a code terminal. No pure black (#000), no pure white (#FFF) in either theme.

### Prose heading color progression

Headings use a progression from primary to lighter/muted for hierarchy:

```css
/* Light */
h1: #2D6A4F (primary)
h2: #2D6A4F (primary)
h3: #40916C (primary-hover / lighter green)
h4: #6B7280 (secondary)

/* Dark */
h1: #5BAB8A (primary)
h2: #5BAB8A (primary)
h3: #7CC4A5 (primary-hover / lighter)
h4: #9CA3AF (secondary)
```

---

## 3) Typography

```css
/* Headings — serif for academic feel */
--font-heading: 'Literata', Georgia, serif;

/* Body — clean sans for UI and dense content */
--font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* Review output — serif for the generated literature review */
--font-review: 'Literata', Georgia, serif;

/* Mono — citations, metadata, code */
--font-mono: 'Fira Code', 'SF Mono', Consolas, monospace;
```

### Scale

```css
--text-xs:    12px;    /* metadata, timestamps, citation positions */
--text-sm:    14px;    /* secondary content, labels, claims */
--text-base:  16px;    /* body text, paper titles */
--text-lg:    18px;    /* section headings in review */
--text-xl:    24px;    /* view titles */
--text-2xl:   32px;    /* review title */
```

### Review rendering

The literature review output uses serif font (Literata) to feel like a real academic document. Body text at 16px with 1.7 line-height for readability. Citations in mono at 12px.

---

## 4) Spacing & Layout

### Layout

```
┌──────────────────────────────────────────────────────┐
│ Header (48px, paper-surface bg)                      │
├────────┬─────────────────────────────────────────────┤
│        │                                              │
│ Sidebar│         Content Area                         │
│ 64px   │         max-width: 960px (review)            │
│ icons  │         full-width (papers list)              │
│        │                                              │
└────────┴─────────────────────────────────────────────┘
```

### Border-radius

```css
--radius-sm:   4px;    /* chips, badges */
--radius-md:   8px;    /* buttons, inputs */
--radius-lg:   12px;   /* cards, paper items */
```

### Shadows

```css
/* Subtle — paper-on-paper feel */
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.04);
--shadow-md:  0 2px 8px rgba(0, 0, 0, 0.06);
```

---

## 5) Components

### Pipeline Trace

```
✅ Ingestion         40/40 converted         ← success color + check
🔄 Claim Extraction  19/40 · 54 claims       ← primary color + spinner
⏳ Theme Dedup                                ← muted color + clock
```

- Completed: `--saurus-success` + check icon
- Active: `--saurus-primary` + animated spinner
- Pending: `--saurus-ink-muted` + clock icon
- Sub-items: indented, smaller text, tree lines

### Paper Card (expandable)

```
┌─────────────────────────────────────────────────────┐
│ [1] Liu, W. et al. — "AAV9-mediated CRISPR..."  ▾  │
│     5 themes · 8 claims                             │
│                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│  │ chip-1 bg  │ │ chip-2 bg  │ │ chip-3 bg  │     │
│  └────────────┘ └────────────┘ └────────────┘     │
│                                                     │
│  • "Claim text here"                                │
│    p.12, §3 · Theme name          ← mono, muted    │
└─────────────────────────────────────────────────────┘
```

- Surface bg, subtle shadow
- Expand/collapse with chevron
- Theme chips use rotating chip colors
- Claims: body font, citation position in mono/muted

### Citation in Review

```
...therapeutic levels of gene expression [1](p.12,§3)...
```

- `[1]` — primary color, clickable (scrolls to reference)
- `(p.12,§3)` — mono, muted, hover for tooltip

### References Entry

```
[1] Liu, W. et al. (2024). "AAV9-mediated CRISPR correction..."
    Nature Gene Therapy, 31(4), 412-428.
    ▸ Cited in: §2.1 (p.12,§3), §2.7 (p.3,§1)
```

- Author/title in body font
- Journal in italic
- Back-references in muted, ▸ prefix

### Empty State (The Saurus mascot)

Centered in content area. Minimal line-art dinosaur illustration. Below:
- "Feed The Saurus your papers"
- "Drop PDF files or click to browse"

### Progress Bar

```css
/* Warm gradient, not cold blue */
background: linear-gradient(90deg, var(--saurus-primary), var(--saurus-accent));
```

---

## 6) Animation

Minimal. Academic tools don't bounce.

```css
/* Stage transitions */
.stage-complete { transition: color 200ms ease, opacity 200ms ease; }

/* Spinner for active stage */
.stage-active .icon { animation: spin 1s linear infinite; }

/* Card expand */
.card-expand { transition: max-height 200ms ease-out; }

/* Progress bar */
.progress-bar { transition: width 300ms ease; }
```

No breathing, no bounce, no slide-in. Things appear, transition color, expand/collapse. That's it.

---

## 7) Ecosystem Position

| Aspect | Compass | Ciclus | Continuum | The Saurus |
|--------|---------|--------|-----------|------------|
| Theme | Maritime wayfinding | Natural cycles | Dark focus tunnel | Academic paper |
| Base | Dark, semi-opaque | Translucent | Dark, opaque | Light, warm |
| Heading | Literata (serif) | Cormorant (serif) | Geist (sans) | Literata (serif) |
| Primary | Horizon blue | Pulse gold | CTP blue | Academic green |
| Accent | Gold | Gold | Blue | Gold |
| Feel | Nautical chart | Window to nature | Control terminal | Research notebook |

The Saurus shares Literata and gold accent with Compass (same author's DNA) but is its own thing: light, academic, warm paper tones.
