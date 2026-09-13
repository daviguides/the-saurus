# The Saurus — Landing Page Brief (Canonical)

_Consolidated from the Fable, AGY, and Codex briefs per the Phase 3 harvest analysis. This is the single input for Phase 5 (HTML generation). Source of truth above this file: `positioning.md`, `vision.md`, `design-system.md`. When this brief contradicts positioning, positioning wins._

---

## 0. Governing rules

**Governing line:** A chatbot gives you an answer. The Saurus gives you the receipts.

**Governing rule:** The landing is not the app in a scroll. App elements appear only as *evidence*: cropped, enlarged, framed by a sentence that tells the reader what they are looking at and why it matters. Mood before information. Editorial breathing between blocks.

**Structure:** Two acts plus a close.
- Act 1 (sections 1–3) answers "what is this" in under one screen of reading.
- Act break (section 4) is the only dark moment on the page.
- Act 2 (sections 5–10) answers "why should I, of all people, believe it" with four demonstrations, then positioning and conviction.
- Close (sections 11–12) returns to the tagline and asks once.

Rough vertical budget: Act 1 ≈ 30% of scroll, Act 2 ≈ 60%, close ≈ 10%.

**Hard constraints:**
- Exactly one exclamation mark on the entire page: the mascot sign-off in section 11.
- The mascot appears in sections 1, 3 (tiny mark at "Feed" only), and 11. It is absent from 5, 6, 7, 8, 9, 10.
- One coherent sample corpus throughout: the circadian / shift-work corpus (40 papers). Every demo element uses it. Label recordings "Recorded sample run". Do not author fictional research findings beyond the specimen text given in this brief; before publishing, replace specimen data with real output from an actual job (see Open items).
- No "AI-powered," "magic," "revolutionary," "effortless," "instant," "understand" (as in "AI that understands"), "intelligent," "smart," "unlock," "supercharge," "10x," "game-changing," "leverage."
- No bare accuracy claims. Say what is checked and how.
- No competitor bashing. Name what each tool does well first.
- No dinosaur in the serious parts (grounding, citation, trace, positioning).

**Shared design rules:**
- Design tokens from `shared/tokens.css`. Light theme is the page default.
- Fonts: Literata (headings, display, review excerpts), Inter (body), Fira Code (mono: eyebrows, captions, stage names, citation addresses).
- Landing display scale is larger than the app: H1 72–96px desktop / 44–56px mobile; H2 44–56px; body 18–20px in editorial columns, max 60–68ch.
- Section spacing 120–200px desktop, 64–96px mobile. Do not squeeze the act break on mobile.
- Main compositions max 1280–1440px wide; prose columns stay at 55–68ch.
- App crops are enlarged ~1.3–1.4× relative to the app, with unrelated chrome removed.
- Motion: fade-in on scroll at most; spinner in the trace is the only continuous animation. All disabled under `prefers-reduced-motion`. No scroll pinning, autoplay walkthroughs, bouncing, or slide-ins.
- Optional top navigation (Codex): `The synthesis · The evidence · The method` as anchor links, plus a quiet "Feed it a corpus" action. Not an app header.

---

## 1. Hero / The Feed

**Arc role:** Hook (0–5 s). The reader should leave thinking: "A dinosaur eats a folder of PDFs and a literature review comes out. That is a joke, but the subtitle says page and paragraph, so it is a serious joke."

### Copy

**Eyebrow (mono, muted):**
`A literature review pipeline`

**H1 (Literata, display):**
Feed The Saurus your papers.

**Sub (Literata, 28–32px, one line if possible):**
From a folder of PDFs to a literature review, with every claim traced to its page.

**Body (Inter, 18px, max ~52ch):**
Upload the corpus you already curated. A multi-agent pipeline analyzes each paper, extracts themes and claims, deduplicates themes across papers, and writes a cohesive review where every citation resolves to paper, page, and paragraph. You watch every stage. You keep the judgment.

**Primary CTA (accent gold button):**
Feed it a corpus

**Secondary CTA (text link, primary green):**
Inspect a sample synthesis →

