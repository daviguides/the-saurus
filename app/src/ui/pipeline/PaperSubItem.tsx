import { Check } from "lucide-react";

interface Props {
  title: string;
  isLast: boolean;
}

export default function PaperSubItem({ title, isLast }: Props) {
  return (
    <div className="relative pl-6 flex items-center gap-2 py-1">
      {/* Vertical connector */}
      {!isLast && (
        <div className="absolute left-[7px] top-5 bottom-0 w-px bg-border" />
      )}
      {/* Horizontal branch */}
      <div className="absolute left-[7px] top-1/2 w-3 h-px bg-border" />
      {/* Node dot */}
      <div className="absolute left-[5px] top-1/2 -translate-y-1/2 w-[5px] h-[5px] rounded-full bg-primary" />
      {/* Content */}
      <Check size={12} className="text-primary flex-shrink-0 ml-1" />
      <span className="text-xs text-text-secondary truncate">{title}</span>
    </div>
  );
}
