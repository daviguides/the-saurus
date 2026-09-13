# The Saurus — Landing Page Brief (Fable)

_Source of truth: `docs/foundation/vision.md`, `positioning.md`, `design-system.md`. When this brief contradicts positioning, positioning wins._

Governing line for the whole page: **A chatbot gives you an answer. The Saurus gives you the receipts.**

Governing rule for the whole page: the landing is not the app in a scroll. App elements appear only as *evidence* — cropped, enlarged, framed by a sentence that tells the reader what they are looking at and why it matters. Mood before information. Editorial breathing between blocks.

The page has one exclamation mark. It is in Section 10 (the mascot sign-off). Nowhere else.

---

## A: Landing Page Sections

Two acts. Act 1 answers "what is this" in under one screen of reading. Act 2 answers "why should I, of all people, believe it" with demonstrations.

| # | Section | Act | Purpose | Key content | Weight |
|---|---|---|---|---|---|
| 1 | **Hero** | 1 | Own the name, state the loop, set the mood | Tagline, one-line expansion, primary CTA, mascot line art, a folder-to-review visual | Hero (full viewport) |
| 2 | **The Problem** | 1 | Name the pain precisely: bookkeeping, not reading | Three sentences, one large pull quote, no UI | Editorial (medium) |
| 3 | **The Loop** | 1 | Show the four stages in plain language | Feed → Digest → Review → Explore; one line each | Medium, horizontal |
| 4 | **Act break: "What no one else does"** | — | Signal the shift from description to proof | A single heading and one sentence | Compact (divider) |
| 5 | **Proof 1: Synthesis by theme** | 2 | Demonstrate corpus-level synthesis and dedup | Before/after: per-paper themes → merged theme; real dedup example ("circadian" / "chronobiological") | Large (demo) |
| 6 | **Proof 2: Every claim has an address** | 2 | Demonstrate page-and-paragraph citation | Enlarged review excerpt with `[3](p.12,§3)`, hover state opening the source paragraph | Large (demo, the centerpiece) |
| 7 | **Proof 3: Grounding is checked, not assumed** | 2 | Explain the NLI check and citation guard mechanically | Three-step verification diagram; the word "reask" | Medium (serious register, no mascot) |
| 8 | **Proof 4: Watch every stage** | 2 | Demonstrate the live trace and durability | Pipeline trace panel, one stage mid-run, one stage marked "resumed" | Large (demo) |
| 9 | **Where it sits** | 2 | Position against adjacent tools without contempt | Compact comparison table from positioning §3 | Compact |
| 10 | **The author stays the author** | 2 → close | Conviction: the draft is yours; the assistant answers, it does not rule | Short text, assistant excerpt with a cited answer, export mention | Medium |
| 11 | **Close / CTA** | close | Return to the tagline; ask once | Tagline, CTA, mascot sign-off (the one exclamation mark) | Hero-adjacent (large, quiet) |
| 12 | **Footer** | — | Boilerplate, links, open-source note | One-paragraph boilerplate, GitHub, docs | Compact |

Rough vertical budget: Act 1 ≈ 30% of scroll, Act 2 ≈ 60%, close ≈ 10%.

---

## B: Narrative Arc

| Arc role | Time | Sections | What the reader should feel / know when it ends |
|---|---|---|---|
| **Hook** (first 5 s) | 0–5 s | 1 Hero | "A dinosaur eats a folder of PDFs and a literature review comes out. That's a joke, but the subtitle says page and paragraph, so it's a serious joke." |
| **Problem** | 5–20 s | 2 Problem, 3 Loop | "They know exactly which part of a lit review I hate. And they aren't claiming to read for me." |
| **Proof** (demos, not claims) | 20 s–2 min | 4 Act break, 5 Synthesis, 6 Address, 7 Grounding, 8 Trace | "I've seen the merged theme. I've seen a citation resolve to a paragraph. I've seen what happens when the check fails. I've seen the trace." Each proof is something they could *see*, not something they are asked to believe. |
| **Conviction** (trust) | 2–3 min | 9 Where it sits, 10 Author stays author | "This does the step after the tools I already use. It doesn't pretend to be my judgment. It knows my fear is the fabricated citation, and it told me how it handles that instead of promising." |
| **Close** (CTA) | last 10 s | 11 Close, 12 Footer | "Fine. Feed it my papers." |

