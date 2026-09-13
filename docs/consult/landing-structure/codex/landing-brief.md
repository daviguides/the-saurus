# The Saurus — Landing Brief

Based on [Vision](../../../foundation/vision.md), [Positioning](../../../foundation/positioning.md), and [Design System](../../../foundation/design-system.md). Positioning governs voice where the documents differ, including keeping the mascot out of errors and verification.

## A: Landing Page Sections

The page has two acts: **a corpus becomes a synthesis**, then **a synthesis becomes something you can inspect and revise**. The product supplies evidence inside that argument. The landing page supplies the pace, scale, and reason to care.

Weights below express relative editorial emphasis and approximate share of page space, including each block’s surrounding whitespace. They total 100%; they are not fixed viewport heights.

### 1. The invitation — 18%

- **Purpose:** Make the product and its input legible immediately, with enough personality to remember its name.
- **Key content:** Primary tagline; scientific PDFs → thematic literature-review draft; paper/page/paragraph provenance; researcher review. Primary action opens the product’s upload entry. Secondary action jumps to the synthesis demonstration.
- **App demo element:** None. A large editorial illustration establishes the input: a dinosaur taking a sheet from a modest stack of papers. The output is named in copy, not represented by an invented screenshot.
- **Background:** Light paper `#FAFAF7`.
- **Typography:** Literata headline at roughly 80–112px on wide screens, 44–56px on mobile; Inter supporting copy at 20–22px. Give the headline room to wrap naturally.
- **Visual treatment:** Asymmetric composition, generous empty margins, minimal scientific line art. Green ink and a restrained gold detail. Quiet navigation rather than an app header. The illustration supports the words without becoming a full-screen cartoon.

### 2. The work between papers — 10%

- **Purpose:** Recognize the researcher’s actual bottleneck: relating findings across an already curated corpus.
- **Key content:** Recurring themes, different terminology, agreement and disagreement, and keeping the source of each claim attached throughout drafting.
- **App demo element:** None. Three large editorial questions, set apart from the paragraph, make the work tangible.
- **Background:** Continue the light paper with no enclosing panel.
- **Typography:** Literata 44–60px lead; Inter 18–20px body; questions in restrained serif text.
- **Visual treatment:** Narrow reading column with a broad unused margin. Leave 160–220px of desktop breathing room after the hero. No pain-point cards, icons, or numerical productivity claims.

### 3. The corpus becomes a synthesis — 20%

- **Purpose:** Demonstrate the central difference: thematic relationships across papers become a connected draft.
- **Key content:** Independent theme and claim extraction; semantic deduplication; review of evidence across the papers contributing to a theme; synthesis with attached citations.
- **App demo element:** One edited demonstration from a real sample run. Show related theme labels from multiple papers, their shared theme after deduplication, and the corresponding review excerpt. Let the visitor inspect contributing papers. Keep distinct source claims visible even when theme labels merge. Choose an example with a meaningful qualification or disagreement if the run contains one.
- **Background:** Light paper; sample review on surface `#F5F5F0` with a fine border.
- **Typography:** Literata 48–64px heading; readable Literata review excerpt at 18–20px; Inter explanation; Fira Code for source locations.
- **Visual treatment:** One generous figure with a caption, not three equally sized feature cards. A few connecting rules explain the relationship between source themes and review text. Remove unrelated navigation and controls from app crops. Show only enough prose to read, never an entire miniature review. On mobile, stack the same evidence in reading order.

### 4. The question at the turn — 5%

- **Purpose:** Shift from the appeal of synthesis to the researcher’s standard of evidence. This is the explicit act break.
- **Key content:** A draft becomes useful when the researcher can examine what supports it.
- **App demo element:** None.
- **Background:** Light paper, ending at a clean boundary before the dark evidence section.
- **Typography:** A single Literata sentence at 48–72px, with one short supporting line.
- **Visual treatment:** An intentional void: roughly 180–240px above and below on desktop, 80–112px on mobile. No decorative transition, feature grid, or animation. This pause belongs to the argument.

### 5. A claim, opened to its source — 20%

