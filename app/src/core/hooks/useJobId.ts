import { useSyncExternalStore } from "react";

const STORAGE_KEY = "answerthis:job_id";

function getSnapshot(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

function subscribe(listener: () => void): () => void {
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) listener();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

export function useJobId(): string | null {
  return useSyncExternalStore(subscribe, getSnapshot);
}