Mapping to messaging pillars:
- Pillar 1 (Synthesis, not summary) → Sections 3, 5
- Pillar 2 (Every claim has an address) → Sections 6, 7
- Pillar 3 (You can watch it think) → Section 8
- Pillar 4 (Researcher stays the author) → Sections 10, 11

The dinosaur appears in 1, 3 (lightly), and 11. It is absent from 6, 7, 8, 9.

---

## C: Real Copy

### 1. Hero

**Eyebrow (mono, muted):**
`A literature review pipeline`

**H1 (Literata, display size):**
Feed The Saurus your papers.

**Sub (Literata, large, one line if possible):**
From a folder of PDFs to a literature review, with every claim traced to its page.

**Body (Inter, short):**
Upload the corpus you already curated. A multi-agent pipeline analyzes each paper, extracts themes and claims, deduplicates themes across papers, and writes a cohesive review where every citation resolves to paper, page, and paragraph. You watch every stage. You keep the judgment.

**Primary CTA (accent gold):**
Feed it a corpus

**Secondary CTA (text link, primary green):**
See a finished review →

**Micro-line under CTAs (mono, muted):**
Open source · Runs locally · 20 to 100 PDFs per job

**Design notes**
- Full-viewport, warm paper background (`--saurus-paper`), light theme.
- Left column: copy. Right column: the mascot — minimal line-art dinosaur, mouth open, a stack of PDF sheets going in, a single bound document with a green cover coming out. Scientific-illustration weight, not cartoon. This is the only place the mascot is large.
- H1 at editorial display scale (72–96px desktop), far larger than anything in the app. Sub in Literata regular, 28–32px. Body Inter 18px, max ~52ch.
- No screenshots in the hero. Mood first.
- Optional: a faint ruled-notebook line pattern behind the illustration, very low contrast.

---

### 2. The Problem

**H2 (Literata):**
Literature reviews take weeks because of bookkeeping, not reading.

**Body (Inter, 18–20px, editorial column):**
You have already done the hard part. The folder has forty papers in it, chosen by you, for a reason. What remains is the part nobody enjoys: reading each one, noting which themes it touches, tracking which papers agree and which do not, finding the page and the paragraph for every claim, and then writing prose that holds all of it together without losing a single citation.

That is not thinking. It is accounting. And it is why most researchers do fewer literature reviews, less thoroughly, than they would like.

**Pull quote (Literata italic, large, green):**
The Saurus does the digestion. You stay the author.

**Design notes**
- No UI. Pure editorial. Wide margins, a single narrow text column (~60ch) offset left, pull quote set large to the right or below with a thin gold rule above it.
- Surface tone slightly different from hero (`--saurus-surface`) to mark the transition.
- Typography does the work: this is the section that tells the reader "we know what you do for a living."

---

### 3. The Loop

**H2:**
Four stages. None of them hidden.

**Four columns (Literata heading, Inter body):**

**Feed**
Drop your PDFs. The Saurus accepts the corpus as it is: no reformatting, no reference manager export, no per-paper setup.

**Digest**
Each paper is analyzed independently and in parallel. Themes and claims are extracted, then themes are matched across the corpus by semantic similarity so that two papers naming the same idea differently end up in the same place.

**Review**
Each theme is reviewed against every paper that touches it. The pipeline then writes a cohesive literature review, structured by theme, with inline citations resolved to paper, page, and paragraph.

**Explore**
Browse per-paper findings, inspect the full trace of every stage, and ask the assistant questions about the corpus. It answers with the same citation discipline as the review.

**Caption under the row (mono, muted):**
`Paper Analysis → Theme Dedup → Theme Review → Aggregation`

**Design notes**
- Horizontal four-up on desktop, stacked on mobile. Thin connecting line between stages using the progress-bar gradient (green → gold) as a single rule, not a bar.
- Each stage gets a small line-art glyph (sheet of paper, overlapping circles, open book, magnifying glass). The dinosaur may appear as a tiny mark at "Feed" only.
- The mono caption ties the friendly names to the real stage names, so the reader sees the same words later in the trace demo.
- Keep it airy. This is orientation, not a feature grid.

---

