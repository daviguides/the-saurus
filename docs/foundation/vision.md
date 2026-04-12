# The Saurus: Vision

_"Feed The Saurus your papers"_

---

## What It Is

The Saurus is a literature review pipeline that devours scientific papers and produces comprehensive, citation-backed reviews. Upload a corpus of PDFs, watch the pipeline process them in parallel, and get a structured literature review with thematic analysis and traceable citations.

## The Name

A thesaurus connects words that mean the same thing. This pipeline connects themes, claims, and papers that relate to each other. The core challenge of theme deduplication across scientific papers (how "chronobiology" and "chronos" refer to the same concept) is essentially what a thesaurus does.

**The Saurus**: part thesaurus, part dinosaur. It devours papers and synthesizes knowledge.

## The Problem It Solves

Researchers accumulate papers. 20, 40, 100 PDFs on a topic. The painful part isn't finding them — it's synthesizing them into a coherent literature review:

- Read each paper, identify themes
- Track which papers say what about each theme
- Find consensus and disagreements across papers
- Trace every claim back to its source (page, paragraph)
- Write a cohesive text that weaves it all together

This is hours or days of manual work. The Saurus compresses it to minutes.

## How It Works

1. **Feed** — Upload PDFs. The Saurus accepts your corpus.
2. **Process** — Pipeline runs in parallel. Each paper analyzed independently (stateless). Themes extracted, claims mapped, duplicates resolved semantically.
3. **Review** — Comprehensive literature review with inline citations. Every claim traceable to source paper, page, and paragraph.
4. **Explore** — Browse per-paper findings (themes, claims). Ask the assistant about any aspect of the corpus.

## What It Is NOT

- Not a paper search engine
- Not a chatbot that answers questions about one paper
- Not a summarizer that condenses a single document

It is a **pipeline processor** that takes a corpus and produces a structured, citation-backed synthesis.

## Design Goals

Designed as a full-stack demonstration of:
- Multi-agent pipeline architecture with parallel processing
- Real-time pipeline tracing (UI shows each stage)
- Citation tracking with source-level granularity
- Async job recovery (resume where you left off)
- RAG-powered assistant over pipeline outputs