**Micro-line under CTAs (mono, muted):**
`Open source · Runs locally · 20 to 100 PDFs per job`

**Benchmark shelf (below the micro-line, mono label + two preset pills):**
Label: `Or inspect a pre-digested sample corpus:`
- Pill 1: **Circadian Misalignment in Shift Work** — `40 papers · 380 pages · 14 themes`
- Pill 2: **Neural Organoid Morphogenesis** — `28 papers · 295 pages · 11 themes`

### Demo elements

- None from the app. No screenshots in the hero. Mood first.
- The benchmark preset pills are the only interactive elements; each opens a finished sample review (same destination as the secondary CTA for pill 1).

### Design notes

- Full viewport, warm paper background (`--saurus-paper`, `#FAFAF7`), light theme.
- Two columns on desktop: copy left, mascot right. Stacked on mobile (copy first).
- Mascot: minimal line-art dinosaur in academic green, mouth open, a stack of PDF sheets going in, one bound document with a green cover coming out. Scientific-illustration weight, not cartoon. This is the only place the mascot is large.
- Optional: a faint ruled-notebook line pattern behind the illustration, very low contrast.
- Preset pills: surface `#F5F5F0`, 1px `--saurus-border`, title in Inter 15px, metrics in Fira Code 12px muted. No dashed dropzone; the CTA opens the real upload entry.

---

## 2. The Problem

**Arc role:** Problem (5–20 s). The reader should feel: "They know exactly which part of a lit review I hate. And they are not claiming to read for me."

### Copy

**Eyebrow (mono):**
`The bookkeeping barrier`

**H2 (Literata):**
Literature reviews take weeks because of bookkeeping, not reading.

**Lead (Inter, 18–20px, editorial column ~60ch):**
You have already done the hard part. The folder has forty papers in it, chosen by you, for a reason. What remains is the part nobody enjoys: reading each one, noting which themes it touches, tracking which papers agree and which do not, finding the page and the paragraph for every claim, and then writing prose that holds all of it together without losing a single citation.

That is not thinking. It is accounting. It fails in three predictable ways.

**Three failure modes (Literata subheads, Inter body, stacked in the same column):**

**The Context Cliff.**
Working memory collapses around paper twelve. By paper thirty-eight you are no longer synthesizing a corpus; you are surviving a reading list, and the last paper is read in isolation from the first.

**The Lexical Disconnect.**
Authors describing the same mechanism use different words for it. One paper says "circadian disruption," another "chronobiological misalignment." A keyword search treats them as two unrelated inquiries, and so does a tired reader.

**The Provenance Drift.**
Notes detach from page numbers. Spreadsheets lose paragraph locations. By the time you write, an assertion has no verifiable address, and finding it again costs an afternoon.

**Pull quote (Literata italic, large, primary green, thin gold rule above):**
The Saurus does the digestion. You stay the author.

### Demo elements

- None. Pure editorial. Typography carries the section.

### Design notes

- Surface tone `--saurus-surface` (`#F5F5F0`) to mark the transition from the hero.
- Single narrow text column offset left; pull quote set large to the right on desktop, below on mobile.
- Failure-mode subheads in Literata 22–24px; no icons, no cards, no numbered badges. A hairline rule between the three is enough.
- This is the section that tells the reader "we know what you do for a living."

---

## 3. Synthesis vs Summary

**Arc role:** Problem → concept (end of Act 1). The reader should understand the single most important claim: the output is organized by theme, not by paper, and should know the four stage names they will see again in the trace.

### Copy

**Eyebrow (mono):**
`Corpus, not document`

**H2 (Literata):**
Synthesis by theme, not summary by paper.

**Body (Inter, ~68ch):**
Document chatbots operate on one paper at a time. Handed a folder, they produce a stack of isolated summaries: paper A studied this, paper B studied that. That is not a literature review. A review is a horizontal cross-section of a field, organized by the concepts running through the literature, not by the bibliographies of the authors who wrote it.

**Stack vs Matrix contrast (two cards, side by side on desktop):**