### 4. Act break

**H2 (Literata, large, centered, alone on a dark band):**
Any tool can summarize a paper. Here is what happens after that.

**One line under it (Inter, muted-on-dark):**
Four things The Saurus does that a chat window over your PDFs does not. Each one is shown, not asserted.

**Design notes**
- Full-bleed band in the dark theme palette (`#1A1D1E` paper, `#E8E4DD` ink, `#5BAB8A` green). "Aged paper under candlelight," not a code terminal. This is the one dark moment on the page and it exists purely to mark the act change.
- Generous vertical padding (30–40vh). Nothing else in the band.
- Everything after this band returns to light paper.

---

### 5. Proof 1: Synthesis by theme

**Eyebrow (mono):** `Stage 2 · Theme Dedup`

**H2:**
Synthesis by theme, not summary by paper.

**Body:**
Extraction is easy. The hard part is recognizing that paper 4 calls it "circadian disruption," paper 11 calls it "chronobiological misalignment," and paper 23 never names it at all but spends three pages on it. The dedup stage matches themes across the corpus semantically and merges them, so the review is organized around what the literature discusses, not around the order you uploaded the files.

**Demo element (enlarged, real data):**

Left: three paper cards, each with its own theme chips —
- `[4] Roenneberg et al.` — chip: *circadian disruption*
- `[11] Kalsbeek et al.` — chip: *chronobiological misalignment*
- `[23] Vetter et al.` — chip: *shift-work phase shift*

Arrow / merge line →

Right: one merged theme card —
**Circadian misalignment** — 3 papers · 11 claims
_Merged from: circadian disruption · chronobiological misalignment · shift-work phase shift_

**Caption (mono, muted):**
Themes are matched by embedding similarity, then confirmed pairwise before merging. Members that fail the check are kept separate.

**Design notes**
- The demo is a cropped, enlarged composite of real app components (paper cards, theme chips in rotating chip colors, the merged theme card). Scale up ~1.4× relative to the app; the reader is looking at evidence, not using a UI.
- Light background. Copy on the left, demo on the right; on mobile, copy then demo.
- The merge arrow is a single green stroke. No animation beyond a fade-in on scroll (and none under `prefers-reduced-motion`).

---

### 6. Proof 2: Every claim has an address

**Eyebrow (mono):** `Stage 4 · Aggregation`

**H2:**
Every citation has an address.

**Body:**
Not a paper title. Not "according to the literature." A paper, a page, and a paragraph. Every claim in the review resolves to a location you can open and read, which means every sentence is one you can defend in a committee meeting, or delete because you disagree with it.

**Demo element (the centerpiece of the page):**

An enlarged excerpt from a generated review, set in Literata:

> Night-shift schedules are consistently associated with delayed melatonin onset relative to day workers [4](p.7,§2), an effect that persists for at least three consecutive rest days [11](p.12,§3). Vetter and colleagues report a smaller but measurable shift in rotating-shift cohorts [23](p.4,§1), which they attribute to partial re-entrainment between rotations [23](p.5,§2).

One citation, `[11](p.12,§3)`, is shown in its hover state: a small paper-toned card opens beside it containing the source paragraph from the PDF with the entailing sentence underlined in gold, plus the line:

`Kalsbeek et al. 2024 · p.12 · §3 · claim kalsbeek-2024-c07 · grounding: entailed (0.94)`

**Caption (mono, muted):**
`[n]` resolves to the reference entry. `(p.12,§3)` resolves to the paragraph. Both are checked before the review is returned.

**Design notes**
- This is the largest single visual on the page. Give it room: near full-width, the review excerpt at 22–24px Literata with 1.7 line-height, citations in Fira Code green with the position in muted mono.
- The hover card is rendered open in the static page (no interaction needed to see it), with a thin gold rule and `--shadow-md`.
- No mascot. No decoration. Paper background, ink text, one gold underline. The restraint is the point.
- If the page supports it, a second state on hover/tap that swaps which citation is open. Optional.

---

### 7. Proof 3: Grounding is checked, not assumed

**Eyebrow (mono):** `Verification`

**H2:**
The model asserts. Something else checks.

**Body:**
Language models produce citations that read correctly and are not. The Saurus does not ask you to trust that this did not happen. It checks, mechanically, at two points:

