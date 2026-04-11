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
  const isFailed = stage.status === "failed";

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-1.5 transition-all duration-200 ease ${
        isRunning
          ? "bg-surface border border-border shadow-sm"
          : "bg-transparent border border-transparent shadow-none"
      }`}
    >
      {/* Status icon — all variants always rendered, toggled via opacity/scale */}
      <div className="relative flex-shrink-0 w-6 h-6 flex items-center justify-center">
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ease ${
            isCompleted ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
        >
          <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
            <Check size={14} className="text-primary" />
          </div>
        </div>
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ease ${
            isRunning ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
        >
          <Loader2 size={20} className="text-primary animate-spin" />
        </div>
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ease ${
            isPending ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
        >
          <Circle size={18} className="text-text-muted/40" />
        </div>
        <div
          className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ease ${
            isFailed ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
        >
          <div className="w-6 h-6 rounded-full bg-error/10 flex items-center justify-center">
            <Circle size={14} className="text-error" />
          </div>
        </div>
      </div>

      {/* Stage icon */}
      <Icon
        size={16}
        className={`transition-colors duration-200 ${isPending ? "text-text-muted/40" : "text-primary"}`}
      />

      {/* Label + activity */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm font-medium transition-colors duration-200 ${
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

      {/* Counter with tick animation on change */}
      {stage.totalPapers > 0 && (
        <span
          key={stage.processedPapers.length}
          className={`text-xs font-mono flex-shrink-0 animate-[tick_200ms_ease] ${
            isPending ? "text-text-muted/40" : "text-text-secondary"
          }`}
        >
          {stage.processedPapers.length}/{stage.totalPapers}
        </span>
      )}
    </div>
  );
}