Left card, label (mono): `The summary stack`
- Subline: Forty papers processed as forty silos.
- Visual: four stacked rows reading `Paper 01 · summary of methods, summary of results`, `Paper 02 · …`, `Paper 03 · …`, `… 37 more summaries` (muted).
- Verdict line (Inter, muted): A list. No cross-paper agreement, no tension, no synthesis.

Right card, label (mono): `The theme matrix`
- Subline: One theme, every paper that touches it.
- Visual: two theme rows from the sample corpus:
  - **Circadian misalignment** — draws on Roenneberg [4], Kalsbeek [11], Vetter [23]. Contrasts persistent melatonin delay with partial re-entrainment between rotations.
  - **Sleep debt and metabolic markers** — draws on Scheer [2], Buxton [9], Morris [17]. Maps agreement on glucose tolerance, disagreement on cortisol timing.
- Verdict line (Inter, primary green): A draft woven around ideas, with the sources still attached.

**Four-step loop (below the contrast, horizontal four-up):**

**Feed**
Drop your PDFs. The Saurus accepts the corpus as it is: no reformatting, no reference manager export, no per-paper setup.

**Digest**
Each paper is analyzed independently and in parallel. Themes and claims are extracted, then themes are matched across the corpus by semantic similarity so that two papers naming the same idea differently end up in the same place.

**Review**
Each theme is reviewed against every paper that touches it. The pipeline then writes a cohesive literature review, structured by theme, with inline citations resolved to paper, page, and paragraph.

**Explore**
Browse per-paper findings, inspect the full trace of every stage, and ask the assistant questions about the corpus. It answers with the same citation discipline as the review.

**Caption under the loop (mono, muted):**
`Paper Analysis → Theme Dedup → Theme Review → Aggregation`

**Closing line (Literata, medium, after the loop):**
Shared vocabulary does not settle a disagreement. The claims and their sources remain there for you to compare.

### Demo elements

- The Stack vs Matrix contrast is a schematic, not an app crop. Drawn in clean vector lines, like a taxonomy chart. The theme rows on the right use the app's merged-theme card styling at reduced scale so the reader recognizes them again in section 5.
- Optional interaction: hovering a theme row highlights its contributing paper numbers. Static fallback is fine.
- The four-step loop uses small line-art glyphs (sheet of paper, overlapping circles, open book, magnifying glass). The dinosaur may appear as a tiny mark at "Feed" only.

### Design notes

- Contrast cards on `--saurus-surface` with 1px `--saurus-border`, modest radius. Left card muted ink; right card with a primary-green header rule. No red/green good-bad coloring beyond that.
- Loop: thin connecting rule between stages using the green→gold progress gradient as a single hairline, not a bar. Airy. This is orientation, not a feature grid.
- Mono caption ties the friendly names to the real stage names so the reader sees the same words in section 8.
- Background returns to `--saurus-paper` for the loop.

---

## 4. Act Break

**Arc role:** The turn. Signals the shift from description to proof. The silence changes the question.

### Copy

**H2 (Literata, 48–72px, centered, alone on the band):**
Any tool can summarize a paper. Here is what happens after that.

**One line under it (Inter, muted-on-dark):**
Four things The Saurus does that a chat window over your PDFs does not. Each one is shown, not asserted.

### Demo elements

- None.

### Design notes

- Full-bleed band in the dark palette: paper `#1A1D1E`, ink `#E8E4DD`, green `#5BAB8A`. "Aged paper under candlelight," not a code terminal.
- This is the one dark moment on the page and exists purely to mark the act change.
- Vertical padding 30–40vh desktop, at least 80–112px mobile. Nothing else in the band: no decoration, no gradient, no animation.
- Everything after this band returns to light paper.

---

## 5. Proof: Semantic Dedup

**Arc role:** Proof 1 (Pillar 1: synthesis, not summary). The reader should be able to *see* three differently named themes become one, and should understand why the product is called a thesaurus.

### Copy

**Eyebrow (mono):**
`Stage 2 · Theme Dedup`

