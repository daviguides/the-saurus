import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Cpu,
  Eye,
  EyeOff,
  FileSearch,
  FileText,
  GitMerge,
  Loader2,
  AlertCircle,
  Quote,
  Tags,
  Zap,
} from "lucide-react";
import type { AgentEvent } from "../../core/types/pipeline";

// --- Constants ---

type ViewMode = "friendly" | "technical";

const AGENT_ICON_MAP: Record<
  string,
  React.ComponentType<{ size?: number; className?: string }>
> = {
  PaperAnalyzer: FileSearch,
  ThemeExtractor: Tags,
  ClaimExtractor: Quote,
  ThemeDedup: GitMerge,
  ThemeReviewer: BookOpen,
  Aggregator: FileText,
};

function getAgentIcon(
  agentName: string,
): React.ComponentType<{ size?: number; className?: string }> {
  return AGENT_ICON_MAP[agentName] ?? Cpu;
}

function formatRelativeTime(timestamp: number, firstTimestamp: number): string {
  const elapsed = (timestamp - firstTimestamp) / 1000;
  if (elapsed < 0.1) return "0.0s";
  if (elapsed < 10) return `${elapsed.toFixed(1)}s`;
  if (elapsed < 60) return `${Math.round(elapsed)}s`;
  const min = Math.floor(elapsed / 60);
  const sec = Math.round(elapsed % 60);
  return `${min}m ${sec}s`;
}

function isEventActive(event: AgentEvent, allEvents: AgentEvent[]): boolean {
  if (event.eventType !== "agent_started") return false;
  const key = `${event.agentName}:${event.paperId ?? ""}`;
  // Check if there's a completing event after this one
  for (let i = allEvents.indexOf(event) + 1; i < allEvents.length; i++) {
    const e = allEvents[i];
    const eKey = `${e.agentName}:${e.paperId ?? ""}`;
    if (eKey === key && (e.eventType === "agent_completed" || e.eventType === "agent_error")) {
      return false;
    }
  }
  return true;
}

// --- OrchestrationStepItem ---

interface StepItemProps {
  event: AgentEvent;
  isLast: boolean;
  mode: ViewMode;
  firstTimestamp: number;
  allEvents: AgentEvent[];
}

