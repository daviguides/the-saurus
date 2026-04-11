import { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";
import TheSaurusMascot from "../shared/TheSaurusMascot";

interface Props {
  onUpload(): void;
  onFilesAdded(files: File[]): void;
  disabled?: boolean;
  progress?: number;
}

export default function EmptyState({ onUpload, onFilesAdded, disabled, progress }: Props) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) onFilesAdded(files);
    },
    [onFilesAdded, disabled],
  );

  return (
    <div
      className="flex flex-col items-center justify-center h-full gap-6 text-center px-4"
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <TheSaurusMascot size={180} className="animate-[breathe_3s_ease-in-out_infinite]" />
      <div>
        <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
          {disabled ? "Uploading papers..." : "Feed The Saurus your papers"}
        </h2>
        <p className="text-text-secondary max-w-md">
          {disabled
            ? "Your PDFs are being uploaded and processed."
            : "Upload scientific PDFs to build your corpus. The Saurus will extract themes, claims, and generate a literature review."}
        </p>
      </div>
      {disabled ? (
        <div className="w-full max-w-sm flex flex-col items-center gap-3">
          <Loader2 size={32} className="text-primary animate-spin" />
          <div className="w-full bg-border rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress ?? 0}%` }}
            />
          </div>
          <p className="text-sm text-text-muted">{progress ?? 0}%</p>
        </div>
      ) : (
        <div
          className={`w-full max-w-sm rounded-lg border-2 border-dashed p-6 transition-all duration-200 cursor-pointer ${
            dragOver
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-border hover:border-primary/50"
          }`}
          onClick={onUpload}
        >
          <p className="text-sm text-text-muted">
            Drop PDFs here or{" "}
            <span className="text-primary font-medium">browse files</span>
          </p>
        </div>
      )}
    </div>
  );
}