**H2 (Literata):**
Part thesaurus. It connects what authors said differently.

**Body (Inter):**
A thesaurus groups words that share a meaning. The Saurus groups themes that share a phenomenon.

Extraction is easy. The hard part is recognizing that paper 4 calls it "circadian disruption," paper 11 calls it "chronobiological misalignment," and paper 23 calls it "shift-work phase shift" while spending three pages on the same thing. The dedup stage matches themes across the corpus by embedding similarity and merges them, so the review is organized around what the literature discusses, not around the order you uploaded the files.

**Caption (mono, muted):**
Themes are matched by embedding similarity, then confirmed pairwise before merging. Members that fail the check are kept separate.

### Demo elements

Dedup specimen (AGY structure, Fable content). Three-part vertical composition on desktop, or left → right if space allows:

**Input box.** Label (mono): `Raw theme labels · extracted from 40 papers`. A chip list of three paper cards, each carrying its own theme chip in a rotating chip color (`--saurus-chip-1..3`):
- `[4] Roenneberg et al. 2023` — chip: *circadian disruption*
- `[11] Kalsbeek et al. 2024` — chip: *chronobiological misalignment*
- `[23] Vetter et al. 2022` — chip: *shift-work phase shift*

**Connector.** A single green stroke with a mono label at its midpoint: `Theme Dedup · embedding match → pairwise confirm`.

**Output card.** Label (mono): `Merged theme · in the review`. One merged theme card in the app's styling:
- Badge (mono): `Theme 03`
- Title (Literata): **Circadian misalignment**
- Meta (Inter): 3 papers · 11 claims · 1 observed tension
- Alias line (mono, muted): `Merged from: circadian disruption · chronobiological misalignment · shift-work phase shift`

**What the reader should notice:** the three original labels survive as aliases on the merged card. Nothing was discarded; it was connected.

### Design notes

- Light `--saurus-paper` background. Copy left, specimen right on desktop; copy then specimen on mobile.
- The specimen is a cropped, enlarged composite of real app components (paper cards, theme chips, merged theme card), ~1.4× app scale. The reader is looking at evidence, not using a UI.
- Chips: muted pastel fills with crisp 1px borders, like index cards in a library catalog.
- Merge stroke is one green line. Fade-in on scroll only; none under `prefers-reduced-motion`.
- No mascot.

---

## 6. Proof: Every Claim Has an Address

**Arc role:** Proof 2 (Pillar 2). The centerpiece of the page. The reader should see a citation resolve to a paragraph and a recorded grounding check, and should feel: "I could defend this sentence in a committee meeting."

### Copy

**Eyebrow (mono):**
`Stage 4 · Aggregation`

**H2 (Literata):**
Every citation has an address.

**Body (Inter):**
Not a paper title. Not "according to the literature." A paper, a page, and a paragraph. Every claim in the review resolves to a location you can open and read, which means every sentence is one you can defend in a committee meeting, or delete because you disagree with it.

**Caption (mono, muted, under the specimen):**
`[n]` resolves to the reference entry. `(p.12,§3)` resolves to the paragraph. Both are checked before the review is returned.

### Demo elements

Two panes side by side on desktop (review excerpt left ~60%, receipt card right ~40%); stacked on mobile.

**Left pane: review excerpt.** Label (mono): `Generated review · §2.3 Recovery dynamics`. Set in Literata 22–24px, line-height 1.7, on a paper-toned manuscript surface:

> Night-shift schedules are consistently associated with delayed melatonin onset relative to day workers [4](p.7,§2), an effect that persists for at least three consecutive rest days [11](p.12,§3). Vetter and colleagues report a smaller but measurable shift in rotating-shift cohorts [23](p.4,§1), which they attribute to partial re-entrainment between rotations [23](p.5,§2).

Citations render as pills in Fira Code: `[n]` in primary green, `(p.x,§y)` in muted mono. The citation `[11](p.12,§3)` is shown in its active state (gold underline, slightly raised), with a thin connector line to the receipt card.

