import { useState, useCallback, useMemo } from "react";
import type { Paper, ViewState } from "../types/paper";

function extractMetadata(file: File): Paper {
  const title = file.name.replace(/\.pdf$/i, "").replace(/[-_]/g, " ");
  return {
    id: crypto.randomUUID(),
    title,
    fileName: file.name,
    sizeBytes: file.size,
    addedAt: Date.now(),
  };
}

export function usePapers() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const viewState: ViewState = useMemo(() => {
    if (papers.length === 0) return "empty";
    if (papers.some((p) => p.themes && p.themes.length > 0)) return "complete";
    return "uploaded";
  }, [papers]);

  const addPapers = useCallback((files: File[]) => {
    const pdfs = files.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (pdfs.length === 0) return;
    const newPapers = pdfs.map(extractMetadata);
    setPapers((prev) => [...prev, ...newPapers]);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      newPapers.forEach((p) => next.add(p.id));
      return next;
    });
  }, []);

  const removePaper = useCallback((id: string) => {
    setPapers((prev) => prev.filter((p) => p.id !== id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(papers.map((p) => p.id)));
  }, [papers]);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const loadPapers = useCallback((newPapers: Paper[]) => {
    setPapers(newPapers);
  }, []);

  return {
    papers,
    viewState,
    selectedIds,
    addPapers,
    removePaper,
    toggleSelect,
    selectAll,
    deselectAll,
    loadPapers,
  };
}
