import type { EnrichedPaperResponse } from "../services/api";
import type { Paper, Theme, Claim } from "../types/paper";

/** Shape of a theme object in the API response. */
interface ApiTheme {
  id?: string;
  name?: string;
  label?: string;
}

/** Shape of a claim object in the API response. */
interface ApiClaim {
  id?: string;
  text?: string;
  page?: number;
  paragraph?: number;
  theme_id?: string;
  source?: { page?: number; paragraph?: number };
}

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
    const themes: Theme[] = (ep.themes ?? []).map((raw) => {
      const t = raw as ApiTheme;
      return {
        id: t.id ?? "",
        label: t.name ?? t.label ?? "",
        colorIndex: getColorIndex(t.id ?? ""),
      };
    });

    const claims: Claim[] = (ep.claims ?? []).map((raw) => {
      const c = raw as ApiClaim;
      return {
        id: c.id ?? "",
        text: c.text ?? "",
        page: c.page ?? c.source?.page ?? 0,
        paragraph: c.paragraph ?? c.source?.paragraph ?? 0,
        themeId: c.theme_id ?? "",
      };
    });

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