**Right pane: receipt card** (AGY component, rendered open statically, no interaction needed):
- Header badge (mono, green): `✓ Grounded citation`
- Address (mono): `[11] Kalsbeek et al. 2024 · p.12 · §3`
- Source quote (Literata italic, blockquote, entailing sentence underlined in gold):
  > "Dim-light melatonin onset remained delayed by a mean of 2.1 h on the third consecutive rest day, indicating that re-entrainment to a day-active schedule was incomplete within the recovery window studied."
- Audit grid (2×2, label mono muted / value Inter):
  - Entailment status — **Entailed**
  - NLI score — `0.94`
  - Claim ID — `kalsbeek-2024-c07`
  - Cited in — `§2.3, §4.1`
- Footer line (mono, muted): `Checked by NLI cross-encoder · citation guard passed`

**What the reader should notice:** the claim in the review and the sentence in the source sit next to each other; the score is a recorded check, not a promise; the claim has an ID that the guard can verify exists.

### Design notes

- This is the largest single visual on the page. Give it room: near full-width composition.
- Receipt card on `--saurus-surface`, gold left border (`--saurus-accent`), `--shadow-md`.
- No mascot. No decoration beyond the one gold underline and the gold border. Paper background, ink text. The restraint is the point.
- Optional: hover/tap on another citation swaps which receipt is open. Static fallback required.
- Every value shown must come from a real job before publishing (see Open items).

---

## 7. Proof: Grounding Verification

**Arc role:** Proof 3 (Pillar 2, method). The section a skeptical PI reads twice. The reader should learn what is checked, by what, and what happens when the check fails, and should hear the tool state its own limit.

### Copy

**Eyebrow (mono):**
`Verification`

**H2 (Literata):**
The model asserts. Something else checks.

**Body (Inter):**
Language models produce citations that read correctly and are not. The Saurus does not ask you to trust that this did not happen. It checks, mechanically, at two points, and sends failures back rather than through.

**Three-step diagram (numbered nodes, Literata label + Inter body, mono sublabel):**

**1 · Entailment.** `NLI cross-encoder`
A natural-language-inference cross-encoder reads each cited claim against the cited passage and scores whether the passage actually entails the claim. It has one job, and it is not the model that wrote the review.

**2 · Citation integrity.** `citation guard`
A guard verifies that every `[n](p.x,§y)` in the review resolves to a real claim extracted in stage one. A citation to a claim that does not exist is rejected before you see it.

**3 · Reask, not shrug.** `reask`
When entailment is borderline or a citation fails to resolve, the offending passage is sent back to the writing agent with the failure attached. Borderline cases are escalated to a stricter check rather than waved through. Failures that survive are shown in the trace, not smoothed over.

**Closing line (Literata, medium):**
This reduces fabrication risk by mechanism. The mechanism is the message.

**Limit statement (Inter, set apart with a hairline rule above, verbatim from Codex):**
The check tests support in a passage. It does not establish that a study is sound or that your corpus covers the field. You still assess the evidence and the draft's interpretation.

### Demo elements

- The diagram: three numbered nodes in a horizontal line on desktop (vertical on mobile), connected by thin rules. Node 3 has a small loop-back arrow to a small mono label `writing agent`.
- One real trace line under the diagram, rendered in the pipeline trace style at small size:
  `⟳ Theme Review · batch 3 · reask · entailment 0.41 < 0.60 · retry 1/2`
- **What the reader should notice:** the threshold and the retry count are visible. The failure is information, not alarm.

### Design notes

- Serious register. No dinosaur, no chip colors, no playful glyphs.
- `--saurus-surface` background to set it apart as the "method" section.
- Diagram nodes: hairline circles with the number in Literata, mono sublabels in muted ink. Rules in `--color-border`.
- Every sentence in this section must be literally true of the pipeline. The NLI threshold (0.60) must match the configured value before publishing.

---

## 8. Proof: Pipeline Trace

**Arc role:** Proof 4 (Pillar 3: you can watch it think). The reader should see a real run with a skipped paper, a reask, and a resume, and conclude "nothing is hidden" because the trace shows what went wrong.

### Copy

