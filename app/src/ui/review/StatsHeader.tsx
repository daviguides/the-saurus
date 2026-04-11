import { FileText, Tags, Quote, Clock } from "lucide-react";
import type { ReviewStats } from "../../core/types/review";

interface Props {
  stats: ReviewStats;
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
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-8 py-3 border-b border-border bg-surface">
      <StatChip icon={FileText} label="papers" value={String(stats.paperCount)} />
      <StatChip icon={Tags} label="themes" value={String(stats.themeCount)} />
      <StatChip icon={Quote} label="claims" value={String(stats.claimCount)} />
      <StatChip icon={Clock} label="generation" value={formatDuration(stats.generationTimeMs)} />
    </div>
  );
}
