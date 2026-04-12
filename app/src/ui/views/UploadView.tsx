import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle } from "lucide-react";
import { useUpload } from "../../core/hooks/useUpload";
import { useJobId, clearJobId } from "../../core/hooks/useJobId";
import { usePipelineTrace } from "../../core/hooks/usePipelineTrace";
import { useReview } from "../../core/hooks/useReview";
import { fetchEnrichedPapers } from "../../core/services/api";
import { transformPapers } from "../../core/transforms/papers";
import { usePapers } from "../../core/hooks/usePapers";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PipelineTrace from "../pipeline/PipelineTrace";
import Toast from "../shared/Toast";

type StateKey = "pipeline" | "error" | "empty";

function CrossfadeSlot({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <div
      className={`absolute inset-0 transition-opacity duration-300 ease ${
        active ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"
      }`}
    >
      {children}
    </div>
  );
}

export default function UploadView() {
  const { loadPapers } = usePapers();

  const {
    status: uploadStatus,
    progress: uploadProgress,
    error: uploadError,
    jobId: uploadJobId,
    upload,
    reset: resetUpload,
  } = useUpload();

  const storedJobId = useJobId();
  const effectiveJobId = uploadJobId ?? storedJobId;

  const { state: pipelineState, connectionLost, isRecovering, isRunning, isCompleted, isFailed } =
    usePipelineTrace(effectiveJobId);

  const { fetchAndLoad: fetchAndLoadReview } = useReview();

  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const handler = () => setModalOpen(true);
    window.addEventListener("open-upload-modal", handler);
    return () => window.removeEventListener("open-upload-modal", handler);
  }, []);

  // Fetch real data when pipeline completes
  useEffect(() => {
    if (isCompleted && effectiveJobId) {
      const timer = setTimeout(async () => {
        try {
          const enriched = await fetchEnrichedPapers(effectiveJobId);
          loadPapers(transformPapers(enriched));
          fetchAndLoadReview(effectiveJobId);
        } catch {
          // Fall back gracefully
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, effectiveJobId, loadPapers, fetchAndLoadReview]);

  const handleFilesAdded = useCallback(
    (files: File[]) => {
      upload(files);
    },
    [upload],
  );

  const isUploading = uploadStatus === "uploading";

  const stateKey: StateKey = useMemo(() => {
    if (isRecovering || uploadStatus === "processing" || isRunning) return "pipeline";
    if (isFailed && effectiveJobId) return "error";
    return "empty";
  }, [isRecovering, uploadStatus, isRunning, isFailed, effectiveJobId]);

  return (
    <>
      <div className="relative h-full">
        <CrossfadeSlot active={stateKey === "pipeline"}>
          <PipelineTrace state={pipelineState} connectionLost={connectionLost} />
        </CrossfadeSlot>

        <CrossfadeSlot active={stateKey === "error"}>
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
            <div className="rounded-xl border border-error/30 p-8 flex flex-col items-center gap-4">
              <AlertCircle size={48} className="text-error" />
              <div>
                <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
                  Pipeline failed
                </h2>
                <p className="text-text-secondary max-w-md text-sm">
                  Something went wrong during processing. Please try uploading your papers again.
                </p>
              </div>
              <button
                type="button"
                onClick={() => clearJobId()}
                className="mt-2 px-4 py-2 text-sm rounded-lg border border-border text-text-secondary hover:text-primary hover:border-primary transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </CrossfadeSlot>

        <CrossfadeSlot active={stateKey === "empty"}>
          <EmptyState
            onUpload={() => setModalOpen(true)}
            onFilesAdded={handleFilesAdded}
            disabled={isUploading}
            progress={uploadProgress}
          />
        </CrossfadeSlot>
      </div>

      <UploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onFilesAdded={handleFilesAdded}
        disabled={isUploading}
      />
      <Toast message={uploadError} onDismiss={resetUpload} />
    </>
  );
}