**Eyebrow (mono):**
`Pipeline Trace`

**H2 (Literata):**
Watch every stage. Nothing is hidden.

**Body (Inter):**
A single prompt over a context window is not a process you can inspect, resume, or reproduce. The Saurus runs as a durable pipeline: each paper analyzed independently, each stage recorded as it happens, each agent's events visible in real time. If a paper cannot be parsed, the review says so and continues. If the job crashes, it resumes from the last completed stage, and the trace shows the resume honestly.

**Caption (mono, muted):**
Every event is persisted as it occurs. The trace you see during the run is the trace you can open afterward.

### Demo elements

Pipeline specimen (AGY structure, Fable content). One framed panel, three parts:

**Header.**
- Badge (mono): `JOB circadian-2026-09 · Recorded sample run`
- Title (Inter): Corpus: Circadian Misalignment in Shift Work (40 papers · 380 pages)
- Metrics row (four tiles, value Literata large / label mono):
  `39/40` Parsed · `187` Themes raw · `41` Themes merged · `312` Claims traced

**Stage list** (app trace component, enlarged ~1.3×, status icons exactly per design system):

```
✓  Ingestion          40/40 converted                           12.4s
✓  Paper Analysis     39/40 · 312 claims · 187 themes           4m 02s
   └ [7] Sørensen et al.   could not be parsed · skipped
✓  Theme Dedup        187 → 41 themes                           38s
⟳  Theme Review       batch 6/9 · 5 themes per batch            running
   └ batch 3           reask · entailment 0.41 < 0.60 · retry 1/2
○  Aggregation                                                  pending
                                                       resumed from journal
```

**Event log strip** (below the stages, mono 12–13px, label `Event log · append-only NDJSON`):
```
[14:32:01] paper_analysis/[7]   parse failed · skipped · review continues
[14:32:03] theme_dedup          merged "circadian disruption" + "chronobiological misalignment" → "Circadian misalignment"
[14:32:08] theme_review/batch-3 reask · entailment 0.41 < 0.60 · retry 1/2
[14:32:11] theme_review/batch-3 retry passed · entailment 0.87
[14:32:14] workflow             resumed from journal · 3 stages replayed, 0 re-executed
```

**What the reader should notice:** the skipped paper, the reask, and the resume are all present and all in plain text. A clean all-green trace would prove less.

### Design notes

- Panel on `--saurus-surface` with `--shadow-md`, hairline border. Light background; this is not a dark console.
- Status colors per design system: success green + check, active green + spinner, pending muted + circle. Skipped paper in plain ink, not red: it is information, not alarm.
- Spinner is the only animation; it stops under `prefers-reduced-motion`.
- Copy left, panel right on desktop; stacked on mobile with the panel scrolling horizontally inside its own container if needed.
- Optional: one event expandable to its paper findings. Static fallback required.
- No mascot.

---

## 9. Where It Sits

**Arc role:** Conviction (positioning). The reader should place The Saurus downstream of tools they already use and feel no rivalry was implied.

### Copy

**H2 (Literata):**
Downstream of the tools you already use.

**Body (Inter, short):**
Use Semantic Scholar or Research Rabbit to find the papers. Use Elicit or Consensus to pull claims from them. Use a writing assistant to polish your own argument. The Saurus is the step in between: it takes the folder and produces the review those tools do not write.

**Table (Inter 15px, column 3 header in primary green):**

| | They give you | The Saurus gives you |
|---|---|---|
| Discovery tools | Papers to read | Synthesis of papers you already have |
| Extraction tools | Claims per paper, side by side | Themes deduplicated across papers, written into a review |
| General LLMs | An answer, unverified | A review, traced to page and paragraph, grounding-checked |
| Writing assistants | Faster prose for your argument | The literature-review draft your argument sits on |
| Manual review | Total control, days of work | Same control, minutes of bookkeeping |

### Demo elements

- None.

### Design notes

- Compact. `--saurus-paper` background, hairline table rules in `--color-border`, no row shading.
- No logos of other products. Names in plain text. Respectful by design.
- No mascot.