- **Purpose:** Demonstrate provenance and explain the scope of grounding verification.
- **Key content:** Claim → cited paper → page → paragraph; source passage beside the claim; NLI entailment check; handling of borderline grounding and invalid citation references.
- **App demo element:** The page’s strongest proof. Continue with a citation from section 3. Selecting it reveals the actual source passage and location, with a separate view of the recorded grounding check. An editorial demonstration may arrange genuine outputs side by side; identify that arrangement as a demonstration rather than implying an existing app layout. Show a real flagged or retried case when available. Never invent a reassuring status.
- **Background:** Warm charcoal `#1A1D1E`; evidence surfaces `#242728`; warm text `#E8E4DD`, green `#5BAB8A`, restrained gold `#E5C349`.
- **Typography:** Literata 48–64px heading and source excerpt; Inter process explanation; Fira Code for paper/page/paragraph addresses and recorded statuses. Metadata remains readable at 14px or larger.
- **Visual treatment:** Large paired claim and passage, like an annotated journal spread. Highlight the relevant passage without turning the whole panel green. Explain status with text, not color alone. No mascot, shields, seal of approval, percentage score, or implied guarantee.

### 6. The method remains visible — 12%

- **Purpose:** Show how the result was produced and what the researcher can inspect when processing needs attention.
- **Key content:** Ingestion, parallel paper analysis, semantic theme deduplication, cross-paper theme review, synthesis; citation checks attached to the work they validate. Real events, retries, skipped inputs, and resumed work remain visible.
- **App demo element:** A short trace excerpt from the same run, with one event expandable to its paper findings. Annotate an actual retry or resumption if the recording contains one. Show the recorded run state honestly; label a replay as a replay.
- **Background:** Return to light paper. This is a new editorial section, not another dark dashboard panel.
- **Typography:** Literata 40–56px lead; Inter stage descriptions; Fira Code event metadata.
- **Visual treatment:** A spare vertical method sequence beside a cropped trace. No full console, token stream, or architecture diagram. The reader should grasp the method before choosing to inspect an event. Only user-triggered expansion and brief opacity/color transitions; respect reduced motion.

### 7. The researcher takes it from here — 9%

- **Purpose:** Make authorship concrete and place the assistant in its supporting role.
- **Key content:** Review and revise the draft, inspect per-paper findings, pursue questions through the retrieval-based assistant, return to cited evidence, export the reviewed text.
- **App demo element:** A small, secondary assistant excerpt answering one question about the sample corpus, with its actual citations. Use a recorded answer from the run. Keep the researcher's question and source link more prominent than chat chrome. Do not make conversation a second product hero.
- **Background:** Light paper with generous open space before the close.
- **Typography:** Literata 48–64px heading; Inter body; Literata draft excerpt if shown; mono citation addresses.
- **Visual treatment:** Text leads. A modest marginal specimen demonstrates exploration. No celebratory completion state or submission imagery. The visual emphasis returns to the researcher’s judgment.

### 8. Feed the next corpus — 6%

- **Purpose:** Invite the now-informed researcher to begin with papers they selected.
- **Key content:** Repeat the upload action and its concrete input. A quiet final brand line gives the dinosaur one last appearance.
- **App demo element:** None; the action opens the actual upload entry, not a decorative landing-page drop zone.
- **Background:** Light surface `#F5F5F0`, separated by a fine rule and open space.
- **Typography:** Literata 56–80px closing line; Inter support and actions; small Inter wordmark/footer.
- **Visual treatment:** One action, one small line-art dinosaur, ample margins. Reuse the hero button label. No last-minute feature list, unsupported trust logos, pricing, or urgency device.

**Shared design and evidence rules**

Use the design system’s families, palette, modest radii, and paper-like surfaces; expand its application typography into a landing-page display scale. Main compositions can reach 1280–1440px, while body prose stays around 55–65 characters per line. Desktop section spacing generally runs 120–200px, reduced to 64–96px on mobile. Do not squeeze away the act break on small screens. Avoid scroll pinning, autoplay walkthroughs, bouncing, and slide-in effects.

