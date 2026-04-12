import type { EnrichedPaperResponse } from "../services/api";
import type { Paper, Theme, Claim } from "../types/paper";

export function transformPapers(enrichedPapers: EnrichedPaperResponse[]): Paper[] {
  // Scoped color assignment — reset on each call
  let colorCounter = 0;
  const colorMap = new Map<string, number>();

  function getColorIndex(themeId: string): number {
    if (!colorMap.has(themeId)) {
      colorMap.set(themeId, colorCounter++);
    }
    return colorMap.get(themeId)!;
  }

  return enrichedPapers.map((ep) => {
    const themes: Theme[] = (ep.themes ?? []).map((t) => ({
      id: t.id ?? "",
      label: t.name ?? "",
      colorIndex: getColorIndex(t.id ?? ""),
    }));

    const claims: Claim[] = (ep.claims ?? []).map((c) => ({
      id: c.id ?? "",
      text: c.text ?? "",
      page: c.page ?? 0,
      paragraph: c.paragraph ?? 0,
      themeId: c.theme_id ?? "",
    }));

    return {
      id: ep.paper_id,
      title: ep.title || ep.filename,
      fileName: ep.filename,
      sizeBytes: 0,
      addedAt: Date.now(),
      themes,
      claims,
    };
  });
}
