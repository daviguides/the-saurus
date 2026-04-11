import { useCallback, useState } from "react";
import TheSaurusMascot from "../shared/TheSaurusMascot";

interface Props {
  onUpload(): void;
  onFilesAdded(files: File[]): void;
}

export default function EmptyState({ onUpload, onFilesAdded }: Props) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) onFilesAdded(files);
    },
    [onFilesAdded],
  );

  return (
    <div
      className="flex flex-col items-center justify-center h-full gap-6 text-center px-4"
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <TheSaurusMascot size={140} className="text-primary/40" />
      <div>
        <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
          Feed The Saurus your papers
        </h2>
        <p className="text-text-secondary max-w-md">
          Upload scientific PDFs to build your corpus. The Saurus will extract
          themes, claims, and generate a literature review.
        </p>
      </div>
      <div
        className={`w-full max-w-sm rounded-lg border-2 border-dashed p-6 transition-colors cursor-pointer ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
        onClick={onUpload}
      >
        <p className="text-sm text-text-muted">
          Drop PDFs here or{" "}
          <span className="text-primary font-medium">browse files</span>
        </p>
      </div>
    </div>
  );
}