---

## 10. The Author Stays the Author

**Arc role:** Conviction (Pillar 4). The reader should feel: "It does not pretend to be my judgment. It told me what it will not do."

### Copy

**Eyebrow (mono):**
`The division of labor`

**H2 (Literata):**
A draft to argue with, not a verdict to accept.

**Body (Inter):**
The Saurus produces a draft and the evidence behind it. It does not rank your papers by importance, does not decide what the field has concluded, and does not claim to have understood anything. It produces the map. Reading is still yours, and so is the argument.

The review is editable and exportable. The per-paper findings are browsable. And the assistant, when you ask it something, answers with citations rather than verdicts.

**Two-column compact cards:**

Left card, heading (Literata): **What The Saurus does**
- Extracts themes and claims in parallel across your PDFs
- Reconciles diverging author terminology through semantic deduplication
- Verifies every cited claim against its source passage with an NLI check
- Delivers an editable review with citations resolved to page and paragraph
- Keeps a persistent, inspectable trace for every stage

Right card, heading (Literata): **What The Saurus will not do**
- Assert that a review is complete without your reading it
- Fabricate a citation or smooth over a broken reference
- Claim to have understood the implications of your field
- Produce your thesis contribution or original argument
- Train on your unreleased manuscripts

**Assistant subheading (Literata, small):**
Keep asking questions of the corpus.

**Assistant caption (mono, muted):**
Answers cite the same claim set as the review. If the corpus does not contain it, the assistant says so.

**Closing line (Literata, medium, verbatim from Codex):**
The Saurus does the digestion. You decide what the literature supports.

### Demo elements

Assistant excerpt, small and secondary, rendered as two paper-toned message blocks beside or below the cards:

> **You:** Which papers disagree about whether the melatonin delay recovers within a week?
>
> **Assistant:** Two positions appear in the corpus. Kalsbeek et al. report persistence beyond three rest days [11](p.12,§3), while Vetter et al. observe partial re-entrainment between rotations [23](p.5,§2). Roenneberg et al. do not address recovery timing directly [4]. The corpus does not contain a study extending beyond seven days, so it cannot settle the question as posed. The review discusses this under §2.3, *Recovery dynamics*.

Citations in mono green, styled identically to section 6. **What the reader should notice:** the assistant names the disagreement, cites both sides with addresses, and says what the corpus does not contain rather than filling the gap.

Optional: a small static `Export · Markdown / PDF` control beside the copy to make "editable and exportable" visible.

### Design notes

- Quiet section. `--saurus-paper` background, wide margins.
- Cards on `--saurus-surface`, hairline border. Left list with small green check marks; right list with small muted dashes (not red crosses).
- Assistant excerpt in Inter 15–16px, no avatars, no chat chrome beyond the two blocks. This is a supporting proof, not a centerpiece.
- No mascot; the dinosaur returns in the next section.

---

## 11. Close / CTA

**Arc role:** Close (last 10 s). The reader should feel: "Fine. Feed it my papers." The page closes on the line it opened with.

### Copy

**H2 (Literata, display, same scale as hero H1):**
Feed The Saurus your papers.

**Sub (Literata, 24–28px):**
Forty papers in. One review out. Every claim traced to a paragraph.

**Primary CTA (accent gold):**
Feed it a corpus

**Secondary CTA (text link):**
Read the docs →

**Benchmark presets (label + two cards):**
Label (mono): `Or inspect a finished review right now:`
- Card 1: **Circadian Misalignment in Shift Work** — `40 papers · 380 pages · 14 themes · 312 traced claims` — `Inspect the review →`
- Card 2: **Neural Organoid Morphogenesis** — `28 papers · 295 pages · 11 themes · 89 traced claims` — `Inspect the review →`

**Mascot sign-off (small Literata italic, beside a small line-art dinosaur):**
Hungry for papers since the Cretaceous!

### Demo elements

- None from the app. The CTA opens the real upload entry; no decorative dropzone.
- Preset cards reuse the pill styling from the hero at card scale.

### Design notes

