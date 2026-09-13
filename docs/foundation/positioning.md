# The Saurus: Positioning

_"Feed The Saurus your papers."_

This document defines who The Saurus is for, what it promises, how it differs from everything adjacent to it, and how it speaks. Every landing page, README, conference slide, and social post should be derivable from what is written here. When a piece of copy contradicts this document, the copy is wrong.

---

## 1. Target Audience

### Primary: the researcher with a folder full of PDFs

A graduate student, postdoc, or early-career researcher who has already done the hard part of collecting 20–100 papers on a topic and now faces the part nobody enjoys: turning that folder into a literature review.

What they have:
- A corpus they curated themselves. They do not need help finding papers.
- A deadline: a thesis chapter, a grant proposal, a related-work section, a systematic review protocol.
- Deep suspicion of AI tools, earned by watching ChatGPT invent a citation.

What they want:
- A first draft of the synthesis that is structured by theme, not by paper.
- Every sentence traceable to a paper, a page, and a paragraph, so they can verify and defend it.
- To see how the result was produced. A black box is unusable in a discipline where method is the argument.

What they fear:
- Fabricated claims. One hallucinated finding in a committee meeting ends the tool's career.
- Losing their own judgment. They want a draft to argue with, not a verdict to accept.

### Secondary: the knowledge worker who reviews technical literature at scale

Research analysts in pharma and biotech, policy researchers, patent analysts, evidence-synthesis teams, and R&D scouting groups. They run the same synthesis loop the academic does, but more often, on more corpora, and with a stronger need for auditability. For them, the pipeline trace and citation granularity are compliance features, not conveniences.

### Not the audience

- Someone with one paper who wants a summary. Any PDF chatbot does this.
- Someone who has not yet chosen their papers. That is discovery, and Semantic Scholar and Elicit are better at it.
- Someone who wants a tool to write their paper for them. The Saurus produces a review of the literature; it does not produce the researcher's contribution.

---

## 2. Value Proposition

### The promise, in one sentence

**The Saurus turns a corpus of papers into a citation-backed literature review, and shows you exactly how it did it.**

### Expanded

A literature review is not a stack of summaries. It is a map: which themes recur, which papers agree, where they disagree, and what evidence supports each position. Building that map by hand means reading every paper, holding every claim in your head, and then writing prose that weaves them together with citations you can defend.

The Saurus does the mapping. It reads each paper in parallel, extracts themes and claims, recognizes when two papers call the same concept by different names, reviews each theme across the corpus, and writes a cohesive synthesis where every claim carries a citation resolved to paper, page, and paragraph. Grounding is verified mechanically, not by trust: a natural-language-inference model checks that each cited claim is actually entailed by the cited passage, and anything borderline is escalated rather than waved through.

Then it hands the researcher the review, the per-paper findings, the full trace of every pipeline stage, and an assistant that can answer questions about the corpus with the same citation discipline.

The researcher stays the author. The Saurus does the digestion.

### What this replaces

Days or weeks of note-taking, spreadsheet-building, and first-draft writing, compressed to minutes, without giving up the ability to check every sentence.

---

## 3. Competitive Positioning

The Saurus does not compete on "finding papers" or "chatting with a PDF." It competes on the step after those: corpus-level synthesis with verifiable provenance. Each category below is a tool the target audience already knows. The job of positioning is to make the boundary unmistakable.

### Discovery and search: Semantic Scholar, Research Rabbit, Elicit (search mode)

**What they do well:** Find papers, map citation graphs, surface related work. Indispensable for building a corpus.

**Where they stop:** At the corpus. They tell you what to read. They do not read it for you, and they do not write the synthesis.

**The Saurus's position:** Downstream. Use them to assemble the folder, then feed the folder to The Saurus. There is no overlap and no reason to frame this as a rivalry. In copy, name them as the step before, not the alternative.

### Claim extraction: Consensus, Elicit (extraction mode)

**What they do well:** Pull structured answers or claims from individual papers. Answer "what does the literature say about X?" with a list of per-paper findings.

**Where they stop:** At the list. Claims are extracted per paper and displayed side by side. Nothing deduplicates themes across papers, nothing reconciles vocabulary ("circadian" vs. "chronobiological"), and nothing writes the review.

**The Saurus's position:** Extraction is stage one of four. The semantic dedup stage and the aggregation stage are precisely what these tools lack. The differentiator is *synthesis*: a coherent, thematically structured text with inline citations, not a table of claims.

### General-purpose LLMs with file upload: ChatGPT, Claude, Gemini

**What they do well:** Flexible, conversational, cheap, and already open in the researcher's browser. Good enough for "summarize this one paper."

**Where they stop:**
- No pipeline. A single prompt over a context window is not a process the researcher can inspect, resume, or reproduce.
- No citation granularity. At best a paper title; never page and paragraph.
- No grounding verification. The model asserts; nobody checks. Fabricated citations are a known and documented failure mode.
- Context limits. Forty PDFs do not fit, and even when they do, attention degrades across the middle of the corpus.

