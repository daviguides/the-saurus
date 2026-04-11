import { Trash2, FileText } from "lucide-react";
import type { Paper } from "../../core/types/paper";

interface Props {
  paper: Paper;
  selected: boolean;
  onToggle(): void;
  onRemove(): void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function PaperListItem({
  paper,
  selected,
  onToggle,
  onRemove,
}: Props) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-bg transition-colors group">
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        className="w-4 h-4 rounded border-border text-primary accent-primary cursor-pointer"
      />
      <FileText size={18} className="text-text-muted shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary truncate">
          {paper.title}
        </p>
        <p className="text-xs text-text-muted">{formatSize(paper.sizeBytes)}</p>
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="opacity-0 group-hover:opacity-100 p-1 rounded text-text-muted hover:text-red-600 hover:bg-red-50 transition-all"
        aria-label={`Remove ${paper.title}`}
      >
        <Trash2 size={15} />
      </button>
    </div>
  );
}
