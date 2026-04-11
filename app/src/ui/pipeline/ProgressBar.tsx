import type { PipelineStageState } from "../../core/types/pipeline";

interface Props {
  stages: PipelineStageState[];
  startedAt: number | null;
  totalPapers: number;
}

function formatElapsed(startedAt: number | null): string {
  if (!startedAt) return "";
  const elapsed = Math.floor((Date.now() - startedAt) / 1000);
  const min = Math.floor(elapsed / 60);
  const sec = elapsed % 60;
  return min > 0 ? `${min}m ${sec}s` : `${sec}s`;
}

export default function ProgressBar({ stages, startedAt, totalPapers }: Props) {
  const completedStages = stages.filter((s) => s.status === "completed").length;
  const activeStage = stages.find((s) => s.status === "running");

  // Weight: each stage contributes equally. Within a stage, paper progress is fractional.
  const stageWeight = 1 / stages.length;
  let progress = completedStages * stageWeight;
  if (activeStage && activeStage.totalPapers > 0) {
    progress += (activeStage.processedPapers.length / activeStage.totalPapers) * stageWeight;
  }
  const pct = Math.round(progress * 100);

  const activeLabel = activeStage
    ? `${stages.findIndex((s) => s.id === activeStage.id) + 1}/${stages.length} stages`
    : `${completedStages}/${stages.length} stages`;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-primary">
          {activeLabel} · {totalPapers} papers
        </span>
        <span className="text-sm text-text-secondary font-mono">
          {pct}% {startedAt && `· ${formatElapsed(startedAt)}`}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-border overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(to right, var(--color-primary), var(--color-accent))",
          }}
        />
      </div>
    </div>
  );
}