**The Saurus's position:** This is the most important contrast, because it is the tool the audience will actually reach for first. The differentiators are concrete and demonstrable:
1. **Stage-by-stage trace.** The user watches paper analysis, dedup, theme review, and aggregation happen, with events per agent. Nothing is hidden.
2. **Page-and-paragraph citations.** Every claim resolves to a location the researcher can open and read.
3. **Mechanical grounding checks.** An NLI cross-encoder verifies entailment between claim and source; a guard enforces that every citation resolves to a real claim ID. Failures trigger a reask, not a shrug.
4. **Parallel, durable processing.** Each paper is analyzed independently; the job survives crashes and resumes from the last completed stage.

Say this plainly: a chatbot gives you an answer; The Saurus gives you a review and the receipts.

### Writing assistants: SciSpace, Jenni AI

**What they do well:** Help a researcher write prose faster: autocomplete, rephrasing, inline citation lookup.

**Where they stop:** They assist the writing of *the researcher's* argument, one sentence at a time. They do not process a corpus, extract themes, or produce a structured synthesis.

**The Saurus's position:** Orthogonal. A researcher might run The Saurus to produce the literature review draft, then use a writing assistant to polish their own contribution section. No conflict; different stage of the workflow.

### The manual literature review

**What it does well:** Everything. The researcher reads every paper, understands every nuance, and produces exactly the synthesis they intend. It is the gold standard.

**Where it stops:** Time. Days to weeks per review. Most researchers do it less often and less thoroughly than they should because of the cost.

**The Saurus's position:** Not a replacement for reading. A replacement for the *bookkeeping* of reading: tracking which paper said what about which theme, reconciling vocabulary, and producing a first draft with the citations already in place. The researcher still reads; they read with a map instead of a blank page.

### Positioning summary

| Category | They give you | The Saurus gives you |
|---|---|---|
| Discovery (Semantic Scholar, Research Rabbit) | Papers to read | Synthesis of papers you already have |
| Extraction (Consensus, Elicit) | Claims per paper, side by side | Themes deduplicated across papers, written into a review |
| General LLMs (ChatGPT, Claude) | An answer, unverified | A review, traced to page and paragraph, grounding-checked |
| Writing assistants (SciSpace, Jenni) | Faster prose for your argument | The literature-review draft your argument sits on |
| Manual review | Total control, days of work | Same control, minutes of bookkeeping |

---

## 4. Messaging Pillars

Every piece of communication should carry at least one of these. Long-form pieces should carry all four.

### Pillar 1: Synthesis, not summary

The Saurus operates on a corpus, not a document. Its output is organized by theme, not by paper. This is the single most important thing to communicate, because it is the thing every adjacent tool does not do.

*Proof points:* semantic theme deduplication across papers; theme review stage that reads each theme against every paper that touches it; aggregation into cohesive prose.

### Pillar 2: Every claim has an address

Citations resolve to paper, page, and paragraph. Grounding is verified by a model whose only job is to check entailment, and citation integrity is enforced by a guard that rejects references to claims that do not exist.

*Proof points:* NLI cross-encoder verification; citation guard with reask; per-claim source location in the review UI.

### Pillar 3: You can watch it think

The pipeline is transparent by design. Every stage, every agent, every event is visible in real time. The researcher can see what was extracted from which paper before the review is written, and can inspect the trace afterward.

*Proof points:* real-time pipeline trace UI; per-paper findings browser; durable execution that shows resumed stages honestly.

### Pillar 4: The researcher stays the author

The Saurus produces a draft and the evidence behind it. It does not produce conclusions, does not rank papers by importance, and does not claim to have understood the field. The researcher's judgment is the final stage of the pipeline, and it is the only one that is not automated.

*Proof points:* review is editable and exportable; assistant answers questions rather than issuing verdicts; nothing in the UI suggests "done, submit this."

---

## 5. Tone & Voice

### The short version

An academic colleague with a sense of humor. Precise about method, relaxed about everything else. Never breathless.

### Voice attributes

**Academic, not corporate.** The reader is used to journal prose and lab-meeting banter, not SaaS landing pages. Prefer complete sentences over fragments. Prefer "the pipeline extracts themes" over "AI-powered theme extraction." Avoid exclamation marks in body copy; one per landing page, maximum, and only if it earns it.

**Precise about process.** When describing what the tool does, say what it actually does. "Deduplicates themes semantically" is better than "understands your research." "Verifies grounding with an NLI model" is better than "ensures accuracy." Specificity is trust with this audience.

**Playful at the edges.** The dinosaur is real and should be used. The Saurus *devours* papers, *digests* a corpus, gets *fed*. This vocabulary belongs in headlines, empty states, loading messages, and the mascot. It does not belong in the description of the citation guard. The rule: the dinosaur is allowed to be funny; the pipeline is not.

**Honest about limits.** The Saurus produces a draft. It says so. Copy that mentions output should mention that the researcher reviews it. Copy that mentions accuracy should mention how it is checked, not assert that it is achieved.