function OrchestrationStepItem({
  event,
  isLast,
  mode,
  firstTimestamp,
  allEvents,
}: StepItemProps) {
  const [detailOpen, setDetailOpen] = useState(false);
  const active = isEventActive(event, allEvents);
  const isError = event.eventType === "agent_error";
  const isCompleted =
    event.eventType === "agent_completed" ||
    event.eventType === "agent_tool_result";

  const Icon = getAgentIcon(event.agentName);
  const displayMessage =
    mode === "technical" ? event.technicalMessage : event.humanMessage;

  // Determine if this event has expandable detail
  const hasDetail =
    (event.eventType === "agent_tool_call" && event.toolArgsPreview) ||
    (event.eventType === "agent_tool_result" && event.resultLen > 0) ||
    (event.eventType === "agent_error") ||
    (event.eventType === "agent_started" && mode === "technical" && event.model);

  return (
    <div className="relative pl-6 pb-4 last:pb-0">
      {/* Connecting line */}
      {!isLast && (
        <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border" />
      )}

      {/* Status indicator */}
      <div className="absolute left-0 top-1 w-[22px] h-[22px] rounded-full border border-border bg-surface flex items-center justify-center z-10">
        {isError ? (
          <AlertCircle size={12} className="text-error" />
        ) : isCompleted ? (
          <Check size={12} className="text-success" />
        ) : active ? (
          <Loader2 size={12} className="text-primary animate-spin" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-primary/40" />
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-1">
        {/* Header row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-primary bg-primary-bg px-1.5 py-0.5 rounded border border-border">
            {formatRelativeTime(event.timestamp, firstTimestamp)}
          </span>
          <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <Icon size={12} className="text-primary" />
            {event.agentName}
          </span>
          {event.eventType === "agent_tool_call" && (
            <span className="text-xs font-mono text-accent">
              {event.toolName}
            </span>
          )}
          {event.eventType === "agent_tool_result" && event.elapsedMs != null && (
            <span className="text-xs font-mono text-text-muted">
              {event.elapsedMs}ms
            </span>
          )}
          {event.eventType === "agent_completed" && event.elapsedMs != null && (
            <span className="text-xs font-mono text-text-muted">
              {event.elapsedMs}ms
            </span>
          )}
        </div>

        {/* Message */}
        <p
          className={`text-sm leading-relaxed ${
            isError ? "text-error" : "text-text-primary"
          }`}
        >
          {displayMessage}
        </p>

        {/* Expandable detail */}
        {hasDetail && (
          <button
            type="button"
            onClick={() => setDetailOpen(!detailOpen)}
            className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors mt-0.5 w-fit"
          >
            {detailOpen ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            details
          </button>
        )}
        {hasDetail && detailOpen && (
          <div className="mt-1 bg-bg rounded-md p-2 border border-border text-xs font-mono text-text-secondary overflow-x-auto">
            {event.eventType === "agent_tool_call" && event.toolArgsPreview && (
              <pre className="whitespace-pre-wrap break-all">
                {event.toolArgsPreview}
              </pre>
            )}
            {event.eventType === "agent_tool_result" && (
              <span>
                Result: {event.resultLen} chars
                {event.elapsedMs != null && ` · ${event.elapsedMs}ms`}
              </span>
            )}
            {event.eventType === "agent_error" && (
              <div className="space-y-1">
                <div className="text-error">{event.error}</div>
                {event.errorType && (
                  <div className="text-text-muted">Type: {event.errorType}</div>
                )}
              </div>
            )}
            {event.eventType === "agent_started" && mode === "technical" && event.model && (
              <span>Model: {event.model}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// --- OrchestrationTrace ---

interface OrchestrationTraceProps {
  events: AgentEvent[];
  isActive: boolean;
  mode?: ViewMode;
  onModeChange?: (mode: ViewMode) => void;
}

export default function OrchestrationTrace({
  events,
  isActive,
  mode: controlledMode,
  onModeChange,
}: OrchestrationTraceProps) {
  const [expanded, setExpanded] = useState(false);
  const [internalMode, setInternalMode] = useState<ViewMode>("friendly");
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const mode = controlledMode ?? internalMode;

  function toggleMode() {
    const next = mode === "friendly" ? "technical" : "friendly";
    if (onModeChange) {
      onModeChange(next);
    } else {
      setInternalMode(next);
    }
  }

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  useEffect(() => {
    if (expanded && isAtBottomRef.current && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [events.length, expanded]);

  if (events.length === 0) return null;

  const firstTimestamp = events[0].timestamp;
  const lastEvent = events[events.length - 1];

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface mt-4">
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-bg/50 transition-colors"
      >
        <div className="relative">
          <Zap size={14} className="text-primary" />
          {isActive && (
            <span className="absolute -top-1 -right-1 w-1.5 h-1.5 bg-success rounded-full animate-pulse" />
          )}
        </div>
        <span className="text-sm font-medium text-text-primary flex-1">
          Orchestration Trace
        </span>
        {!expanded && (
          <span className="text-xs text-text-muted truncate max-w-48">
            {isActive
              ? lastEvent.humanMessage
              : `Completed · ${events.length} steps`}
          </span>
        )}
        <span className="text-xs font-mono text-text-muted bg-bg px-1.5 py-0.5 rounded">
          {events.length}
        </span>
        {expanded ? (
          <ChevronDown size={14} className="text-text-muted" />
        ) : (
          <ChevronRight size={14} className="text-text-muted" />
        )}
      </button>

      {/* Expand/collapse via CSS grid */}
      <div
        className="grid transition-[grid-template-rows] duration-200 ease"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden min-h-0">
          {/* Mode toggle */}
          <div className="flex items-center justify-end px-4 py-1.5 border-t border-border bg-bg/30">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleMode();
              }}
              className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
            >
              {mode === "friendly" ? <Eye size={12} /> : <EyeOff size={12} />}
              {mode === "friendly" ? "Technical" : "Friendly"}
            </button>
          </div>

          {/* Timeline */}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="max-h-64 overflow-y-auto px-4 pb-3"
          >
            {events.map((event, index) => (
              <OrchestrationStepItem
                key={event.id}
                event={event}
                isLast={index === events.length - 1}
                mode={mode}
                firstTimestamp={firstTimestamp}
                allEvents={events}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