**Three-step diagram (Inter, labeled):**

**1 · Entailment.**
A natural-language-inference cross-encoder reads each cited claim against the cited passage and scores whether the passage actually entails the claim. It has one job and it is not the model that wrote the review.

**2 · Citation integrity.**
A guard verifies that every `[n](p.x,§y)` in the review resolves to a real claim extracted in stage one. A citation to a claim that does not exist is rejected before you see it.

**3 · Reask, not shrug.**
When entailment is borderline or a citation fails to resolve, the offending passage is sent back to the writing agent with the failure attached. Borderline cases are escalated to a stricter check rather than waved through. Failures that survive are shown in the trace, not smoothed over.

**Closing line (Literata, medium):**
This reduces fabrication risk by mechanism. The mechanism is the message.

**Design notes**
- Serious register. No dinosaur, no chip colors, no playful glyphs. `--saurus-surface` background to set it apart as the "method" section.
- Diagram: three numbered nodes in a vertical or horizontal line, connected by thin rules. Node 3 has a small loop-back arrow to the writer. Mono labels: `NLI cross-encoder`, `citation guard`, `reask`.
- Optional small evidence element: a real trace line, e.g. `⟳ Theme Review · batch 3 · reask (entailment 0.41 < 0.6) · retry 1/2`. Rendered in the pipeline trace style at small size.
- This is the section a skeptical PI reads twice. Every sentence must be literally true of the pipeline.

---

### 8. Proof 4: Watch every stage

**Eyebrow (mono):** `Pipeline Trace`

**H2:**
Watch every stage. Nothing is hidden.

**Body:**
A single prompt over a context window is not a process you can inspect, resume, or reproduce. The Saurus runs as a durable pipeline: each paper analyzed independently, each stage recorded as it happens, each agent's events visible in real time. If a paper cannot be parsed, the review says so and continues. If the job crashes, it resumes from the last completed stage, and the trace shows the resume honestly.

**Demo element (real trace, enlarged):**

```
✓  Ingestion          40/40 converted                           12.4s
✓  Paper Analysis     40/40 · 312 claims · 187 themes           4m 02s
   └ [7] Sørensen et al.   could not be parsed · skipped
✓  Theme Dedup        187 → 41 themes                           38s
⟳  Theme Review       batch 6/9 · 5 themes per batch            running
   └ batch 3           reask · entailment 0.41 < 0.60 · retry 1/2
○  Aggregation                                                  pending
                                                       resumed from journal
```

**Caption (mono, muted):**
Every event is persisted as it occurs. The trace you see during the run is the trace you can open afterward.

**Design notes**
- The trace panel is a real app component, enlarged ~1.3×, rendered on `--saurus-surface` with `--shadow-md`. Status colors exactly as the design system: success green + check, active green + spinner, pending muted + circle, the skipped paper in plain text (not red — it is information, not alarm).
- The `resumed from journal` line and the `reask` line are both deliberately included. They demonstrate "no hidden stages" better than a clean all-green trace would.
- Spinner is the only animation, and it stops under `prefers-reduced-motion`.
- Copy left, trace right on desktop.

---

### 9. Where it sits

**H2:**
Downstream of the tools you already use.

**Body (short):**
Use Semantic Scholar or Research Rabbit to find the papers. Use Elicit or Consensus to pull claims from them. Use a writing assistant to polish your own argument. The Saurus is the step in between: it takes the folder and produces the review those tools do not write.

**Table (compact, Inter 15px):**

| | They give you | The Saurus gives you |
|---|---|---|
| Discovery tools | Papers to read | Synthesis of papers you already have |
| Extraction tools | Claims per paper, side by side | Themes deduplicated across papers, written into a review |
| General LLMs | An answer, unverified | A review, traced to page and paragraph, grounding-checked |
| Writing assistants | Faster prose for your argument | The literature-review draft your argument sits on |
| Manual review | Total control, days of work | Same control, minutes of bookkeeping |

**Design notes**
- Compact. Paper background, hairline table rules in `--color-border`, no shading. Column 3 header in primary green.
- No logos of other products. Names in plain text. Respectful by design.

---

### 10. The author stays the author

**H2:**
It reads the corpus. You keep the judgment.

