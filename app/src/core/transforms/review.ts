import type { EnrichedPaperResponse, RawReview } from "../services/api";
import type { ReviewData, ReviewPaper, ReviewClaim } from "../types/review";

export function transformReview(
  raw: RawReview,
  enrichedPapers: EnrichedPaperResponse[],
): ReviewData {
  // Build paper_id → paper index mapping
  const paperIdToIndex = new Map<string, number>();
  for (let i = 0; i < enrichedPapers.length; i++) {
    paperIdToIndex.set(enrichedPapers[i].paper_id, i + 1);
  }

  // Build ref_number → paper index mapping from citations
  const refToPaperIndex: Record<number, number> = {};
  for (const cit of raw.citations ?? []) {
    const idx = paperIdToIndex.get(cit.paper_id);
    if (idx != null) {
      refToPaperIndex[cit.ref_number] = idx;
    }
  }

  // Build markdown from sections (with abstract if present)
  const parts: string[] = [];
  if (raw.abstract) {
    parts.push(`*${raw.abstract}*`);
  }
  for (const s of raw.sections) {
    parts.push(`## ${s.label}\n\n${s.content}`);
  }
  const markdown = parts.join("\n\n");

  // Build ReviewPaper[] from enriched papers
  const papers: ReviewPaper[] = enrichedPapers.map((ep, i) => {
    const claims: ReviewClaim[] = (ep.claims ?? []).map((c: Record<string, unknown>) => ({
      text: (c.text as string) ?? "",
      page: (c.page as number) ?? (c.source as Record<string, unknown>)?.page as number ?? 0,
      paragraph: (c.paragraph as number) ?? (c.source as Record<string, unknown>)?.paragraph as number ?? 0,
      themeId: (c.theme_id as string) ?? "",
    }));

    // Find which sections cite this paper — prefer citations data, fallback to claim_ids
    let citedIn: string[];
    if (raw.citations && raw.citations.length > 0) {
      // Use citation ref_numbers that point to this paper
      const refsForPaper = new Set(
        raw.citations
          .filter((cit) => cit.paper_id === ep.paper_id)
          .map((cit) => cit.ref_number),
      );
      citedIn = raw.sections
        .filter((s) => (s.citation_refs ?? []).some((ref) => refsForPaper.has(ref)))
        .map((s) => s.label);
    } else {
      // Fallback: match by claim_ids (stub aggregator compat)
      citedIn = raw.sections
        .filter((s) =>
          s.claim_ids.some((cid) =>
            (ep.claims ?? []).some((c: Record<string, unknown>) => c.id === cid),
          ),
        )
        .map((s) => s.label);
    }

    return {
      index: i + 1,
      id: ep.paper_id,
      title: ep.title || ep.filename,
      authors: ep.authors.join(", "),
      year: "",
      journal: "",
      citedIn,
      claims,
    };
  });

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
      generationTimeMs: 0,
    },
    generatedAt: Date.now(),
  };
}