**Warm, not cute.** The visual identity is a research notebook: paper tones, serif headings, green and gold. The voice matches: it sounds like a well-organized colleague, not a cartoon. The dinosaur is a mascot, not a personality that narrates the interface.

### Register by context

| Context | Register | Example |
|---|---|---|
| Landing page hero | Confident, short, dinosaur permitted | "Feed The Saurus your papers." |
| Feature description | Precise, procedural, no mascot | "Each paper is analyzed independently; themes are then matched across the corpus by semantic similarity." |
| Empty states, loading | Playful, brief | "The Saurus is hungry. Drop some PDFs." |
| Error messages | Plain, useful, no jokes | "Paper 7 could not be parsed. The review continues without it." |
| Academic conference | Formal, method-forward | "A multi-agent pipeline for corpus-level literature synthesis with verified citation grounding." |
| Social | Direct, one idea per post, dinosaur welcome | "40 papers in. One literature review out. Every claim traced to a paragraph." |

### Words we use

devour, digest, feed, corpus, synthesis, theme, claim, trace, grounded, resolve (a citation), stage, pipeline, review, verify, source

### Words we avoid

magic, revolutionary, effortless, instant, understand (as in "AI that understands"), intelligent, smart, powered by AI, unlock, supercharge, 10x, game-changing

---

## 6. Taglines & Headlines

### Primary tagline

**Feed The Saurus your papers.**

Short, imperative, owns the name, implies the whole product loop (input in, digestion happens, something comes out). Use it as the hero line and as the sign-off in long-form pieces.

### Alternative headlines by context

**Landing page (sub-hero, expanding the tagline)**
- From a folder of PDFs to a literature review, with every claim traced to its page.
- It reads the corpus. You keep the judgment.

**Landing page (feature section leads)**
- Synthesis by theme, not summary by paper.
- Every citation has an address.
- Watch every stage. Nothing is hidden.

**Social**
- 40 papers in. One review out. Every claim traced to a paragraph.
- A chatbot gives you an answer. The Saurus gives you the receipts.
- Literature reviews take weeks because of bookkeeping, not reading. We automated the bookkeeping.

**Academic conference / poster**
- Corpus-level literature synthesis with verified citation grounding.
- Multi-agent theme extraction, semantic deduplication, and grounded review generation over scientific corpora.

**Developer / README**
- A durable, multi-agent pipeline that turns PDFs into a citation-backed literature review.

**Mascot / brand moments**
- Hungry for papers since the Cretaceous.
- Part thesaurus. Part dinosaur. All appetite.

---

## 7. What We Don't Say

These are not stylistic preferences. Each one, if violated, damages trust with the exact audience The Saurus depends on.

### No "AI magic"

Never describe the pipeline as magic, effortless, or instant. Never use "AI-powered" as a feature. The audience has a working model of what language models do and do not do; vague enthusiasm reads as either ignorance or evasion. Describe the stages. Name the models where it matters. Let the method be the pitch.

### No "replaces the researcher"

Never imply that The Saurus writes your literature review, finishes your thesis chapter, or removes the need to read. The output is a draft with evidence attached. The researcher reviews, edits, argues with, and owns it. Copy that suggests otherwise is both false and offensive to the reader.

### No accuracy promises

Never say "accurate," "hallucination-free," "guaranteed," or "trustworthy" as bare claims. Say what is checked and how: NLI-verified grounding, citation guards with reask, borderline cases escalated. The Saurus reduces fabrication risk by mechanism, and the mechanism is the message. An unqualified accuracy claim will be tested by the first skeptical reader and will fail on the first edge case.

### No competitor bashing

Do not say Elicit is bad or ChatGPT is dangerous. Say what each does well and where The Saurus begins. The audience uses those tools daily and will keep using them. Positioning by contrast is fine; positioning by contempt is not.

### No dashboard language

Never "leverage," "unlock insights," "supercharge your workflow," or "10x your research." The visual identity is a research notebook, and the voice should never sound like the SaaS dashboard the design deliberately avoided.

### No dinosaur in the serious parts

The mascot does not appear in error messages, in the description of grounding verification, in the citation UI, or in conference materials. When the reader needs to trust the tool, the dinosaur steps aside.

### No hidden stages

Never describe the pipeline in a way that implies it is simpler than it is. If a stage failed and was retried, the trace shows it. If a paper was skipped, the review says so. Transparency is a pillar, and copy that smooths over the process contradicts the product.

---

## Appendix: One-paragraph boilerplate

For use in READMEs, about pages, and anywhere a compact description is needed.

> The Saurus is a literature review pipeline. Upload a corpus of scientific PDFs and a multi-agent pipeline analyzes each paper in parallel, extracts themes and claims, deduplicates themes semantically across the corpus, and writes a cohesive literature review where every claim is cited to paper, page, and paragraph. Citation grounding is verified mechanically, and every pipeline stage is visible in real time. The Saurus produces the draft and the evidence; the researcher keeps the judgment. Part thesaurus, part dinosaur. Feed it your papers.
