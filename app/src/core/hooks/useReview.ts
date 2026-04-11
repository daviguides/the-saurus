import { useState, useCallback, useSyncExternalStore } from "react";
import type { ReviewData } from "../types/review";

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

  const loadReview = useCallback((data: ReviewData) => {
    reviewData = data;
    notify();
  }, []);

  const clearReview = useCallback(() => {
    reviewData = null;
    notify();
  }, []);

  return {
    review,
    hasReview: review !== null,
    loadReview,
    clearReview,
  };
}
