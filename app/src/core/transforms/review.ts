import type { EnrichedPaperResponse, RawReview } from "../services/api";
import type { ReviewData, ReviewPaper, ReviewClaim } from "../types/review";

export function transformReview(
  raw: RawReview,
  enrichedPapers: EnrichedPaperResponse[],
): ReviewData {
  // Build markdown from sections
  const markdown = raw.sections
    .map((s) => `## ${s.label}\n\n${s.content}`)
    .join("\n\n");

  // Build ReviewPaper[] from enriched papers
  const papers: ReviewPaper[] = enrichedPapers.map((ep, i) => {
    const claims: ReviewClaim[] = (ep.claims ?? []).map((c: Record<string, unknown>) => ({
      text: (c.text as string) ?? "",
      page: (c.page as number) ?? (c.source as Record<string, unknown>)?.page as number ?? 0,
      paragraph: (c.paragraph as number) ?? (c.source as Record<string, unknown>)?.paragraph as number ?? 0,
      themeId: (c.theme_id as string) ?? "",
    }));

    // Find which sections cite this paper
    const citedIn = raw.sections
      .filter((s) =>
        s.claim_ids.some((cid) =>
          (ep.claims ?? []).some((c: Record<string, unknown>) => c.id === cid),
        ),
      )
      .map((s) => s.label);

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
    stats: {
      paperCount: enrichedPapers.length,
      themeCount: allThemes.size,
      claimCount,
      generationTimeMs: 0,
    },
    generatedAt: Date.now(),
  };
}
