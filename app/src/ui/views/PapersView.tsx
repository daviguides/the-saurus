import { useCallback, useEffect, useRef, useState } from "react";
import { usePapers } from "../../core/hooks/usePapers";
import { useUpload } from "../../core/hooks/useUpload";
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
    jobId,
    upload,
    reset: resetUpload,
  } = useUpload();

  const { state: pipelineState, isRunning, isCompleted } =
    usePipelineTrace(jobId);

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
    if (isCompleted && jobId && !fetchedRef.current) {
      fetchedRef.current = true;
      const timer = setTimeout(async () => {
        try {
          const enriched = await fetchEnrichedPapers(jobId);
          loadMockComplete(transformPapers(enriched));
          fetchAndLoadReview(jobId);
        } catch {
          // Fall back gracefully — papers view stays in current state
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, jobId, loadMockComplete, fetchAndLoadReview]);

  const handleFilesAdded = useCallback(
    (files: File[]) => {
      upload(files);
    },
    [upload],
  );

  const isUploading = uploadStatus === "uploading";

  // Show pipeline trace when upload succeeded or pipeline is actively running
  if (uploadStatus === "processing" || isRunning) {
    return <PipelineTrace state={pipelineState} />;
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

  if (viewState === "complete") {
    return <PaperCards papers={papers} />;
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