Every demonstration must be understandable as a static figure, with an optional inspect/replay action. Present the editorial point before the evidence and its implication after it. Use one coherent sample corpus throughout, cleared for display. Label it “Sample corpus” and label recordings “Recorded sample run.” Scientific excerpts, bibliographic details, claim locations, statuses, and timings must come from that run. Do not author fictional research findings as proof.

This brief specifies the intended page from the foundation documents; it does not certify shipped functionality. Before publishing, confirm the described upload, citation inspection, trace, grounding, assistant, editing, and export behavior in the product. If a mechanism cannot be demonstrated, revise its claim to match the available behavior. Publish no invented answer, fabricated result, benchmark, testimonial, or elapsed-time promise. All authored landing copy is provided in section C; captured research content is evidence to select, not marketing text to fabricate.

## B: Narrative Arc

| Beat | Sections | Reader’s question | Narrative move | Evidence or resolution |
|---|---|---|---|---|
| Hook | 1 | What would I feed it, and what would I get? | Name the input, thematic draft, and human review immediately. | Scientific PDFs in; a cited draft for the researcher to examine. |
| Problem | 2 | Does it address the work I am stuck on? | Describe relating papers, reconciling terminology, and retaining sources. | Familiar tasks and concrete questions, without inflated pain or speed claims. |
| Proof, first movement | 3 | Does it actually synthesize across my corpus? | Follow multiple papers into one theme and its review passage. | Genuine extraction and deduplication outputs beside the resulting synthesis. |
| Turn | 4 | Can I examine the basis of that synthesis? | Pause the demonstration and raise the evidentiary standard. | A typographic question and deliberate empty space. |
| Proof, second movement | 5–6 | Can I trace the claims and inspect the process? | Open one citation, explain its grounding check, then reveal the run that produced it. | Source passage, exact address, recorded check, and actual pipeline events. |
| Conviction | 7 | What remains mine to do? | Put checking, interpretation, revision, and authorship in the researcher’s hands. | A concrete corpus question with cited retrieval, followed by a return to the source. |
| Close | 8 | What is the next step? | Invite a corpus the reader has already curated. | The same upload action introduced in the hero. |

**Act I — From collection to synthesis (1–3).** Start with appetite, then recognize the intellectual work between papers. Demonstrate a corpus-level relationship before showing machinery. The first act earns interest through a useful result the visitor can read.

**Act break (4).** The silence changes the question. A coherent passage alone is insufficient evidence for the decision this audience needs to make.

**Act II — From synthesis to scrutiny and authorship (5–8).** Follow the result backward to its sources and method, then forward into the researcher’s own judgment. The dark evidence spread marks this shift; the return to paper restores the feel of a working research document.

The scroll follows an argument, not the app’s tab order. Upload is an invitation, not a simulated onboarding flow. Synthesis appears before the pipeline explanation because the reader first needs to see what the process is for. Chat arrives late because it supports scrutiny rather than defining the product. Large typography, editorial margins, a deliberate void, and a single dark spread make the page larger in scale and calmer in rhythm than the application.

## C: Real Copy

The following is publishable authored copy. Labels identify placement and are not themselves page text. Research passages and recorded outputs shown in demonstrations must be drawn from the sample run as specified in A.

### 1. The invitation

**Wordmark:** The Saurus

**Navigation:** The synthesis · The evidence · The method

**Navigation action:** Upload your papers

**Eyebrow:** A literature review pipeline

**Headline:** Feed The Saurus your papers.

**Body:** Turn your corpus of scientific PDFs into a literature-review draft organized by theme, with each claim traced to its paper, page, and paragraph. You review the evidence, revise the synthesis, and make the argument your own.

**Primary action:** Upload your papers

**Secondary action:** Inspect a sample synthesis

**Supporting line:** Start with the papers you have already chosen.

**Illustration caption:** A healthy appetite for the literature.

### 2. The work between papers

**Headline:** You have the papers. Now comes the work between them.

**Body:** One paper names a theme differently. Another qualifies a finding. A third disagrees. Building a literature review means following those connections across your corpus—and keeping track of which passage supports which claim.

**Editorial questions:**

- Which themes recur across the papers?
- Where do the findings agree or diverge?
- What passage supports this claim?

