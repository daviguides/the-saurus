import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";

interface AssistantState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

const AssistantContext = createContext<AssistantState | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  return (
    <AssistantContext value={{ isOpen, toggle, open, close }}>
      {children}
    </AssistantContext>
  );
}

export function useAssistant(): AssistantState {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used within AssistantProvider");
  return ctx;
}
