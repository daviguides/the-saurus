import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileSearch,
  FileText,
  GitMerge,
  Loader2,
  AlertCircle,
  Play,
  Quote,
  Tags,
  Zap,
} from "lucide-react";
import type { PipelineEvent } from "../../core/types/pipeline";
import { isAgentEvent } from "../../core/types/pipeline";

// --- Constants ---

const STAGE_ICON_MAP: Record<
  string,
  React.ComponentType<{ size?: number; className?: string }>
> = {
  paper_analysis: FileSearch,
  theme_extraction: Tags,
  claim_extraction: Quote,
  theme_dedup: GitMerge,
  theme_review: BookOpen,
  aggregation: FileText,
};

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

function getEventIcon(
  event: PipelineEvent,
): React.ComponentType<{ size?: number; className?: string }> {
  if (isAgentEvent(event)) {
    return AGENT_ICON_MAP[event.agentName] ?? Cpu;
  }
  if (event.stage) {
    return STAGE_ICON_MAP[event.stage] ?? Play;
  }
  return Zap;
}

function getEventColor(event: PipelineEvent): string {
  const et = event.eventType;
  if (et === "job_failed" || et === "agent_error") return "text-error";
  if (et === "job_completed" || et === "agent_completed") return "text-success";
  if (et === "stage_completed" || et === "paper_processed" || et === "paper_analyzed")
    return "text-primary";
  return "text-text-secondary";
}

function isTerminalEvent(event: PipelineEvent): boolean {
  return (
    event.eventType === "job_completed" ||
    event.eventType === "job_failed" ||
    event.eventType === "stage_completed" ||
    event.eventType === "agent_completed" ||
    event.eventType === "agent_error"
  );
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

// --- TraceStepItem ---

interface StepItemProps {
  event: PipelineEvent;
  isLast: boolean;
  firstTimestamp: number;
  isActive: boolean;
}

function TraceStepItem({ event, isLast, firstTimestamp, isActive: active }: StepItemProps) {
  const isError = event.eventType === "job_failed" || event.eventType === "agent_error";
  const isCompleted = isTerminalEvent(event) && !isError;
  const Icon = getEventIcon(event);
  const color = getEventColor(event);

  return (
    <div className="relative pl-6 pb-3 last:pb-0">
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
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-mono text-primary bg-primary-bg px-1.5 py-0.5 rounded border border-border">
          {formatRelativeTime(event.timestamp, firstTimestamp)}
        </span>
        <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
          <Icon size={12} className="text-primary" />
          {event.eventType}
        </span>
        <span className={`text-sm ${color}`}>{event.message}</span>
      </div>
    </div>
  );
}

// --- OrchestrationTrace ---

interface OrchestrationTraceProps {
  events: PipelineEvent[];
  isActive: boolean;
}

export default function OrchestrationTrace({
  events,
  isActive,
}: OrchestrationTraceProps) {
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

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

  // Pre-compute active event set (O(N)) instead of O(N^2) per-item scan
  const activeEventIds = useMemo(() => {
    const ids = new Set<string>();
    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      const et = event.eventType;
      if (et !== "stage_started" && et !== "agent_started" && et !== "job_started") continue;
      const stage = event.stage;
      let hasTerminal = false;
      for (let j = i + 1; j < events.length; j++) {
        if (events[j].stage === stage && isTerminalEvent(events[j])) {
          hasTerminal = true;
          break;
        }
      }
      if (!hasTerminal) ids.add(event.id);
    }
    return ids;
  }, [events]);

  if (events.length === 0) return null;

  const firstTimestamp = events[0].timestamp;
  const lastEvent = events[events.length - 1];

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface mt-4">
      {/* Header */}
      <button
        type="button"
        aria-expanded={expanded}
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
          Event Trace
        </span>
        {!expanded && (
          <span className="text-xs text-text-muted truncate max-w-48">
            {lastEvent.message}
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

      {/* Expandable timeline */}
      <div
        className="grid transition-[grid-template-rows] duration-200 ease"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden min-h-0">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="max-h-64 overflow-y-auto border-t border-border px-4 py-3"
          >
            {events.map((event, index) => (
              <TraceStepItem
                key={event.id}
                event={event}
                isLast={index === events.length - 1}
                firstTimestamp={firstTimestamp}
                isActive={activeEventIds.has(event.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
