import { useSyncExternalStore } from "react";

const STORAGE_KEY = "thesaurus:job_id";

const listeners = new Set<() => void>();

function notifyAll() {
  listeners.forEach((l) => l());
}

// Listen for cross-tab changes
if (typeof window !== "undefined") {
  window.addEventListener("storage", (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) notifyAll();
  });
}

function getSnapshot(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useJobId(): string | null {
  return useSyncExternalStore(subscribe, getSnapshot);
}

export function clearJobId(): void {
  localStorage.removeItem(STORAGE_KEY);
  // Same-tab localStorage changes don't fire StorageEvent,
  // so notify useSyncExternalStore subscribers manually.
  notifyAll();
}
