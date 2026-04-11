import type { EnrichedPaperResponse } from "../services/api";
import type { Paper, Theme, Claim } from "../types/paper";

let colorCounter = 0;
const colorMap = new Map<string, number>();

function getColorIndex(themeId: string): number {
  if (!colorMap.has(themeId)) {
    colorMap.set(themeId, colorCounter++);
  }
  return colorMap.get(themeId)!;
}

export function transformPapers(enrichedPapers: EnrichedPaperResponse[]): Paper[] {
  return enrichedPapers.map((ep) => {
    const themes: Theme[] = (ep.themes ?? []).map((t: Record<string, unknown>) => ({
      id: (t.id as string) ?? "",
      label: (t.name as string) ?? (t.label as string) ?? "",
      colorIndex: getColorIndex((t.id as string) ?? ""),
    }));

    const claims: Claim[] = (ep.claims ?? []).map((c: Record<string, unknown>) => ({
      id: (c.id as string) ?? "",
      text: (c.text as string) ?? "",
      page: (c.page as number) ?? (c.source as Record<string, unknown>)?.page as number ?? 0,
      paragraph: (c.paragraph as number) ?? (c.source as Record<string, unknown>)?.paragraph as number ?? 0,
      themeId: (c.theme_id as string) ?? "",
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