**Closing line:** The Saurus organizes that evidence into a draft you can examine and revise.

### 3. The corpus becomes a synthesis

**Eyebrow:** Across the corpus

**Headline:** Follow a theme across your papers.

**Body:** The pipeline extracts themes and claims from each paper independently. Semantic deduplication brings together theme labels that refer to the same concept. Each theme is then reviewed across its contributing papers and woven into a synthesis for you to assess.

**Figure labels:** Sample corpus · Themes extracted from papers · Shared theme · Review draft

**Figure action:** Inspect contributing papers

**Figure caption:** Follow the source themes into a shared theme, then read the corresponding passage in the review draft. The individual claims retain their source references.

**Closing line:** Shared vocabulary does not settle a disagreement. The claims and their sources remain there for you to compare.

### 4. The question at the turn

**Headline:** What supports that sentence?

**Supporting line:** A useful draft gives you somewhere to look.

### 5. A claim, opened to its source

**Eyebrow:** Evidence you can inspect

**Headline:** Every claim has an address.

**Body:** Follow a claim’s citation to the paper, page, and paragraph it references. Read the source passage beside the claim and judge whether it supports the wording in the draft.

**Figure labels:** Claim in the draft · Cited source passage · Paper · Page · Paragraph · Grounding check

**Figure actions:** Open the source passage · Inspect the grounding check

**Figure caption:** The claim and its cited passage, shown together so you can examine the connection.

**Method subheading:** Grounding is checked against the passage.

**Method body:** A natural-language-inference model checks whether the cited passage entails the claim. Borderline results are escalated for further checking. A separate citation guard rejects references to nonexistent claim IDs and requests a correction.

**Limit statement:** The check tests support in a passage. It does not establish that a study is sound or that your corpus covers the field. You still assess the evidence and the draft’s interpretation.

### 6. The method remains visible

**Eyebrow:** An inspectable process

**Headline:** See the stages behind the synthesis.

**Body:** A multi-agent pipeline analyzes papers in parallel, brings related themes together, reviews the evidence within each theme, and assembles the literature-review draft. The trace records the work as it happens and remains available for inspection.

**Stage descriptions:**

1. **Ingest the PDFs.** Convert the uploaded papers into text for analysis.
2. **Extract themes and claims.** Analyze each paper independently and attach source locations to its claims.
3. **Deduplicate themes.** Match theme labels by meaning across the corpus.
4. **Review each theme.** Bring together the claims from papers contributing to that theme.
5. **Assemble the synthesis.** Produce a thematic draft with citations for you to review.

**Check note:** Citation integrity and NLI grounding checks accompany the generated claims and citations.

**Trace label:** Recorded sample run

**Trace action:** Inspect a pipeline event

**Trace caption:** Open an event to inspect the recorded work behind the draft.

**Recovery note:** Retries remain visible in the trace. Skipped papers are reported, and interrupted jobs resume from completed stages.

### 7. The researcher takes it from here

**Headline:** The researcher stays the author.

**Body:** The draft gives you a structure to question. Read the source passages, compare the per-paper findings, and revise the synthesis around your own assessment of the literature. Edit and export the review when you are ready to take it into your writing.

**Assistant subheading:** Keep asking questions of the corpus.

**Assistant body:** The retrieval-based assistant draws on the pipeline outputs to answer questions with citations. Use those references to return to the evidence as you review the draft.

**Sample question:** Which papers contribute to this theme, and what does each claim?

**Assistant action:** Inspect the cited evidence

**Assistant caption:** A question about the sample corpus, with the recorded answer and its source references.

**Closing line:** The Saurus does the digestion. You decide what the literature supports.

### 8. Feed the next corpus

**Headline:** A corpus to digest. An argument to make.

**Body:** Feed The Saurus the scientific PDFs you have collected. Get a thematic draft with the evidence attached, ready for your review.

**Primary action:** Upload your papers

**Supporting line:** Begin with your selected corpus of PDFs.

**Footer wordmark:** The Saurus

**Footer line:** Part thesaurus. Part dinosaur. Here to devour papers.