**Body:**
The Saurus produces a draft and the evidence behind it. It does not rank your papers by importance, does not decide what the field has concluded, and does not claim to have understood anything. It produces the map. Reading is still yours, and so is the argument.

The review is editable and exportable. The per-paper findings are browsable. And the assistant, when you ask it something, answers with citations rather than verdicts.

**Demo element (assistant excerpt, small):**

> **You:** Which papers disagree about whether the melatonin delay recovers within a week?
>
> **Assistant:** Two positions appear in the corpus. Kalsbeek et al. report persistence beyond three rest days [11](p.12,§3), while Vetter et al. observe partial re-entrainment between rotations [23](p.5,§2). Roenneberg et al. do not address recovery timing directly [4]. The review discusses this under §2.3, *Recovery dynamics*.

**Caption (mono, muted):**
Answers cite the same claim set as the review. If the corpus does not contain it, the assistant says so.

**Design notes**
- Quiet section. Assistant excerpt rendered as two paper-toned message blocks, Inter, citations in mono green. Small: this is a supporting proof, not a centerpiece.
- Optional: a small "Export · Markdown / PDF" control shown as a static element beside the copy, to make "editable and exportable" visible.
- Still no mascot; the dinosaur returns in the next section.

---

### 11. Close / CTA

**H2 (Literata, display size, same as hero):**
Feed The Saurus your papers.

**Sub:**
Forty papers in. One review out. Every claim traced to a paragraph.

**Primary CTA (accent gold):**
Feed it a corpus

**Secondary CTA:**
Read the docs →

**Mascot sign-off (mono or small Literata italic, beside a small line-art dinosaur):**
Hungry for papers since the Cretaceous!

**Design notes**
- Large, quiet, mostly whitespace. The H1-scale tagline returns so the page closes on the same line it opened with.
- The mascot is small here (a quarter of hero size), placed at the edge, looking satisfied. This is the one exclamation mark on the page and the last playful note.
- Warm paper background. Optionally the faint gold→green gradient rule from Section 3 as a single horizontal line above the CTA.

---

### 12. Footer

**Boilerplate (Inter, small):**
The Saurus is a literature review pipeline. Upload a corpus of scientific PDFs and a multi-agent pipeline analyzes each paper in parallel, extracts themes and claims, deduplicates themes semantically across the corpus, and writes a cohesive literature review where every claim is cited to paper, page, and paragraph. Citation grounding is verified mechanically, and every pipeline stage is visible in real time. The Saurus produces the draft and the evidence; the researcher keeps the judgment. Part thesaurus, part dinosaur.

**Links:** GitHub · Documentation · Architecture · Design system · License

**Design notes**
- `--saurus-sidebar` background, muted ink, hairline top border. Compact. No mascot.

---

## Copy audit against positioning

- Exclamation marks: 1 (Section 11).
- Words used: devour (mascot only, implied in illustration), digest/digestion (2, 3), feed (1, 3, 11), corpus (throughout), synthesis (5, 9), theme/claim (throughout), trace/traced (1, 6, 8, 11), grounded/grounding (6, 7, 9).
- Words avoided: no "magic," "revolutionary," "effortless," "instant," "understand" (Section 10 uses "does not claim to have understood" — a negation, deliberately), "intelligent," "unlock," "supercharge," "AI-powered."
- No accuracy promise: Section 7 says what is checked and how; Section 6 hover shows a score, not a guarantee.
- No replacement claim: Sections 2, 10, 11 all state the researcher keeps judgment.
- No competitor bashing: Section 9 names what each tool does well first.
- Mascot absent from 6, 7, 8, 9 (the trust sections).
- Time claim: "minutes of bookkeeping" appears only in the comparison table row, quoted from positioning; no "in minutes" promise in the hero.

## Open items for the HTML round

1. Real dedup example: the circadian names are plausible placeholders. Replace with an actual merged theme from a real job's YAML so the demo is literally true.
2. Real trace: pull an actual `events.ndjson` slice with a reask and a resume so Section 8 is a screenshot, not a mock.
3. NLI threshold values (0.60) in Sections 7–8 must match the configured value in the pipeline before publishing.
4. Mascot illustration: needs a hero-scale version (papers in, review out) and a small satisfied version for Section 11.
