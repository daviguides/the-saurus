# Landing HTML Diagnosis — Phase C round vs benchmarking

_Four candidates (Fable, Codex, AGY, Kimi) evaluated at 1440px against `landing-brief.md`, `competitor-analysis.md`, and `answerthis-analysis.md`. Full-page screenshots in `/private/tmp/claude-502/landing-screenshots/{fable,codex,agy,kimi}.png`._

## Mechanical audit (all four)

| Check | Fable | Codex | AGY | Kimi |
|---|---|---|---|---|
| File size | 62 KB | 61 KB | 108 KB | 61 KB |
| Full-page height @1440 | 16 220 px | 15 097 px | 13 977 px | 14 757 px |
| Full-page width @1440 | **1880 px (horizontal overflow bug)** | 1440 | 1440 | 1440 |
| Visible-text `!` count | 1 | 1 | 1 | 1 |
| Banned words (10x/unlock/supercharge/accurate/…) | 0 | 0 | 0 | 0 |
| Brief sections present (of 12) | 12 | 12 | 12 | 12 |
| Copy verbatim from brief | yes | yes | yes | yes |
| Dark act break | yes | yes | yes | yes |
| Dark-mode toggle | yes | yes | yes | yes |
| `prefers-reduced-motion` handled | yes | yes (plus forced-colors + print) | partial (spinner only) | yes |
| Motion | fade-in on scroll | none (static) | none | fade-in on scroll |

All four followed the brief's copy to the letter. The differentiation is entirely in layout, atmosphere, typographic decisions, and correctness bugs.

---

## Fable

### Visual analysis
- **Feels like:** an editorial magazine page, closest to "narrative with evidence." Very large ink-black Literata H1 (96px), generous voids (section padding up to 176px, act break 34vh).
- **App-in-a-scroll?** No. Evidence is cropped and captioned (`fig. 1 — digestion, schematic`, `Recorded sample run`).
- **Breathing:** best of the four; the close section has ~200px of empty paper before the H2 and a gold→green hairline.
- **Act break:** present, tallest of the four; the second sentence is set in `#5BAB8A` green for emphasis. Effective.
- **Typography:** H1 impact is the strongest. Body 18px Inter, 66ch. Mono eyebrows uppercase with tracking.
- **Atmosphere:** academic warmth. Ink-black headings (not green) read as print; green is reserved for the pull quote, citations, and act-break emphasis.
- **Bugs (blocking):**
  1. **Hero and close subtitles render one word per line.** `.hero .sub` and `.close .sub` inherit the trace rule `.sub{display:grid;grid-template-columns:28px 160px 1fr;min-width:560px}` (line 250). The anonymous text item lands in the 28px column. This ruins the first screen.
  2. **Horizontal overflow:** document scrollWidth is 1880px at a 1440 viewport (`body{overflow-x:hidden}` masks the scrollbar but the full-page capture shows it). Likely `.mascot-wrap:before{inset:-6% -4%}` or the `.sub{min-width:560px}` leak.
  3. Hero mascot is a small, awkward stegosaurus-ish loop with a legible "Review" book; smallest and least "scientific-illustration" of the four, though the brief's papers-in/review-out story is present.

### Content completeness
- 12/12 sections, verbatim copy. Receipt card, pipeline trace (with skipped paper, reask, resume, NDJSON log), dedup specimen, stack-vs-matrix: all present.
- Nav: `The synthesis · The evidence · The method` + quiet "Feed it a corpus" + theme toggle, per brief.
- Tiny dinosaur mark at "Feed" step: present (per brief).

### Benchmark techniques
| Technique | Applied |
|---|---|
| Sample corpus shelf | yes, hero + close, mono metrics |
| Receipt card with NLI score | yes, gold left border, tether line to the active citation, underlined entailing span |
| Serif + mono + sans pairing | yes, cleanest execution (Literata manuscript at 24px, Fira addresses at .62em) |
| Honest trace | yes: skipped paper, reask 0.41 < 0.60, `resumed from journal`, NDJSON strip |
| Claim confidence audit | yes (2×2 audit grid) |
| Academic trust signals | yes, no logos, no counters, limit statement set apart |

### Anti-pattern check
- No SaaS language, no accuracy assertions, no "AI magic." Dinosaur absent from 5–10. Mascot sign-off is the only `!`.

### Summary
Fable has the best editorial atmosphere and the strongest display typography, the best receipt/citation composition (tether line, manuscript surface), and the tightest mono/serif discipline. It is also the only one with page-breaking bugs (subtitle grid collision, horizontal overflow). Keep: section rhythm, H1 scale in ink, act-break green emphasis, citation composition, trace panel with `resumed from journal` right-aligned, close section void. Fix or discard: the `.sub` class collision and the overflow.

