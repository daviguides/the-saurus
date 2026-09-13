# The Saurus — Atmosphere Brief for Landing R2 (Phase E)

_This is the single instruction set for building the final landing page. It consolidates `landing-brief.md` (copy and structure, which are locked), `positioning.md` (voice), `design-system.md` (tokens), the two benchmarking documents (techniques and anti-patterns), and a diagnosis of the four Round 1 landings. An implementer should be able to produce the correct page from this file alone._

_Rule of precedence: positioning > landing-brief copy > this brief > any R1 file. Copy in R2 is verbatim from `landing-brief.md` sections 1–12. This document governs everything that is not copy: scale, rhythm, silence, components, code quality._

---

## 0. The one-paragraph target

A reader lands on warm paper, not a SaaS grid. A serif headline the size of a journal masthead says "Feed The Saurus your papers." and a small line-art dinosaur is eating a folder of PDFs. Nothing is animated. There is more empty space than text. Scrolling down, the page reads like a longform essay with four exhibits set into it: a merged-theme card, a citation receipt, a three-step verification diagram, and a pipeline trace that shows a skipped paper and a retry. Halfway down, the page goes dark for one screen and says a single sentence, then returns to paper. It ends on the same headline it opened with, asks once, and signs off with the only exclamation mark on the page. The reader should feel that a careful colleague built this, and that nothing was hidden from them.

---

## 1. Atmosphere Definition

### 1.1 Mood: academic warmth, not SaaS

The page is a research notebook that happens to be a website. Concretely:

| Property | Do | Do not |
|---|---|---|
| Ground | `#FAFAF7` paper, `#F5F5F0` surface, `#F0F0EB` sidebar/footer | Pure white, gradients, glows, mesh backgrounds |
| Ink | `#1C1C1E`; secondary `#6B7280`; muted `#9CA3AF` (never below 12px in muted) | Gray-on-gray at small sizes; muted ink for anything the reader must read |
| Emphasis | One green (`#2D6A4F`) for headings, links, checks; one gold (`#D4AF37`) for the CTA, the entailment underline, the receipt border, the pull-quote rule | Violet, blue, red for "bad", multi-color status systems |
| Edges | 1px hairlines (`#E8E5DE`), radius 4/8/12px, shadows `--shadow-sm`/`--shadow-md` only | `shadow-lg`, hover lifts (`translateY`), glass/blur cards, borders thicker than 3px |
| Type | Literata for anything the page *says*; Inter for anything it *explains*; Fira Code for anything it *records* | Uppercase tracked labels, geometric sans headlines, weight 700+ anywhere |
| Motion | Fade-in (opacity + 8–10px rise, 500ms) on specimen panels only; one spinner | Fade on headings/eyebrows/paragraphs, hover transforms, scroll pinning, counters |
| Mascot | Sections 1, 3 (glyph at "Feed"), 11 | Sections 5–10, nav, footer, favicon at hero scale |

The heuristic when in doubt: would this element look at home in a well-typeset PDF of a journal article? Hairlines, small caps in mono, pull quotes, figure captions: yes. Cards with lift on hover, pill badges with tracking, gradient buttons: no.

### 1.2 "Scale larger than the app": concrete numbers

The app is a 16px tool. The landing is a display document. Every measure below is larger than its app equivalent.

```css
/* Display */
--h1:        clamp(48px, 7vw, 96px);     /* hero and close H2; Literata 500; lh 1.02; ls -0.02em; max-width 11ch */
--h2:        clamp(40px, 4.4vw, 56px);   /* section H2; Literata 500; lh 1.1; ls -0.015em; max-width 20ch */
--h2-act:    clamp(40px, 5.4vw, 72px);   /* act-break H2; Literata 400; lh 1.12; max-width 22ch; centered */
--h3:        24px;                        /* failure modes, loop steps, verification nodes; Literata 500 */
--sub-hero:  clamp(24px, 2.4vw, 32px);   /* hero sub; Literata 400; lh 1.3; max-width 28ch */
--statement: clamp(22px, 2.4vw, 30px);   /* "closing line" in sections 3, 7, 10; Literata 500; lh 1.4; max-width 36ch */
--pullquote: clamp(30px, 3.4vw, 46px);   /* section 2; Literata italic 400; primary green; lh 1.2; max-width 14ch */

/* Reading */
--lead:      clamp(18px, 1.4vw, 20px);   /* Inter 400; lh 1.65; max-width 62ch */
--body:      18px;                        /* Inter 400; lh 1.7; max-width 54–60ch inside specimens' copy columns */
--small:     15px;                        /* Inter; table cells, card lists, loop step bodies, chat blocks */

/* Recording */
--mono:      13px;                        /* Fira Code; eyebrows, captions, citation addresses, log lines; letter-spacing .01em */
--mono-min:  12px;                        /* absolute floor for any mono text; nothing on the page is smaller */
--review:    clamp(20px, 1.8vw, 24px);   /* Literata 400; lh 1.75; the generated-review excerpt in section 6 */
```

Heading color is `--saurus-primary` (light `#2D6A4F`, dark `#5BAB8A`) for H1 and H2, per the design system's heading progression. H3 in ink. Weight never exceeds 600; H1/H2 at 500.

App crops (merged theme card, receipt card, trace stage list) are rendered at roughly 1.3–1.4× app scale: card padding 24–28px instead of 16, stage rows 15px instead of 13, metric values 32px Literata instead of 20.

### 1.3 "Editorial breathing" in CSS

Breathing is vertical distance that is large, consistent, and asymmetric in favor of the top of each block.

```css
/* Section rhythm */
--sec-y:     clamp(112px, 12vw, 192px);  /* padding-block for every section, desktop */
/* mobile (≤ 760px): padding-block 80px; never below 72px */

/* Inside a section */
eyebrow → H2                margin-bottom: 22–24px
H2 → lead                   margin-bottom: 28px
lead → lead                 margin-top: 20–26px   (paragraph spacing inside .prose)
lead → specimen/exhibit     margin-top: 56–64px
specimen → caption          margin-top: 28–32px
caption → statement         margin-top: 56px
statement → next section    handled by --sec-y

/* Hero */
hero min-height: calc(100vh - 64px); padding-block clamp(56px, 8vh, 96px)
H1 → sub: 28px · sub → body: 28px · body → CTA row: 36px · CTA → micro: 18px · micro → shelf: 44px

/* Containers */
.wrap   max-width: 1360px; padding-inline: clamp(20px, 4vw, 56px)
.prose  max-width: 62–66ch
two-column proof grids: 5fr / 7fr (copy / specimen) with column-gap clamp(40px, 6vw, 96px)
```

