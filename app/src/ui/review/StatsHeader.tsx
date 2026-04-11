import { useEffect, useRef, useState } from "react";
import { FileText, Tags, Quote, Clock } from "lucide-react";
import type { ReviewStats } from "../../core/types/review";

interface Props {
  stats: ReviewStats;
}

function useCountUp(target: number, durationMs = 600): number {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const start = performance.now();
    function tick(now: number) {
      const t = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      setValue(Math.round(eased * target));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, durationMs]);

  return value;
}

function formatDuration(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

function StatChip({ icon: Icon, label, value }: { icon: typeof FileText; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 text-sm text-text-secondary">
      <Icon size={14} className="text-text-muted" />
      <span className="font-medium text-text-primary">{value}</span>
      <span>{label}</span>
    </div>
  );
}

export default function StatsHeader({ stats }: Props) {
  const papers = useCountUp(stats.paperCount);
  const themes = useCountUp(stats.themeCount);
  const claims = useCountUp(stats.claimCount);
  const genMs = useCountUp(stats.generationTimeMs);

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-8 py-3">
      <StatChip icon={FileText} label="papers" value={String(papers)} />
      <StatChip icon={Tags} label="themes" value={String(themes)} />
      <StatChip icon={Quote} label="claims" value={String(claims)} />
      <StatChip icon={Clock} label="generation" value={formatDuration(genMs)} />
    </div>
  );
}
