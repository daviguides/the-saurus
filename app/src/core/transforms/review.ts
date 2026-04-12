import type { EnrichedPaperResponse, RawReview } from "../services/api";
import type { ReviewData, ReviewPaper, ReviewClaim } from "../types/review";

export function transformReview(
  raw: RawReview,
  enrichedPapers: EnrichedPaperResponse[],
): ReviewData {
  // Build paper_id → enriched paper lookup
  const paperById = new Map<string, EnrichedPaperResponse>();
  for (const ep of enrichedPapers) {
    paperById.set(ep.paper_id, ep);
  }

  // Build ref_number → paper index mapping from citations
  // Each citation [N] maps to a claim, which maps to a paper
  const refToPaperIndex: Record<number, number> = {};

  // Build ReviewPaper[] from citations — one entry per citation ref_number
  // This shows each cited claim as a separate reference entry
  const papers: ReviewPaper[] = [];
  const citations = raw.citations ?? [];

  // Also build claim lookup from enriched papers
  const claimById = new Map<string, Record<string, unknown>>();
  for (const ep of enrichedPapers) {
    for (const c of ep.claims ?? []) {
      const id = c.id as string;
      if (id) claimById.set(id, c);
    }
  }

  for (const cit of citations) {
    const ep = paperById.get(cit.paper_id);
    const claim = claimById.get(cit.claim_id);
    const claimText = (claim?.summary as string) ?? (claim?.text as string) ?? "";
    const page = cit.page ?? (claim?.source as Record<string, unknown>)?.page as number ?? 0;
    const paragraph = cit.paragraph ?? (claim?.source as Record<string, unknown>)?.paragraph as number ?? 0;

    // Find which sections reference this citation
    const citedIn = raw.sections
      .filter((s) => (s.citation_refs ?? []).includes(cit.ref_number))
      .map((s) => s.label);

    papers.push({
      index: cit.ref_number,
      id: cit.claim_id,
      title: ep?.title ?? cit.paper_title ?? ep?.filename ?? "Unknown paper",
      authors: ep?.authors?.join(", ") ?? "",
      year: "",
      journal: page > 0 ? `p.${page}, §${paragraph}` : "",
      citedIn,
      claims: claimText
        ? [{ text: claimText, page, paragraph, themeId: "" }]
        : [],
    });

    refToPaperIndex[cit.ref_number] = cit.ref_number;
  }

  // If no citations from aggregator, fall back to paper-level references
  if (papers.length === 0 && raw.references) {
    for (let i = 0; i < raw.references.length; i++) {
      const ref = raw.references[i];
      const ep = paperById.get(ref.paper_id);
      const citedIn = (ref.cited_in ?? []).flatMap((ci) => {
        return raw.sections
          .filter((s) => (s.citation_refs ?? []).includes(ci.ref_number))
          .map((s) => s.label);
      });

      papers.push({
        index: i + 1,
        id: ref.paper_id,
        title: ref.paper_title ?? ep?.title ?? "Unknown",
        authors: ref.authors?.join(", ") ?? ep?.authors?.join(", ") ?? "",
        year: "",
        journal: "",
        citedIn: [...new Set(citedIn)],
        claims: [],
      });
    }
  }

  // Build markdown from sections
  const parts: string[] = [];
  if (raw.abstract) {
    parts.push(`*${raw.abstract}*`);
  }
  for (const s of raw.sections) {
    parts.push(`## ${s.label}\n\n${s.content}`);
  }
  const markdown = parts.join("\n\n");

  // Compute stats
  const allThemes = new Set<string>();
  let claimCount = 0;
  for (const ep of enrichedPapers) {
    for (const t of ep.themes ?? []) {
      allThemes.add((t as Record<string, unknown>).id as string);
    }
    claimCount += (ep.claims ?? []).length;
  }

  return {
    markdown,
    papers,
    refToPaperIndex,
    stats: {
      paperCount: enrichedPapers.length,
      themeCount: allThemes.size,
      claimCount,
      // TODO: compute from actual pipeline elapsed time when available
      generationTimeMs: 0,
    },
    generatedAt: Date.now(),
  };
}
