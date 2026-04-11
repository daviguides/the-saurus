import { useState } from "react";
import {
  FileText,
  Tags,
  Quote,
  GitMerge,
  BookOpen,
  Check,
  Loader2,
  Circle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { PipelineStageState } from "../../core/types/pipeline";
import { PIPELINE_STAGES } from "../../core/types/pipeline";
import PaperSubItem from "./PaperSubItem";

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  FileText,
  Tags,
  Quote,
  GitMerge,
  BookOpen,
};

interface Props {
  stage: PipelineStageState;
  paperTitles: Map<string, string>;
}

export default function StageItem({ stage, paperTitles }: Props) {
  const config = PIPELINE_STAGES.find((s) => s.id === stage.id);
  const Icon = config ? ICON_MAP[config.icon] : Circle;
  const label = config?.label ?? stage.id;

  const isRunning = stage.status === "running";
  const isCompleted = stage.status === "completed";
  const isPending = stage.status === "pending";

  const [expanded, setExpanded] = useState(isRunning);

  // Auto-expand when stage starts running
  if (isRunning && !expanded) setExpanded(true);

  const hasProcessed = stage.processedPapers.length > 0;

  return (
    <div className="border border-border rounded-lg mb-2 overflow-hidden bg-surface">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-bg/50 transition-colors"
      >
        {/* Status icon */}
        <div className="flex-shrink-0">
          {isCompleted && (
            <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
              <Check size={14} className="text-primary" />
            </div>
          )}
          {isRunning && (
            <Loader2 size={20} className="text-primary animate-spin" />
          )}
          {isPending && (
            <Circle size={20} className="text-text-muted" />
          )}
          {stage.status === "failed" && (
            <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center">
              <Circle size={14} className="text-red-500" />
            </div>
          )}
        </div>

        {/* Stage icon + label */}
        <Icon
          size={16}
          className={isPending ? "text-text-muted" : "text-primary"}
        />
        <span
          className={`flex-1 text-sm font-medium ${
            isPending ? "text-text-muted" : "text-text-primary"
          }`}
        >
          {label}
        </span>

        {/* Paper count */}
        {stage.totalPapers > 0 && (
          <span className="text-xs font-mono text-text-secondary">
            {stage.processedPapers.length}/{stage.totalPapers}
          </span>
        )}

        {/* Expand chevron */}
        {hasProcessed && (
          expanded ? (
            <ChevronDown size={14} className="text-text-muted" />
          ) : (
            <ChevronRight size={14} className="text-text-muted" />
          )
        )}
      </button>

      {/* Expanded paper list */}
      {expanded && hasProcessed && (
        <div className="px-4 pb-3 pl-14 border-t border-border/50">
          {stage.processedPapers.map((paperId, i) => (
            <PaperSubItem
              key={paperId}
              title={paperTitles.get(paperId) ?? paperId}
              isLast={i === stage.processedPapers.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