---

## Codex

### Visual analysis
- **Feels like:** a finished, publishable product page. Headings in primary green Literata at 88/56px, body 18px/1.75, `min-height:100svh` hero.
- **App-in-a-scroll?** No. Every specimen is a `<figure>` with a `<figcaption>`; the trace panel caption reads "The skipped paper, the reask, and the resume remain visible."
- **Breathing:** very good; section padding 120–168px, act break 32vh. The hero shelf is separated by a hairline rule and spans both columns.
- **Act break:** present, clean, no decoration. Effective.
- **Typography:** balanced. `text-wrap:balance` on headings; the pull quote is vertically centered against the failure list (sticky-free, elegant). Positioning table has `<caption>` and a `Your tools` column header.
- **Atmosphere:** academic warmth; the only one whose hero mascot actually reads as scientific line-art (long-neck dinosaur, PDFs with "PDF" tags, bound "Review" volume, gold ribbon, ruled-notebook pattern behind). Caption: "A curated corpus. A draft with receipts."
- **Flaws:** headings all in green become monotone over 15k px (Fable's ink headings with green accents have more contrast). Mono captions at 10–12px are at the legibility floor. Hero H1 slightly smaller than brief maximum.

### Content completeness
- 12/12, verbatim. Includes extras the others lack: honest **specimen disclaimers** ("Design specimens from the landing brief. Recorded outputs and the second review are not bundled." / "Source quote, claim ID, and NLI 0.94 are supplied design specimens, not measured results."), a `<details>` reference list with anchor targets for `[4] [11] [23]`, a `<dialog>` explaining the placeholder second corpus, real GitHub URLs in footer, skip link, `forced-colors` and `@media print` support, `aria-labelledby` on every section.
- The BibTeX export entry is omitted from the footer (matches Open item 8: only ship what exists).
- Mascot at "Feed" step: yes (tiny glyph).

### Benchmark techniques
| Technique | Applied |
|---|---|
| Sample corpus shelf | yes, with ↗ arrows, plus placeholder honesty |
| Receipt card with NLI score | yes; citations are real `<a>` links to receipt/reference anchors |
| Serif + mono + sans pairing | yes |
| Honest trace | yes, plus explicit caption naming the three failure events |
| Claim confidence audit | yes |
| Academic trust signals | strongest: the specimen disclaimers are exactly the "say what is checked" posture the AnswerThis teardown demands |

### Anti-pattern check
- Clean. Nothing to flag. The disclaimers slightly over-communicate for a public page but are correct for Phase C given Open items 1–5.

### Summary
Codex is the most production-ready and the most honest: accessible, semantic, real links, disclaimers where data is fabricated, and a hero illustration that actually satisfies the brief. Its weakness is uniformity: green-on-everything headings and small mono captions flatten the drama Fable achieves. Keep: hero mascot (as the base), figure/figcaption discipline, specimen disclaimers, `<details>` reference list, footer links, a11y/print scaffolding, pull-quote vertical centering.

---

## AGY

### Visual analysis
- **Feels like:** a polished SaaS template wearing the design tokens. Everything is in a card: the hero mascot sits inside a bordered, shadowed frame; the verification diagram is wrapped in a card; the centerpiece is a card containing two more cards; the positioning table has header shading and a tinted "Saurus" column; the mascot sign-off is a pill.
- **App-in-a-scroll?** Partially. The nested-card centerpiece and `shadow-lg` wrapper read as UI chrome, contrary to brief rule "unrelated chrome removed."
- **Breathing:** the shortest page (13 977 px) with section padding 96–160px; section-surface bands alternate every section, so the "void" is replaced by stripes.
- **Act break:** present, but it has a 1px `#353838` top/bottom border and is the shortest (32vh max 220px). Adequate.
- **Typography:** green H1/H2 at 84/54px; `display-h2` wraps to one line at 1440 for most sections, which makes the page feel wide and shallow. Uppercase mono eyebrows with 0.1em tracking, uppercase audit labels: the mono is doing "dashboard" work.
- **Atmosphere:** SaaS-leaning. Green pill CTA in the nav (brief asks for a quiet action), `transform:translateY(-1px)` hover lifts, gradient-ish shadows, mascot with a **gold monocle** and "00:INPUT / 02:DIGESTION / 04:SYNTHESIS" axis labels under the illustration: a cartoon, not scientific illustration.
- **Bugs:** hero CTA "Feed it a corpus" in the close section fires a `javascript:alert(...)`; footer Integration/Exports links are `javascript:void(0)`; the trace's pending Aggregation row says "resumed from journal" in its detail column (the resume note belongs to the panel, not to a stage). Reduced-motion only covers the spinner; hover transforms remain.

### Content completeness
- 12/12, verbatim. Adds a **fourth nav item "Positioning"** (brief specifies three). Adds a `receiptsData` JS map with three additional fabricated receipts (Roenneberg 0.91, Vetter 0.89/0.93) so clicking any citation swaps the card; this is the brief's "optional interaction" done fully, but it authored fictional findings beyond the brief's specimen text (brief hard constraint: "Do not author fictional research findings beyond the specimen text given").
- Export badge lists BibTeX.

### Benchmark techniques
| Technique | Applied |
|---|---|
| Sample corpus shelf | yes, as stacked full-width rows |
| Receipt card with NLI score | yes, interactive swap (best interaction), but boxed inside two more cards |
| Serif + mono + sans pairing | yes, but mono is uppercase-heavy and cold |
| Honest trace | yes; active row highlighted with a green tint (fine) |
| Claim confidence audit | yes |
| Academic trust signals | weakest: tinted table column, nav pill CTA, monocle mascot |

### Anti-pattern check
- No banned words. But: mascot appears in nav brand mark (acceptable) and the monocle/axis-label illustration is "AI mascot" framing. Chrome everywhere violates "the landing is not the app in a scroll." Authored extra fictional receipts.

### Summary
AGY is the most feature-complete interactively (citation swap, richest dark tokens with chip text colors) and has good responsive breakpoints, but it is the least editorial: cards inside cards, stripes instead of void, a cartoon mascot, a dead `alert()` CTA. Keep: the citation-click → receipt swap mechanic (with brief-only data), the chip text-color tokens for dark mode, the four-tile metrics header. Discard: nested card wrappers, nav pill CTA, monocle, axis labels, table tinting, 4th nav item.

---

## Kimi

### Visual analysis
- **Feels like:** a solid, restrained page that sits between Fable and Codex. Green Literata headings at 88px, `section{padding:150px}`, act break 34vh.
- **App-in-a-scroll?** No.
- **Breathing:** good. The problem section is single-column with the pull quote *below* the failure list (brief asked for right-on-desktop, below-on-mobile), which loses the sticky counterpoint.
- **Act break:** present, dark, the darkest variant in dark mode (`#101213`). Effective.
- **Typography:** clean; nav links in Fira Code mono (a nice touch), wordmark with green "Saurus." Chips are set in *italic Literata* which is the most "library index card" reading of the chips across the four. Manuscript excerpt at 23px with generous 48/52px padding.
- **Atmosphere:** academic. Mostly warm. The hero mascot is the problem: a single-contour long, low quadruped that reads as a dog or anteater, mouth barely open, papers on the ground; not a dinosaur, not "papers in / review out" legibly. The sign-off mascot is likewise ambiguous.
- **Flaws:** trace panel event log lines are `white-space:pre` and clip on the right (`chronobiological misalig…`, `0 re-execute…`) at 1440 in the 1.2fr column; `resumed from journal` is a separate `<p>` outside `.trace-stages`, fine. All in-page links go to `#top` or `#trace`; the preset pills point at `#trace` rather than the evidence section. Close section is left-aligned (brief implied centered/"mostly whitespace"; left is acceptable but the gold rule is only 120px).

### Content completeness
- 12/12, verbatim. Tiny dinosaur mark at "Feed": yes (a 3-point blob; hard to read). Export note present. Footer includes BibTeX.

### Benchmark techniques
| Technique | Applied |
|---|---|
| Sample corpus shelf | yes |
| Receipt card with NLI score | yes; underlines the *second* clause of the quote (Fable/Codex/AGY underline the first, the actual entailing span) |
| Serif + mono + sans pairing | yes; mono nav is a distinctive extra |
| Honest trace | yes, but log clipped |
| Claim confidence audit | yes |
| Academic trust signals | good; hairline table, italic verdicts |

### Anti-pattern check
- Clean on language. Mascot not in serious sections. Mascot legibility fails the brief's "scientific-illustration weight" requirement.

### Summary
Kimi is competent and quiet with a few distinctive small decisions (mono nav, italic-serif chips, horizontal arrow connector in the dedup specimen, event-log `.ev` green keys). It lacks a single standout moment and its mascot is off-brief. Keep: italic Literata chips, mono nav links, `The <em>Saurus</em>` wordmark treatment, the green-keyed event log. Fix: log clipping, pull-quote placement, receipt underline span, mascot.

---

## Cross-cutting observations

1. **Copy convergence is total.** Because the brief supplied every sentence, no landing differentiates on words. Phase E should therefore harvest *layout and atmosphere*, not copy.
2. **Green headings vs ink headings.** Codex/AGY/Kimi set every heading in primary green; Fable sets headings in ink and uses green only for the pull quote, citation numbers, and the act-break emphasis. Fable's approach gives green more meaning and better matches the "research volume" aesthetic in the benchmarking's Differentiation Matrix.
3. **Mascot quality gap.** Only Codex's dinosaur satisfies "papers in, review out, scientific-illustration weight." AGY's is a cartoon with a monocle; Kimi's is not recognizably a dinosaur; Fable's is small and rough.
4. **Honesty about specimen data.** Only Codex labels the receipt/trace/preset values as design specimens. Given brief Open items 1–5 (replace with real job output), this is the correct Phase C posture and should carry into Phase E until real data lands.
5. **Chrome discipline.** Fable and Codex keep evidence on paper with a single hairline; AGY boxes everything; Kimi is in between.
6. **Correctness.** Fable ships broken (subtitle grid collision + overflow); AGY ships an `alert()` CTA and void links; Kimi ships clipped logs; Codex ships clean.

## Final harvest table

| Aspect | Best landing | Why |
|---|---|---|
| Hero mascot illustration | **Codex** | Only one that reads as a dinosaur eating PDFs with a bound Review coming out, at line-art weight, with notebook rule behind and a caption |
| Hero typography / H1 impact | **Fable** | 96px ink Literata, tightest tracking; green reserved for meaning (after fixing the `.sub` bug) |
| Editorial breathing / void | **Fable** | Largest section rhythm, tallest act break, close section with true whitespace |
| Act break | **Fable** | Green emphasis on the second sentence, 34vh, no borders |
| Problem section layout | **Codex** | Pull quote vertically centered beside the failure list; failure rules only |
| Stack vs Matrix cards | **Kimi / Codex** (tie) | Mono paper labels with green citation numbers; Codex's staggered summary rows tell the "silo" story visually |
| Four-step loop | **Codex** | Glyph + title inline, hairline gradient rule, least card-like |
| Dedup specimen | **Fable** | Vertical stroke with pill label at the midpoint, merged card with left green border; Kimi's italic-serif chips are the best chip treatment to graft in |
| Citation centerpiece | **Fable** | Manuscript surface, gold tether from the active citation to the receipt, underline on the actual entailing span |
| Receipt interaction | **AGY** | Click-to-swap receipt (restrict data to the brief's single specimen) |
| Verification diagram | **Fable / Codex** | Hairline circles on a rule, no card wrapper; Fable's loop-back arrow SVG is the clearest |
| Pipeline trace panel | **Fable** | Grid-aligned stage rows, `resumed from journal` right-aligned in the panel, NDJSON strip with green keys; Codex's caption naming the three failure events should be added |
| Positioning table | **Codex** | `<caption>`, `Your tools` header, `scope` attributes, no shading |
| Author section + assistant | **Fable** | You/Assistant blocks offset left/right, assistant with green left border, export chip |
| Close section | **Fable** (after fix) | Display-scale H2, gradient hairline, quiet presets, mascot at the edge |
| Footer | **Codex** | Real GitHub URLs, BibTeX omitted until it ships, "Back to top" |
| Accessibility / semantics | **Codex** | Skip link, `aria-labelledby`, `<figure>`, `<details>`, focus styles, forced-colors, print |
| Dark-mode token set | **AGY** | Chip text colors per chip, heading progression tokens |
| Specimen honesty | **Codex** | Explicit "design specimen, not measured" notes matching Open items 1–5 |
| Overall Phase E base | **Codex structure + Fable atmosphere** | Codex's markup and honesty as the skeleton; Fable's spacing, ink headings, act-break emphasis, and evidence compositions layered on; AGY's receipt swap and Kimi's chips grafted in |

## Phase E consolidation checklist

1. Start from Codex's DOM (semantics, links, disclaimers, mascot).
2. Port Fable's spacing scale (`--sec-y:clamp(72px,12vw,176px)`, act break `clamp(112px,34vh,320px)`), ink headings, and green act-break emphasis.
3. Replace Codex's receipt/manuscript composition with Fable's (tether line, manuscript surface), keep Codex's anchor links inside it, add AGY's click-to-swap limited to the brief's one specimen.
4. Use Kimi's italic Literata chips in the dedup specimen and its mono nav links.
5. Keep Codex's problem-section pull-quote placement and positioning table.
6. Use Fable's trace panel layout with Codex's failure-events caption.
7. Do not carry over: AGY's nested cards, nav pill CTA, monocle mascot, 4th nav item, `alert()` CTA; Fable's `.sub` collision and overflow; Kimi's mascot and clipped log.
