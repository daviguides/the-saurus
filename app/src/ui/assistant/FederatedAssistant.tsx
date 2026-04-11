import React, { Component, Suspense } from "react";
import type { ReactNode, ErrorInfo } from "react";
import { X } from "lucide-react";
import clsx from "clsx";
import { useAssistant } from "../../core/context/AssistantContext";
import { useTheme } from "../../core/hooks/useTheme";

const EmbeddedApp = React.lazy(
  () => import("theSaurusAssistant/EmbeddedApp"),
);

// --- Error Boundary ---

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: (props: { resetErrorBoundary: () => void }) => ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class AssistantErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[FederatedAssistant] Remote load failed:", error, info);
  }

  reset = () => this.setState({ hasError: false });

  render() {
    if (this.state.hasError) {
      return this.props.fallback({ resetErrorBoundary: this.reset });
    }
    return this.props.children;
  }
}

// --- Fallback UIs ---

function LoadingSkeleton() {
  return (
    <div className="flex-1 flex flex-col px-4 py-6 gap-4 animate-pulse">
      <div className="h-4 w-3/4 bg-border rounded" />
      <div className="h-4 w-1/2 bg-border rounded" />
      <div className="h-20 w-full bg-border rounded-xl" />
      <div className="h-4 w-2/3 bg-border rounded" />
      <div className="h-20 w-full bg-border rounded-xl" />
      <div className="flex-1" />
      <div className="h-10 w-full bg-border rounded-xl" />
    </div>
  );
}

function ErrorFallback({
  resetErrorBoundary,
}: {
  resetErrorBoundary: () => void;
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-12 h-12 rounded-full bg-error/10 flex items-center justify-center mb-3">
        <X size={24} className="text-error" />
      </div>
      <h3 className="text-sm font-semibold text-text-primary mb-1">
        Assistant unavailable
      </h3>
      <p className="text-xs text-text-muted mb-4 max-w-[220px]">
        The assistant module couldn&apos;t be loaded. It may not be running.
      </p>
      <button
        type="button"
        onClick={resetErrorBoundary}
        className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

// --- Main Component ---

export default function FederatedAssistant() {
  const { isOpen, close } = useAssistant();
  const { theme } = useTheme();
  const isDark = theme === "dark";

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={close}
        />
      )}

      {/* Drawer panel */}
      <aside
        className={clsx(
          "fixed top-0 right-0 h-full z-40 flex flex-col bg-surface border-l border-border",
          "w-[85vw] max-w-[var(--drawer-width)] lg:w-[var(--drawer-width)]",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Drawer header */}
        <div
          className="flex items-center justify-between px-4 border-b border-border shrink-0"
          style={{ height: "var(--header-height)" }}
        >
          <h2 className="text-sm font-semibold text-text-primary">
            Assistant
          </h2>
          <button
            type="button"
            onClick={close}
            className="flex items-center justify-center w-7 h-7 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg transition-colors duration-200"
          >
            <X size={16} />
          </button>
        </div>

        {/* Federated content */}
        <AssistantErrorBoundary fallback={ErrorFallback}>
          <Suspense fallback={<LoadingSkeleton />}>
            <EmbeddedApp isOpen={isOpen} isDark={isDark} onClose={close} />
          </Suspense>
        </AssistantErrorBoundary>
      </aside>
    </>
  );
}
