import { useState, useCallback, useSyncExternalStore } from "react";
import type { ReviewData } from "../types/review";
import { fetchReview, fetchEnrichedPapers } from "../services/api";
import { transformReview } from "../transforms/review";

let reviewData: ReviewData | null = null;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return reviewData;
}

export function useReview() {
  const review = useSyncExternalStore(subscribe, getSnapshot);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReview = useCallback((data: ReviewData) => {
    reviewData = data;
    notify();
  }, []);

  const clearReview = useCallback(() => {
    reviewData = null;
    notify();
  }, []);

  const fetchAndLoad = useCallback(
    async (jobId: string) => {
      setLoading(true);
      setError(null);
      try {
        const [rawReview, enrichedPapers] = await Promise.all([
          fetchReview(jobId),
          fetchEnrichedPapers(jobId),
        ]);
        const data = transformReview(rawReview, enrichedPapers);
        loadReview(data);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load review";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [loadReview],
  );

  return {
    review,
    hasReview: review !== null,
    loading,
    error,
    loadReview,
    clearReview,
    fetchAndLoad,
  };
}
