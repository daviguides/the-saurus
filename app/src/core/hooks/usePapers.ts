import { useState, useCallback, useMemo } from "react";
import type { Paper, ViewState } from "../types/paper";

export function usePapers() {
  const [papers, setPapers] = useState<Paper[]>([]);

  const viewState: ViewState = useMemo(() => {
    if (papers.length === 0) return "empty";
    if (papers.some((p) => p.themes && p.themes.length > 0)) return "complete";
    return "uploaded";
  }, [papers]);

  const loadPapers = useCallback((newPapers: Paper[]) => {
    setPapers(newPapers);
  }, []);

  return {
    papers,
    viewState,
    loadPapers,
  };
}
