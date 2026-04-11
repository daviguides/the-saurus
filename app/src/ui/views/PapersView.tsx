import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle } from "lucide-react";
import { usePapers } from "../../core/hooks/usePapers";
import { useUpload } from "../../core/hooks/useUpload";
import { useJobId, clearJobId } from "../../core/hooks/useJobId";
import { usePipelineTrace } from "../../core/hooks/usePipelineTrace";
import { useReview } from "../../core/hooks/useReview";
import { fetchEnrichedPapers } from "../../core/services/api";
import { transformPapers } from "../../core/transforms/papers";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PaperList from "../papers/PaperList";
import PaperCards from "../papers/PaperCards";
import PipelineTrace from "../pipeline/PipelineTrace";
import Toast from "../shared/Toast";

export default function PapersView() {
  const {
    papers,
    viewState,
    selectedIds,
    addPapers,
    removePaper,
    toggleSelect,
    loadMockComplete,
  } = usePapers();

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

  const { state: pipelineState, isRecovering, isRunning, isCompleted, isFailed } =
    usePipelineTrace(effectiveJobId);

  const { fetchAndLoad: fetchAndLoadReview } = useReview();

  const [modalOpen, setModalOpen] = useState(false);
  const fetchedRef = useRef(false);

  useEffect(() => {
    const handler = () => setModalOpen(true);
    window.addEventListener("open-upload-modal", handler);
    return () => window.removeEventListener("open-upload-modal", handler);
  }, []);

  // Fetch real data when pipeline completes
  useEffect(() => {
    if (isCompleted && effectiveJobId && !fetchedRef.current) {
      fetchedRef.current = true;
      const timer = setTimeout(async () => {
        try {
          const enriched = await fetchEnrichedPapers(effectiveJobId);
          loadMockComplete(transformPapers(enriched));
          fetchAndLoadReview(effectiveJobId);
        } catch {
          // Fall back gracefully — papers view stays in current state
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, effectiveJobId, loadMockComplete, fetchAndLoadReview]);

  const handleFilesAdded = useCallback(
    (files: File[]) => {
      upload(files);
    },
    [upload],
  );

  const isUploading = uploadStatus === "uploading";

  // Show pipeline trace during recovery or active processing
  if (isRecovering || uploadStatus === "processing" || isRunning) {
    return <PipelineTrace state={pipelineState} />;
  }

  // Show error state for failed pipelines
  if (isFailed && effectiveJobId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
        <AlertCircle size={48} className="text-red-500" />
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
          Start New Review
        </button>
      </div>
    );
  }

  if (viewState === "complete") {
    return <PaperCards papers={papers} />;
  }

  if (viewState === "empty") {
    return (
      <>
        <EmptyState
          onUpload={() => setModalOpen(true)}
          onFilesAdded={handleFilesAdded}
          disabled={isUploading}
          progress={uploadProgress}
        />
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

  return (
    <>
      <PaperList
        papers={papers}
        selectedIds={selectedIds}
        onToggle={toggleSelect}
        onRemove={removePaper}
        onAddMore={() => setModalOpen(true)}
        onGenerate={() => {}}
      />
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
