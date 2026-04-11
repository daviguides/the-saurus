import {
  FileText,
  Tags,
  Quote,
  GitMerge,
  BookOpen,
  Check,
  Loader2,
  Circle,
} from "lucide-react";
import type { PipelineStageState } from "../../core/types/pipeline";
import { PIPELINE_STAGES } from "../../core/types/pipeline";

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  FileText,
  Tags,
  Quote,
  GitMerge,
  BookOpen,
};

interface Props {
  stage: PipelineStageState;
  lastProcessedTitle?: string;
}

export default function StageItem({ stage, lastProcessedTitle }: Props) {
  const config = PIPELINE_STAGES.find((s) => s.id === stage.id);
  const Icon = config ? ICON_MAP[config.icon] : Circle;
  const label = config?.label ?? stage.id;

  const isRunning = stage.status === "running";
  const isCompleted = stage.status === "completed";
  const isPending = stage.status === "pending";

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-1.5 transition-colors ${
        isRunning ? "bg-surface border border-border" : "bg-transparent"
      }`}
    >
      {/* Status icon */}
      <div className="flex-shrink-0 w-6 flex justify-center">
        {isCompleted && (
          <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
            <Check size={14} className="text-primary" />
          </div>
        )}
        {isRunning && (
          <Loader2 size={20} className="text-primary animate-spin" />
        )}
        {isPending && (
          <Circle size={18} className="text-text-muted/40" />
        )}
        {stage.status === "failed" && (
          <div className="w-6 h-6 rounded-full bg-error/10 flex items-center justify-center">
            <Circle size={14} className="text-error" />
          </div>
        )}
      </div>

      {/* Stage icon */}
      <Icon
        size={16}
        className={isPending ? "text-text-muted/40" : "text-primary"}
      />

      {/* Label + activity */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm font-medium ${
            isPending ? "text-text-muted" : "text-text-primary"
          }`}
        >
          {label}
        </span>
        {isRunning && lastProcessedTitle && (
          <p className="text-xs text-text-secondary truncate mt-0.5">
            ↳ {lastProcessedTitle}
          </p>
        )}
      </div>

      {/* Counter */}
      {stage.totalPapers > 0 && (
        <span
          className={`text-xs font-mono flex-shrink-0 ${
            isPending ? "text-text-muted/40" : "text-text-secondary"
          }`}
        >
          {stage.processedPapers.length}/{stage.totalPapers}
        </span>
      )}
    </div>
  );
}
