import { Plus } from "lucide-react";
import type { Paper } from "../../core/types/paper";
import PaperListItem from "./PaperListItem";

interface Props {
  papers: Paper[];
  selectedIds: Set<string>;
  onToggle(id: string): void;
  onRemove(id: string): void;
  onAddMore(): void;
  onGenerate(): void;
}

export default function PaperList({
  papers,
  selectedIds,
  onToggle,
  onRemove,
  onAddMore,
  onGenerate,
}: Props) {
  const selectedCount = selectedIds.size;

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-heading font-semibold text-text-primary">
          Papers ({papers.length})
        </h2>
        <button
          type="button"
          onClick={onAddMore}
          className="flex items-center gap-1 text-sm text-primary hover:text-primary-hover font-medium transition-colors"
        >
          <Plus size={16} />
          Add More
        </button>
      </div>

      <div className="flex-1 overflow-y-auto -mx-2 px-2 space-y-1">
        {papers.map((paper) => (
          <PaperListItem
            key={paper.id}
            paper={paper}
            selected={selectedIds.has(paper.id)}
            onToggle={() => onToggle(paper.id)}
            onRemove={() => onRemove(paper.id)}
          />
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-border">
        <button
          type="button"
          onClick={onGenerate}
          disabled={selectedCount === 0}
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Generate Literature Review
          {selectedCount > 0 && ` (${selectedCount} paper${selectedCount > 1 ? "s" : ""})`}
        </button>
      </div>
    </div>
  );
}