- Large, quiet, mostly whitespace. Warm `--saurus-paper` background.
- Optional: the faint gold→green gradient hairline from section 3 as a single horizontal rule above the CTA.
- Mascot small (a quarter of hero size), placed at the edge, looking satisfied. This is the one exclamation mark on the page and the last playful note.

---

## 12. Footer

**Arc role:** Boilerplate. Compact.

### Copy

**Wordmark:** The Saurus

**Footer line (Literata italic, small, verbatim from Codex):**
Part thesaurus. Part dinosaur. Here to devour papers.

**Boilerplate (Inter, small, from positioning appendix):**
The Saurus is a literature review pipeline. Upload a corpus of scientific PDFs and a multi-agent pipeline analyzes each paper in parallel, extracts themes and claims, deduplicates themes semantically across the corpus, and writes a cohesive literature review where every claim is cited to paper, page, and paragraph. Citation grounding is verified mechanically, and every pipeline stage is visible in real time. The Saurus produces the draft and the evidence; the researcher keeps the judgment.

**Link columns (AGY structure, three columns):**

Architecture
- Pipeline stages
- Grounding verification
- Semantic deduplication
- Event trace and recovery

Integration
- Python pipeline API
- Papers MCP server
- Qdrant vector store
- Command-line clients

Exports
- Markdown
- PDF
- YAML / NDJSON job data
- BibTeX

**Bottom line (Inter, small, muted):**
Open source · Runs locally · No papers retained for training · GitHub · Documentation · License

### Demo elements

- None.

### Design notes

- `--saurus-sidebar` background, muted ink, hairline top border. Compact.
- No mascot in the footer (the sign-off in section 11 was the last appearance).
- Link targets must point to real docs; remove any column entry that has no destination at publish time.

---

## Copy audit against positioning

- Exclamation marks: 1 (section 11 mascot sign-off).
- Words used: devour (12), digest/digestion (2, 3, 10), feed (1, 3, 11), corpus (throughout), synthesis (3, 9), theme/claim (throughout), trace/traced (1, 6, 8, 11), grounded/grounding (6, 7, 9), resolve (1, 6, 7), stage/pipeline (throughout), verify (7, 10), source (6, 7, 10).
- Words avoided: no "magic," "revolutionary," "effortless," "instant," "intelligent," "smart," "AI-powered," "unlock," "supercharge," "10x," "game-changing," "leverage." "Understood" appears only in negation (section 10: "does not claim to have understood") as positioning itself does.
- No accuracy promise: section 7 says what is checked and how, then states the limit; section 6 shows a recorded score, not a guarantee.
- No replacement claim: sections 2, 10, 11 state the researcher keeps judgment.
- No competitor bashing: section 9 names what each tool does well first; section 3 describes chatbots' behavior, not their worth.
- Mascot absent from 5–10.
- Time claim: "minutes of bookkeeping" appears only in the section 9 table row, quoted from positioning. No "in minutes" promise in the hero or close.
- Dinosaur absent from grounding, citation, trace, and positioning sections.

## Open items for the HTML round

1. **Real dedup example.** The circadian theme names and paper numbers are plausible placeholders. Replace with an actual merged theme from a real job's YAML so section 5 is literally true.
2. **Real trace.** Pull an actual `events.ndjson` slice with a skipped paper, a reask, and a resume so section 8 is a recording, not a mock. Adjust the metrics header to match.
3. **Real receipt.** Section 6's source quote, NLI score, and claim ID must come from the same job.
4. **NLI threshold.** The value 0.60 in sections 7 and 8 must match the configured pipeline value.
5. **Second benchmark corpus.** "Neural Organoid Morphogenesis" is a placeholder; either run it or replace it with a real second corpus. If only one corpus exists, show one preset in sections 1 and 11.
6. **Mascot illustration.** Needs a hero-scale version (papers in, review out) and a small satisfied version for section 11.
7. **Footer links.** Confirm every link column entry has a real destination.
8. **Export formats.** Confirm which exports ship (Markdown, PDF, BibTeX) and trim the footer column to match.
