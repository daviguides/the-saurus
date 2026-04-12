import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";

const STORAGE_KEY = "thesaurus:theme";

const listeners = new Set<() => void>();

function emitChange() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function getServerSnapshot(): Theme {
  return "dark";
}

function toggle() {
  const next = document.documentElement.classList.toggle("dark")
    ? "dark"
    : "light";
  localStorage.setItem(STORAGE_KEY, next);
  emitChange();
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return { theme, toggle } as const;
}