Whitespace ratio as a check: on a 1440×900 desktop viewport, at any scroll position in Act 1, no more than ~45% of the viewport should be occupied by text or exhibits. In Act 2, exhibits may fill up to ~60%. The close should be under 35%.

### 1.4 The dark act break: exact spec

Section 4 is the only dark element on the page in light mode.

```css
.act-break {
  background: #1A1D1E;            /* dark --saurus-paper, literally */
  color: #E8E4DD;                 /* dark --saurus-ink */
  padding-block: clamp(120px, 36vh, 320px);   /* mobile: min 112px */
  text-align: center;
}
.act-break h2 {
  font: 400 clamp(40px, 5.4vw, 72px)/1.12 Literata;
  color: #E8E4DD;
  max-width: 22ch; margin-inline: auto;
}
.act-break h2 em { font-style: normal; color: #5BAB8A; }   /* optional: second sentence in dark-mode green */
.act-break p {
  font: 400 18px/1.6 Inter; color: #9CA3AF;
  max-width: 52ch; margin: 28px auto 0;
}
```

- Nothing else in the band: no border, no gradient, no texture, no mascot, no icon, no reveal animation. The H2 and the one-line sub are present on first paint.
- The sentence break is set so "Here is what happens after that." starts a new line on desktop (use `<br>` or the `em` span with `display:block` above 900px).
- In dark mode the band must still register as a change: use `#101213` background with 1px `#353838` top/bottom borders (Kimi's approach). The band is the act change, not a color; it must read as one in both themes.
- Everything after the band returns to `--saurus-paper`. Section 5 has no top border.

### 1.5 Mu / the void: where the page is deliberately silent

"Mu" here means an intentional absence that carries meaning. The page has eight of them. Each is a place where an R1 implementation or a competitor would have put something, and R2 must not.

1. **Hero has no product screenshot.** Copy, mascot, two pills. The absence says: we are not going to sell you a dashboard.
2. **Section 2 has no visuals at all.** Three failure modes as typographic subheads with hairlines; a pull quote. No icons, no numbered badges, no cards. The absence says: we know what you do for a living, we do not need to illustrate it.
3. **The act break is empty except for one sentence.** The absence resets attention.
4. **The receipt card has no decoration beyond one gold underline and one gold border.** No badge stack, no icons, no "verified" seal. The absence says: the evidence is enough.
5. **The trace is not all green.** A skipped paper and a reask sit in plain ink. The absence of alarm color says: failure is information.
6. **Section 7 ends with a limit statement set apart by a hairline.** The absence of a follow-up reassurance is the point; the last thing the skeptical reader sees is the tool stating what it does not check.
7. **Section 9 has no competitor logos.** Names in plain text. The absence says: no rivalry.
8. **The close is mostly whitespace.** Headline, sub, two CTAs, two preset cards, a small mascot, one sentence. No feature recap, no testimonials, no metrics band, no newsletter form.

Two smaller silences: eyebrows are sentence case (`Stage 2 · Theme Dedup`), not uppercase; and there is exactly one animated element on the page (the spinner in the trace), which stops under `prefers-reduced-motion`.

---

## 2. Benchmarking Techniques to Apply

Every item below is mandatory in R2 unless marked optional.

### 2.1 Pre-digested corpus shelf (Semantic Scholar query pills, Consensus chips)
- Hero, below the micro-line. Label in mono: `Or inspect a pre-digested sample corpus:`; two pills, surface background, 1px border, title Inter 15px 500, metrics Fira Code 12px muted. Hover: border turns primary. No transform.
- Both pills link to a real destination. If the organoid corpus does not exist at publish time, show one pill (see Open Items). Do not link a placeholder pill to `#close` or to a dialog.
- Repeated at card scale in section 11 with the `Inspect the review →` line.

### 2.2 Verification receipt card (Jenni AI claim popup, Elicit sentence-level citations, AnswerThis highlight-jump, surpassed)
- Section 6, right pane (~40%), rendered open, static. Surface background, 3px gold left border, `--shadow-md`, radius 12px, padding 28px.
- Contents in this order: badge `✓ Grounded citation` (mono 12.5px, primary); address `[11] Kalsbeek et al. 2024 · p.12 · §3` (mono 13.5px, ink); blockquote in Literata italic 17px with the entailing clause underlined (2px gold, `text-underline-offset: 4px`, no highlight fill); 2×2 audit grid (`dt` mono 11.5px muted / `dd` Inter 15px; NLI score and Claim ID in mono); footer `Checked by NLI cross-encoder · citation guard passed` (mono 11.5px muted).
- A 1px gold tether from the active citation pill in the left pane to the card's left edge, with a 7px gold dot at the pill end. Hidden below 960px.
- The active citation in the review excerpt: `[11](p.12,§3)` with a 2px gold bottom border and raised 2px. The other citations are plain pills: `[n]` primary green, `(p.x,§y)` muted mono, both Fira Code at 0.62em of the review size.
- The NLI score, threshold, claim ID, and quote must come from one real job before publishing. Until then, the page carries one global note (see 2.9), not a caveat under every exhibit.

### 2.3 Honest trace with failures (no competitor does this)
- Section 8: one framed panel on surface, hairline border, `--shadow-md`, radius 12px. Three parts: header (job badge, corpus title, four metric tiles with Literata 32px values and mono labels), stage list, event-log strip on sidebar background.
- Stage list rows: grid `28px 160px 1fr auto`, Inter 15px, padding 11px 28px. Status: done = green check SVG; active = green spinner (the only animation); pending = muted circle. Sub-rows (`└ [7] Sørensen et al.  could not be parsed · skipped`, `└ batch 3  reask · entailment 0.41 < 0.60 · retry 1/2`) in 13.5px secondary ink, indented under their stage. The skipped paper is in ink, not red. `resumed from journal` is a right-aligned mono line under the stage list, not attached to any single stage.
- Event log: `<pre>` Fira Code 12.5px, lh 1.7, timestamps muted, one keyword per line in primary green at most (the merged theme name, the passed score). Horizontal scroll inside its own container on mobile; the page never scrolls sideways.
- Panel is light. It is a lab notebook page, not a terminal.

### 2.4 Typographic pairing (Elicit's Martina Plantijn + Plex Mono, adapted)
- Literata carries authority: H1, H2, H3, hero sub, pull quote, statements, the review excerpt, the receipt blockquote, metric values, the footer tagline, the mascot sign-off.
- Inter carries explanation: leads, bodies, table cells, card lists, chat blocks, buttons, nav.
- Fira Code carries evidence: eyebrows, captions, citation addresses, job badges, alias lines, stage sublabels, log lines, the micro-line, preset metrics, footer column heads.
- Never mix roles: no Inter headings, no mono body copy, no Literata in a button.
- Load exactly: Literata 400/500/600 + italic 400/500 (opsz axis on), Inter 400/500/600, Fira Code 400/500, `display=swap`, with `Georgia`, system sans, and `SF Mono, Consolas` fallbacks.

### 2.5 Methodological diagram with loopback (PRISMA flow, Elicit whitepapers)
- Section 7: three nodes in a row on desktop (grid, gap 40px), vertical on mobile. Each node: 56px hairline circle with the number in Literata 22px, then H3 (`Entailment.`), mono sublabel (`NLI cross-encoder`), Inter 15.5px body. A 1px rule at circle-center height connects the three (hidden on mobile). Node 3 carries a small return-arrow SVG with the mono label `writing agent`.
- Below the diagram: one trace line in the pipeline-trace style at small scale, with the spinner: `⟳ Theme Review · batch 3 · reask · entailment 0.41 < 0.60 · retry 1/2`.
- Then the statement, then the limit statement (Inter 16.5px secondary ink, hairline above, max 62ch). Nothing after the limit statement.

### 2.6 Stack vs Matrix contrast (Consensus's search-vs-consensus framing)
- Section 3: two cards side by side, equal width, gap 24px. Left ("The summary stack"): mono label, Literata 20px subline, four mono rows on paper background (fourth dashed and muted), verdict in muted ink. Right ("The theme matrix"): 3px primary top border, two theme rows in the app's merged-theme styling at reduced scale (Literata 18px title, 14px "Draws on…" line with `[n]` in green mono, 14px muted note), verdict in primary green.
- Optional: hovering a theme row tints its `[n]` pills with `--saurus-primary-bg`. No transforms.

### 2.7 "What it will not do" boundary (Ai2's non-commercial restraint)
- Section 10: two surface cards, hairline border, Literata 22px headings, lists with hairline separators; left list marks are green `✓` in mono, right list marks are muted `–` (never red crosses).
- Beside the copy, a static export control: `Export · Markdown / PDF` (mono 12.5px, hairline border, download glyph). Add BibTeX only if it ships (Open Items).

### 2.8 Upstream/downstream positioning (Research Rabbit's ecosystem stance, AnswerThis's "we finish the draft" framing without the bashing)
- Section 9: H2, short lead naming the tools they already use and what each does well, then the five-row table. Table: Inter 15px, hairline rows only, first column Literata 17px, third column header in primary green, no row or column shading, no logos. Horizontal scroll container below 640px.

### 2.9 Cropped evidence frames (Jenni's editor crops)
- Every exhibit is a crop, not a screenshot: no browser chrome, no app header, no sidebar, no window frame. Exhibits sit directly on the page or in a single hairline panel. Section 6's manuscript pane is a surface card with generous padding (clamp 28–56px) so the review text reads as a manuscript.
- One global specimen note replaces per-exhibit caveats: in the section 8 job badge, `JOB circadian-2026-09 · Recorded sample run`. If publishing before real data lands, add exactly one sentence in the footer bottom line: `Exhibits show a recorded sample run.` Nothing else on the page apologizes for itself.

### 2.10 Monospaced eyebrows (Elicit, Research Rabbit)
- Every section except 4, 9, 11 opens with a Fira Code 13px eyebrow in secondary ink, sentence case as written in the copy (`A literature review pipeline`, `The bookkeeping barrier`, `Corpus, not document`, `Stage 2 · Theme Dedup`, `Stage 4 · Aggregation`, `Verification`, `Pipeline Trace`, `The division of labor`). Letter-spacing `.02em`, never uppercase.
- Section 3's mono caption under the loop (`Paper Analysis → Theme Dedup → Theme Review → Aggregation`) ties the friendly names to the stage names the reader will see in section 8. Keep it.

### 2.11 Narrative act break (structural innovation)
- As specified in 1.4. This is the single strongest structural differentiator in the benchmark; do not soften it, shorten it, or add anything to it.

### 2.12 Privacy line and open artifacts (AnswerThis's "Your research stays yours", Jenni/Research Rabbit export badges)
- The micro-line `Open source · Runs locally · 20 to 100 PDFs per job` under the hero CTAs and `Open source · Runs locally · No papers retained for training` in the footer bottom line are the privacy statement. Plain mono text, no shield icons, no lock glyphs.
- Footer "Exports" column lists only formats that ship.

---

## 3. Anti-Patterns to Enforce

A pre-publish grep list follows this section. Everything here is a hard failure, not a preference.

### 3.1 From the competitor analysis
- **No SaaS clichés.** No "10x", "supercharge", "unlock", "leverage", "seamless", "game-changing", "in minutes" as a promise (the phrase "minutes of bookkeeping" appears only in the section 9 table, verbatim from positioning).
- **No bare accuracy claims.** Never "accurate", "hallucination-free", "guaranteed", "trustworthy", "reliable", "flawless", "always". Say what is checked and by what.
- **No AI ghostwriting framing.** Never "writes your review", "finishes your chapter", "AI writer", "autocomplete", "paraphrase". The page says "draft" and "the researcher stays the author".
- **No feature bloat.** One product, four proofs. No feature grid, no icon wall, no "and also" section.
- **No consensus meter, percentage bars, or agreement scores.** The theme matrix shows agreement and tension in words.
- **No competitor bashing.** Section 9 names what each tool does well first. No comparison table with red crosses against named products.
- **No mascot in the serious sections.** The dinosaur does not appear in 5–10, in the nav beyond a 24px wordmark glyph, or as a watermark.
- **No black-box framing.** Never describe the pipeline as simpler than it is; the trace shows the skip, the reask, and the resume.
- **No social-proof theater.** No logo marquee, no "trusted by N researchers", no testimonials, no institution badges, no funder badges.
- **No vanity metrics band.** The only numbers on the page are per-job (39/40, 187, 41, 312) and corpus sizes.

### 3.2 AnswerThis-specific
- No "Flawless", "Always Accurate", "The only tool that…", "Verified" as a badge.
- No typos. Run a spell-check pass; use American spelling consistently ("analyzes", "deduplicates"); check every specimen string (`Sørensen`, `kalsbeek-2024-c07`, `§`) survives encoding.
- No writing-assistant, paraphraser, detector, or thesis-generator anywhere, including footer links and meta description.
- No compliance badges (PRISMA, Cochrane) without a linked method document. The page does not claim compliance with anything.
- No dark-mode-by-default developer-tool aesthetic. Light paper is the default; dark is a toggle.
- No autoplay video, no embedded product loop.
- No pricing, no "Start for free", no "no credit card required".

### 3.3 From the Round 1 diagnosis (code-level)
- No `javascript:void(0)`, no `onclick="alert(…)"`, no `href="#"` on real CTAs. Every link has a destination or is removed.
- No `localhost` URLs in the shipped file.
- No hover `transform: translateY(…)`, no `box-shadow` above `--shadow-md`, no `shadow-lg` token.
- No uppercase eyebrows or `letter-spacing ≥ .06em` on labels.
- No mono or caption text under 12px.
- No fade-in on eyebrows, headings, leads, or the act break. Reveal only on exhibit panels (contrast cards, dedup specimen, citation composition, verification nodes, trace panel, division cards, chat blocks).
- No boxed mascot: the hero illustration sits on the page, not inside a bordered card with a shadow.
- No decorative additions to the mascot (monocle, radiance lines, seals, ribbons, measurement rulers).
- No fabricated additional research findings. R1 AGY invented three extra receipts with new quotes and scores; that violates the brief's "do not author fictional research findings beyond the specimen text". Interactive receipt swapping is allowed only once real data exists for every swapped citation.
- No per-exhibit "this is a specimen" caveat paragraphs (Codex had five). One global note, per 2.9.
- No extra nav items ("Positioning"). Nav is `The synthesis · The evidence · The method` plus the quiet CTA and the theme toggle.
- No CSS class collisions between layout and content (Fable's `.sub` applied grid rules to the hero subhead).
- No shaded table columns or rows.

### 3.4 Pre-publish grep list

Run against the final HTML (case-insensitive, text nodes and attributes):

```
10x|supercharge|unlock|leverage|seamless|game-changing|revolutionary|magic|effortless|instant
accurate|hallucination|guaranteed|trustworthy|reliable|flawless|always
AI-powered|powered by AI|intelligent|smart
writes your|write your|autocomplete|paraphras|essay|detector
javascript:void|alert\(|localhost|href="#"
translateY|shadow-lg|text-transform:\s*uppercase
PRISMA|Cochrane|trusted by
```

Expected hits: `understood` only inside "does not claim to have understood" (sections 10 and its card); `!` exactly once, in `Hungry for papers since the Cretaceous!`. Everything else in the list should return zero.

---

## 4. Phase C Diagnosis Summary

All four R1 files used the locked copy faithfully and implemented all twelve sections. The differences are in atmosphere, code quality, and discipline.

### 4.1 Fable (`landing-html/fable/index.html`, 877 lines)

**What worked (keep):**
- Closest to the brief's display scale: H1 `clamp(46px,7.2vw,96px)`, act break `clamp(112px,34vh,320px)`, section rhythm `clamp(72px,12vw,176px)`.
- Two-column proof layout with sticky copy column (`position: sticky; top: 110px`) so the explanation stays beside a tall exhibit.
- Sticky pull quote in section 2 with a gold top rule.
- Gold tether from the active citation to the receipt card; gold underline on the entailing clause with a faint gold wash.
- Trace panel structure: badge, title, four Literata metric tiles, grid-based stage rows, sub-rows with tree glyph, right-aligned `resumed from journal`, sidebar-toned log strip.
- The most compact, readable CSS of the four; token block mirrors `shared/tokens.css` exactly.
- `fig. 1 — digestion, schematic` caption under the mascot: a small, correct academic note.
- Green wash on `[n]` pills when hovering a theme row (optional interaction done quietly).

**What failed (fix):**
- `.sub` class collision: the trace sub-row rule (`display:grid; grid-template-columns:28px 160px 1fr; min-width:560px`) also applies to the hero subhead `<p class="sub">`. Rename the trace class to `.stage-sub`.
- Eyebrows uppercase with `.06em` tracking.
- Mascot is a stegosaurus with back plates; the current art direction is a slim baby brontosaurus (see Open Items).
- Second preset pill links to `#close`; first links to `#evidence` (a section, not a review).
- Nav CTA is a bordered button rather than a text action; fine, but keep it quieter (no border, primary text).
- No skip link, no `:focus-visible` styles, no `aria-label` on the scroll regions, no print stylesheet.
- H1/H2 in ink rather than primary green (design-system heading progression says green).

**Harvest:** the whole file as the R2 skeleton, the tether, the trace panel, the sticky columns.

### 4.2 Codex (`landing-html/codex/index.html`, 498 lines)

**What worked (keep):**
- The accessibility layer, complete: skip link; `:focus-visible` outlines (3px primary, offset 5px); `main[tabindex=-1]`; `role="region"` + `aria-label` + `tabindex=0` on horizontally scrolling containers; `<caption>` on the table with `scope` on headers; `<dl>` for audit grid, metrics, and chat; `<time>` in log lines; `<figure>/<figcaption>` for exhibits; `svg role="img"` with `<title>` and `<desc>` on the mascot; `aria-pressed` on the theme toggle; hash navigation that opens parent `<details>` and moves focus; `forced-colors` and `print` media queries; `aria-hidden` on decorative arrows.
- The breathing: `body` line-height 1.75, `.prose p { margin-top: 26px }`, section `clamp(120px,10.5vw,168px)`, a dedicated `.statement` class (`clamp(25px,2.7vw,36px)`, primary green, max 43ch) for the three closing lines, and a `.limit` block set apart by a rule.
- Sentence-case eyebrows at 12px mono. Headings weight 400 in primary green, `text-wrap: balance`.
- Light theme is the default regardless of system preference; the toggle stores an explicit choice. This protects the act break's meaning on first visit.
- Theme toggle is `hidden` until JS runs (no dead button without JS).
- Manuscript pane as a ruled block (top/bottom hairlines, left padding) rather than a card: the most "journal page" treatment of the review excerpt.
- Honest handling of the missing second corpus (dialog explaining it is a placeholder) rather than a dead link.

**What failed (fix):**
- Mono sizes of 10–11px in the trace, audit grid, presets, and captions. Below the 12px floor.
- Underlined links everywhere (`text-decoration` on every `<a>`) reads as a default stylesheet; use underline only on in-prose links.
- Five separate "design specimen / not bundled" caveats. Honest, but they clutter the exhibits. Replace with one global note.
- Header `min-height: 100px` is heavy; 64px.
- Mascot SVG is a filled silhouette with paper fill and a complex single path; it reads as a blob at small sizes.
- CTAs point to `http://localhost:5173/upload`.
- HTML minified onto single lines per section: hard to maintain. R2 should be formatted.
- No reveal animation at all (acceptable, but the brief allows fade-in on exhibits and it helps pacing).

**Harvest:** every accessibility rule above, the `.statement` and `.limit` classes, the light-default theme logic, the manuscript-as-ruled-block treatment, the hash-navigation focus script, the print stylesheet.

### 4.3 AGY (`landing-html/agy/index.html`, 2,961 lines)

**What worked (keep):**
- Chip text colors per chip (`--saurus-chip-1-text: #4C1D95` etc., with dark equivalents): the only R1 that made chip labels legible on their pastel fills. Adopt these six text tokens.
- Notebook ruled pattern implemented as a repeating linear-gradient at 28px, very low contrast (useful reference for the optional hero texture, though see Open Items on the mascot image).
- Interactive receipt swap wiring is clean (data attributes, single card updated). Keep the mechanism for later; do not ship the fabricated data.
- Comments delimit every section clearly.

**What failed (fix):**
- Reads as SaaS: `--shadow-lg`, `translateY(-1px)` on buttons and preset cards, `translateX(2px)` on pills, shaded "The Saurus gives you" column, uppercase eyebrows with `.1em` tracking, gold CTA in the nav with a shadow.
- Mascot boxed in a bordered, shadowed card; decorated with a monocle, gold string, radiance lines, a verification seal, a bookmark ribbon, and a ruler with `00:INPUT / 02:DIGESTION / 04:SYNTHESIS` labels. Violates "scientific-illustration weight, not cartoon" and "no decoration".
- Fabricated three additional receipts (quotes, scores, claim IDs) for the swap interaction.
- `javascript:void(0)` links across the footer; `onclick="alert(…)"` on the primary CTA.
- Extra "Positioning" nav item.
- `resumed from journal` placed as the Aggregation stage's detail text, which misstates what resumed.
- H1 at `clamp(42px,5.8vw,84px)`: under the brief's 72–96px desktop target.
- 2,961 lines for the same content; CSS is verbose and partly inline (`style=""` attributes on ~30 elements).

**Harvest:** chip text tokens; receipt-swap mechanism (dormant until real data); nothing visual.

### 4.4 Kimi (`landing-html/kimi/index.html`, 1,203 lines)

**What worked (keep):**
- Mascot direction: a single-contour, long-necked dinosaur drawn with one continuous 3.5px stroke, a paper stack going in on the left, a bound review on the right, one ground line. Closest to the current brontosaurus art direction and to "scientific illustration".
- The satisfied sign-off dinosaur (closed eye, closed mouth, a paper crumb): the right tone for section 11.
- Dark-mode act break darker than the dark page (`#101213`) so the band still reads as a band.
- Chips in Literata italic on pastel with matching darker borders: the "index card in a catalog" look the brief asks for.
- Section rhythm 150px fixed on desktop is generous; the close at `170px 0 150px`.
- Mono nav links and a bordered mono nav CTA give the header a notebook-index feel.
- `.hero-grid>*, .split>* … { min-width: 0 }` guard prevents grid blowout from long mono strings.

**What failed (fix):**
- Section 2 is single-column with the pull quote below; the brief wants the quote large to the right on desktop.
- Wordmark `The <em>Saurus</em>` splits the name in two colors; the name is one word pair in one color.
- Fade-in applied to eyebrows, headings, and paragraphs: the page flickers in piece by piece.
- Section padding has no clamp; 150px at 1024px is too much, and the mobile breakpoint drops straight to 84px.
- Hero pills link to `#trace`; close CTAs link to `#top`.
- No accessibility work: no skip link, no focus styles, no aria on scroll regions, no `<figure>`.
- Headings at weight 600 are a notch heavier than the brief's register.

**Harvest:** the mascot contour style (as the placeholder), the sign-off dinosaur, the dark-mode band color, the italic-serif chips, the `min-width:0` grid guard.

---

## 5. Consolidated Implementation Spec

### 5.1 Base

Start from **Fable's file**. It has the correct scale and structure and the least CSS to unwind. Apply, in order:

1. Rename `.sub` (trace sub-row) to `.stage-sub`; verify the hero subhead renders as a paragraph.
2. Replace the `<head>` and top-of-body with Codex's: `meta color-scheme`, `meta theme-color`, favicon data-URI, skip link, `<main id="main" tabindex="-1">`, and the inline pre-paint theme script (light default; apply `.dark` only if `localStorage['saurus-theme'] === 'dark'`).
3. Port Codex's global rules: `:focus-visible`, `.sr-only`, `text-wrap: balance` on headings, `@media (forced-colors)`, `@media print`, `.statement`, `.limit`.
4. Set H1/H2 color to `--saurus-primary`; H1/H2 weight 500; eyebrows sentence case, `letter-spacing: .02em`, no `text-transform`.
5. Add AGY's six `--saurus-chip-n-text` tokens (light and dark) and use them on chips.
6. Replace the hero and sign-off mascots with the placeholder spec in 5.4.
7. Restrict `.reveal` to exhibit panels; remove it from copy blocks.
8. Route every link per 5.6. Remove the `href="#docs"` footer stubs that have no destination.
9. Format the HTML: one element per line where practical, 2-space indent, section banner comments.

### 5.2 Section by section

| # | Section | Base | Change |
|---|---|---|---|
| nav | Top navigation | Fable | Wordmark = 24px line-art glyph + "The Saurus" in Literata 600 20px, one color. Links `The synthesis · The evidence · The method` Inter 14px secondary. CTA `Feed it a corpus` as primary-green text, no border. Theme toggle 34px circle, hidden until JS. Sticky, 64px, paper at 88% with 10px blur, hairline bottom. Anchor links hidden below 820px. |
| 1 | Hero | Fable layout, Codex semantics | 7fr/5fr grid, copy left, mascot right; stacked below 900px with copy first. `<figure>` + `<figcaption class="caption">fig. 1 — digestion, schematic</figcaption>`. No card, no border around the illustration. Pills per 2.1. Optional faint ruled pattern behind the illustration is **removed** (see Open Items: the generated image has no ruled lines). |
| 2 | The Problem | Fable | Surface background, hairline top and bottom. 7fr/5fr; sticky pull quote right with 1px gold top rule; three failure modes as H3 24px + Inter 17px, separated by hairlines, no icons. Stacks below 900px, quote after the failures. |
| 3 | Synthesis vs Summary | Fable | Contrast cards per 2.6. Loop: four columns, 1px green→gold hairline across the top, 32px line glyphs (sheet with tiny dinosaur mark, overlapping circles, open book, magnifier), H3 24px, Inter 15.5px. Mono caption, then `.statement`. Two columns below 900px, one below 560px. |
| 4 | Act Break | Fable copy split, Kimi dark variant | Per 1.4. `id="evidence"` stays on this band so the nav link lands the reader on the turn. No `.reveal`. |
| 5 | Dedup | Fable | 5fr/7fr with sticky copy. Specimen: label, three paper rows (surface, hairline, `[n]` mono muted, chip Literata italic 14px on chip color with chip text color and matching border), vertical 2px green connector with the pill label `Theme Dedup · embedding match → pairwise confirm`, label, merged card (3px green left border, `Theme 03` badge, Literata 30px title, meta, mono alias line). Reveal on the specimen only. |
| 6 | Citation (centerpiece) | Fable composition, Codex manuscript treatment | Intro grid: H2 left, lead right, aligned to baseline. Composition 3fr/2fr: manuscript pane as a ruled block on surface (hairline top/bottom, padding clamp 28–56px, review text `--review`), receipt card per 2.2 with tether. Caption below in mono. Optional `<details>` with the three reference entries (Codex) may stay; it is the only disclosure on the page. |
| 7 | Grounding | Fable | Surface background with hairlines. Nodes per 2.5. Trace line with spinner. `.statement`, then `.limit`. Nothing after. |
| 8 | Trace | Fable | 5fr/7fr with sticky copy. Panel per 2.3. Move `resumed from journal` out of any stage row. Log `<pre>` with `<time>` elements. Scroll region has `role="region"`, `aria-label`, `tabindex="0"`. |
| 9 | Where it sits | Fable | Table per 2.8 with `<caption>` (visually hidden or mono muted) and `scope` attributes. No eyebrow. |
| 10 | Author | Fable | Two cards per 2.7; export control; assistant block 4fr/7fr with two message blocks (you: right margin 12%; assistant: left margin 12%, 2px green left border), `<dl>` semantics, citations styled as in 6. `.statement` closes. |
| 11 | Close | Fable | Centered. 1px green→gold rule (min 520px, 60%) above. H2 at `--h1` scale. Sub Literata clamp 20–28px secondary. CTA row. Shelf with two preset cards (min-width 300px, `Inspect the review →` in Inter 14px primary). Sign-off: Kimi's satisfied dinosaur at ~96×64, Literata italic 16px, right-aligned on desktop, centered on mobile. |
| 12 | Footer | Fable | Sidebar background, hairline top. 5fr + 3×2fr. Wordmark, italic tagline, boilerplate 13.5px muted max 52ch. Three link columns with mono 12px heads (sentence case). Bottom line. Only real destinations. |

### 5.3 CSS framework

```css
:root {
  /* tokens: copy shared/tokens.css light block verbatim; html.dark copies the dark block */
  --font-heading: 'Literata', Georgia, serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'Fira Code', 'SF Mono', Consolas, monospace;
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;
  --sec-y: clamp(112px, 12vw, 192px);
  --gutter: clamp(20px, 4vw, 56px);
  --wrap: 1360px;
  color-scheme: light;
}
html.dark { color-scheme: dark; /* dark tokens */ }

body { margin: 0; background: var(--saurus-paper); color: var(--saurus-ink);
       font: 400 18px/1.7 var(--font-body); -webkit-font-smoothing: antialiased; overflow-x: hidden; }
h1, h2, h3 { font-family: var(--font-heading); font-weight: 500; margin: 0; text-wrap: balance; }
h1, h2 { color: var(--saurus-primary); }
section { padding-block: var(--sec-y); }
.wrap { max-width: var(--wrap); margin-inline: auto; padding-inline: var(--gutter); }
.prose { max-width: 64ch; }
.prose p + p { margin-top: 24px; }
.eyebrow { font: 400 13px/1.6 var(--font-mono); color: var(--saurus-ink-secondary); letter-spacing: .02em; margin-bottom: 24px; display: block; }
.caption { font: 400 13px/1.6 var(--font-mono); color: var(--saurus-ink-muted); }
.statement { font: 500 clamp(22px, 2.4vw, 30px)/1.4 var(--font-heading); color: var(--saurus-ink); max-width: 36ch; margin-top: 56px; }
.limit { margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--color-border); max-width: 62ch; font-size: 16.5px; color: var(--saurus-ink-secondary); }
.btn-gold { background: var(--saurus-accent); color: #1C1C1E; font: 500 16px var(--font-body); padding: 14px 26px; border-radius: var(--radius-md); }
.btn-gold:hover { background: #E0BC48; }   /* color change only; no transform, no shadow change */

/* grids */
.two-col { display: grid; grid-template-columns: minmax(0,5fr) minmax(0,7fr); gap: clamp(40px, 6vw, 96px); align-items: start; }
.two-col > * { min-width: 0; }
.sticky-copy { position: sticky; top: 110px; }

/* breakpoints */
@media (max-width: 960px) { .two-col { grid-template-columns: 1fr; } .sticky-copy { position: static; } }
@media (max-width: 900px) { /* hero, problem, contrast, loop → 2 cols, footer → 2 cols */ }
@media (max-width: 760px) { section { padding-block: 80px; } .act-break { padding-block: 112px; } }
@media (max-width: 560px) { /* loop → 1 col, metrics → 2×2, footer → 1 col, pills → column */ }
@media (max-width: 380px) { :root { --gutter: 20px; } .audit { grid-template-columns: 1fr; } }

/* motion */
.reveal { opacity: 0; transform: translateY(10px); transition: opacity .5s ease, transform .5s ease; }
.reveal.in { opacity: 1; transform: none; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .reveal { opacity: 1; transform: none; transition: none; }
  .spin { animation: none; }
}
```

Color usage rules:
- `--saurus-error` is defined but never used on this page.
- Chip colors appear only in section 5 (and optionally section 3's theme rows). Never on badges, status, or buttons.
- Gold appears exactly at: the two primary CTAs, the pull-quote rule, the loop hairline (as gradient end), the receipt border and underline, the tether, the citation active state, the close rule. Nowhere else.

### 5.4 Mascot placeholders

Until the generated image arrives, ship two inline SVGs based on Kimi's contour style, redrawn to the current art direction (see `git log` on `docs/prompts`: baby brontosaurus proportions, slim long neck, 1:1 square, single baseline, no ruled lines, no chevrons, the review book floating with distance from the tail).

- **Hero:** `viewBox="0 0 560 560"` (square), `max-width: 520px`, `stroke: var(--saurus-primary)`, `stroke-width: 3`, round caps and joins, single continuous body contour, open mouth facing left, three PDF sheets in `--saurus-ink-secondary` 1.6px entering from the left, a bound review (green cover, paper pages) floating to the right of the tail with clear space, one dotted baseline in `--saurus-ink-muted`. `role="img"`, `<title>Papers in. A review out.</title>`, `<desc>` describing the scene. No fills except paper on the sheets and green on the cover. No eye ring, no plates, no teeth, no motion lines.
- **Sign-off:** `viewBox="0 0 140 92"`, ~96×64 rendered, same stroke style at 1.8px, closed mouth, closed contented eye, one paper crumb. `aria-hidden="true"`.
- **Wordmark glyph and "Feed" step mark:** 24–32px head-and-neck profile only, `stroke-width: 2.2`, `currentColor`.

When the image arrives: swap the hero SVG for `<img src="…" width="1024" height="1024" alt="A dinosaur eating a folder of PDFs; a bound review floats beside its tail">` inside the same `<figure>`, `max-width: 520px`, `height: auto`. Keep the sign-off as SVG unless a small version is supplied. Image ≤ 200KB WebP with PNG fallback via `<picture>`.

### 5.5 Interactive elements and JS

One inline `<script>` at the end of `<body>`, no dependencies, ~60 lines:

1. **Theme.** Pre-paint snippet in `<head>` reads `localStorage['saurus-theme']` and adds `.dark` only when it equals `'dark'`. Toggle button: flips `.dark`, writes the choice, updates `aria-pressed` and `meta[name=theme-color]`. Light is the default regardless of system preference (rationale: the act break only works if the page opens light).
2. **Reveal.** `IntersectionObserver` on `.reveal` with `rootMargin: '0px 0px -8% 0px'`, `threshold: .08`, unobserve after first intersection. If `prefers-reduced-motion` or no IO support: add `.in` to all immediately.
3. **Hash navigation.** Codex's handler: intercept same-page `a[href^="#"]`, `pushState`, open ancestor `<details>`, set `tabindex=-1` if needed, `focus({preventScroll:true})`, `scrollIntoView({block:'start'})`. `scroll-padding-top: 80px` on `html` to clear the sticky nav.
4. **Optional (dormant):** receipt swap on citation click, wired via `data-cite` attributes, enabled only when real receipts exist for every citation in the excerpt. Ship the excerpt with the `[11]` receipt open and no click handlers until then.

Nothing else. No smooth-scroll polyfill, no analytics, no font loader script.

### 5.6 Link routing

| Element | Destination |
|---|---|
| Nav wordmark | `#top` |
| Nav `The synthesis` | `#synthesis` (section 3) |
| Nav `The evidence` | `#evidence` (section 4, the act break) |
| Nav `The method` | `#method` (section 7) |
| Nav / hero / close `Feed it a corpus` | `{APP_URL}/upload` (Open Items); until then `#feed`, which is the id of section 11 |
| Hero `Inspect a sample synthesis →` | `{SAMPLE_REVIEW_URL}` for the circadian corpus; until then `#citation` (section 6) |
| Hero pill 1 / close card 1 | same as above |
| Hero pill 2 / close card 2 | `{SAMPLE_REVIEW_URL_2}` or removed |
| Close `Read the docs →` | `{DOCS_URL}` (GitHub README anchor is acceptable) |
| Footer Architecture column | GitHub `docs/architecture.md` anchors (Codex's targets are a reasonable starting set; verify each) |
| Footer Integration column | README anchors; remove any entry without one |
| Footer Exports column | README anchors; list only shipping formats |
| Footer `GitHub · Documentation · License` | repo root, README, LICENSE |

Section ids: `top` (hero), `problem`, `synthesis`, `evidence` (act break), `dedup`, `citation`, `method`, `trace`, `positioning`, `author`, `feed` (close), `footer`.

### 5.7 Accessibility requirements

From Codex, in full:

- `<html lang="en">`, `<meta name="color-scheme" content="light dark">`, `<meta name="theme-color">` updated by the toggle.
- Skip link as the first focusable element, visible on focus.
- Landmarks: `<header>`, `<nav aria-label="Page navigation">`, `<main>`, `<footer>`, one `<section aria-labelledby>` per numbered section with a real heading id.
- `:focus-visible { outline: 3px solid var(--saurus-primary); outline-offset: 5px; }` on everything; `[tabindex="-1"]:focus` styled the same with offset 7px.
- Touch targets ≥ 44×44px: theme toggle, nav links (padding-block 12px), preset pills, `<summary>`.
- Horizontally scrolling containers (trace stage list, event log, positioning table): `role="region"`, `aria-label` explaining the scroll, `tabindex="0"`.
- Table: `<caption>`, `th scope="col"` / `scope="row"`.
- Audit grid, metrics, chat: `<dl>`/`<dt>`/`<dd>`. Log timestamps: `<time>`.
- Exhibits: `<figure>` with `<figcaption>`. Hero mascot: `svg role="img"` + `<title>` + `<desc>`; decorative SVGs `aria-hidden="true"`.
- Citation pills that are links carry `aria-label="Reference 11, page 12, paragraph 3"`.
- Status glyphs in the trace carry `aria-label="Complete"` / `"Running"` / `"Pending"`; the spinner is `aria-hidden` with the label on its wrapper.
- Contrast: muted ink (`#9CA3AF`) only at ≥ 13px and only for captions, timestamps, and metadata. Anything the reader must read is secondary ink or darker. Check every mono line against its background at 4.5:1; Codex's `--muted: #62686E` alias is the fallback when `#9CA3AF` fails.
- `@media (forced-colors: active)` maps tokens to system colors and restores borders on chips, pills, receipt, trace panel; act break gets `Canvas` background with `CanvasText` borders.
- `@media print`: hide nav, CTAs, skip link; collapse section padding; act break prints as light with ink text; `break-inside: avoid` on receipt, trace panel, division cards; body 12pt.
- `prefers-reduced-motion`: all transitions and the spinner off; `scroll-behavior: auto`.
- Every image/SVG has `width`/`height` or a fixed aspect to prevent layout shift.

### 5.8 Performance budget

- One HTML file. CSS and JS inline. SVGs inline. No build step.
- Total HTML ≤ 120KB uncompressed before the mascot image; ≤ 140KB after (image is a separate request).
- External requests: exactly one stylesheet from `fonts.googleapis.com` (with `preconnect` to both Google font hosts) plus the font files it pulls, plus the mascot image. Nothing else. No CDN scripts, no icon fonts, no analytics.
- Font request limited to the weights in 2.4; `display=swap`; fallback stacks that do not reflow badly (Georgia for Literata, system sans for Inter).
- Largest Contentful Paint element is the H1 (text), not the image. The hero image gets `fetchpriority="high"`; the sign-off image, if any, gets `loading="lazy"`.
- No layout shift: `min-height` on the hero, explicit dimensions on media, `text-wrap: balance` limited to headings.
- Works with JS disabled: light theme, all content visible (no `.reveal` opacity 0 without JS: add `.reveal` class via JS, or set `.no-js .reveal { opacity: 1 }` with `<html class="no-js">` cleared by the pre-paint script).

### 5.9 Definition of done

- [ ] Copy matches `landing-brief.md` sections 1–12 verbatim (diff the text nodes).
- [ ] Grep list in 3.4 returns only the expected hits; exactly one `!`.
- [ ] Mascot absent from sections 5–10.
- [ ] Renders correctly at 1440, 1024, 768, 390, 320px wide with no horizontal page scroll.
- [ ] Light and dark themes both pass the contrast check; the act break is distinguishable from the page in both.
- [ ] Keyboard-only walk: skip link → nav → every link and pill → table region → trace region → footer, with visible focus at each stop.
- [ ] `prefers-reduced-motion` shows the page with no motion and the spinner static.
- [ ] Print preview produces a readable document under 8 pages.
- [ ] No link resolves to `#`, `javascript:`, or `localhost`.
- [ ] File formatted, ≤ 1,100 lines, with section banner comments.

---

## 6. Open Items

Decide or supply before generating the final HTML. Each has a default so the build is not blocked.

1. **Mascot image.** Being generated externally (baby brontosaurus, 1:1, single baseline, no ruled lines, review book floating apart from the tail). **Default:** the SVG placeholder in 5.4, drawn to the same art direction, so the swap is a one-line change. Because the image will have no ruled lines, the optional notebook pattern behind the hero is dropped now so the placeholder and final composition match.

2. **Real pipeline data vs sample data.** Sections 5, 6, 7, 8 and the preset metrics (`14 themes`, `312 traced claims`, `39/40`, `187 → 41`, `0.94`, `0.41 < 0.60`, `kalsbeek-2024-c07`) are specimens from the brief. **Default:** ship the specimens with the single global note from 2.9, and keep every value in one place (a small JSON-like block in the script, or clearly grouped in the HTML) so replacement from a real `jobs/<id>/` YAML and `events.ndjson` is mechanical. The NLI threshold `0.60` must be checked against the pipeline config before publishing; if it differs, update sections 7 and 8 together.

3. **Second benchmark corpus.** "Neural Organoid Morphogenesis" is a placeholder. **Default:** build with two pills/cards, and if no second job exists at publish time, remove the second pill and second card rather than linking a placeholder. Do not use a dialog or a disclosure to explain its absence (Codex's approach was honest but adds UI for something that should simply not be there).

4. **Deployment URLs.** Needed: `APP_URL` (the upload entry the gold CTA opens), `SAMPLE_REVIEW_URL` (finished circadian review), `DOCS_URL`, and confirmed GitHub anchors for the footer. **Default:** in-page anchors per 5.6 with the placeholders left as clearly named `data-href` attributes so a single find-and-replace finishes routing.

5. **Export formats.** Confirm which of Markdown, PDF, BibTeX, YAML/NDJSON ship. **Default:** `Export · Markdown / PDF` on the control and Markdown, PDF, YAML/NDJSON in the footer; add BibTeX only when it exists.

6. **Dark mode policy.** Recommended and defaulted: light on first visit regardless of system preference; toggle persists. Confirm this is acceptable; if the team prefers following `prefers-color-scheme`, keep the toggle and accept that some readers meet the act break on an already-dark page.

7. **Receipt interaction.** Recommended: static in R2. Enable citation-click swapping only when real receipts exist for `[4](p.7,§2)`, `[23](p.4,§1)`, and `[23](p.5,§2)` from the same job as `[11]`.

8. **Meta and social.** `<title>The Saurus — Feed The Saurus your papers.</title>`; description from the hero sub. Open Graph image is not yet available; use the mascot image once it exists. No third-party share scripts.
