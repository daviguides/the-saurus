interface Props {
  completed: number;
  total: number;
  startedAt: number | null;
}

function formatElapsed(startedAt: number | null): string {
  if (!startedAt) return "";
  const elapsed = Math.floor((Date.now() - startedAt) / 1000);
  const min = Math.floor(elapsed / 60);
  const sec = elapsed % 60;
  return min > 0 ? `${min}m ${sec}s` : `${sec}s`;
}

export default function ProgressBar({ completed, total, startedAt }: Props) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-primary">
          {completed}/{total} papers processed
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
