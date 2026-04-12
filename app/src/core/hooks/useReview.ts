import { useCallback, useSyncExternalStore } from "react";
import type { ReviewData } from "../types/review";
import { fetchReview, fetchEnrichedPapers } from "../services/api";
import { transformReview } from "../transforms/review";

// Shared store so all consumers see the same loading/error/data state
interface ReviewStore {
  data: ReviewData | null;
  loading: boolean;
  error: string | null;
}

let store: ReviewStore = { data: null, loading: false, error: null };
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return store;
}

export function useReview() {
  const { data: review, loading, error } = useSyncExternalStore(subscribe, getSnapshot);

  const loadReview = useCallback((data: ReviewData) => {
    store = { ...store, data, loading: false, error: null };
    notify();
  }, []);

  const clearReview = useCallback(() => {
    store = { data: null, loading: false, error: null };
    notify();
  }, []);

  const fetchAndLoad = useCallback(
    async (jobId: string) => {
      store = { ...store, loading: true, error: null };
      notify();
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
        store = { ...store, loading: false, error: message };
        notify();
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
