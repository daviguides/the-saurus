import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Loader2, Upload, X } from "lucide-react";

interface Props {
  open: boolean;
  onClose(): void;
  onFilesAdded(files: File[]): void;
  disabled?: boolean;
}

export default function UploadModal({ open, onClose, onFilesAdded, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) modalRef.current?.focus();
  }, [open]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        onFilesAdded(files);
        onClose();
      }
    },
    [onFilesAdded, onClose, disabled],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (disabled) return;
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        onFilesAdded(files);
        onClose();
      }
    },
    [onFilesAdded, onClose, disabled],
  );

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label="Upload papers"
        tabIndex={-1}
        className="relative w-full max-w-lg rounded-xl bg-surface p-6 shadow-xl outline-none"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 rounded-md p-1 text-text-secondary hover:text-text-primary hover:bg-border/50 transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        <h2 className="text-lg font-heading font-semibold text-text-primary mb-4">
          Upload Papers
        </h2>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragOver(true);
          }}
          onDragEnter={() => { if (!disabled) setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 transition-colors ${
            disabled
              ? "border-border opacity-60 cursor-not-allowed"
              : dragOver
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
          }`}
        >
          {disabled ? (
            <>
              <Loader2 size={36} className="text-primary animate-spin" />
              <p className="text-text-secondary text-sm text-center">
                Uploading...
              </p>
            </>
          ) : (
            <>
              <Upload
                size={36}
                className={dragOver ? "text-primary" : "text-text-muted"}
              />
              <p className="text-text-secondary text-sm text-center">
                Drag & drop PDF files here
              </p>
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover transition-colors"
              >
                Browse Files
              </button>
            </>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />

        <p className="mt-3 text-xs text-text-muted text-center">
          Accepted format: PDF
        </p>
      </div>
    </div>,
    document.body,
  );
}
