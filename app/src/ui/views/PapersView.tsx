import { useCallback, useEffect, useState } from "react";
import { usePapers } from "../../core/hooks/usePapers";
import { useUpload } from "../../core/hooks/useUpload";
import { usePipelineTrace } from "../../core/hooks/usePipelineTrace";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PaperList from "../papers/PaperList";
import PaperCards from "../papers/PaperCards";
import PipelineTrace from "../pipeline/PipelineTrace";
import Toast from "../shared/Toast";
import { MOCK_COMPLETE_PAPERS } from "../../mocks/papers";

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

  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const handler = () => setModalOpen(true);
    window.addEventListener("open-upload-modal", handler);
    return () => window.removeEventListener("open-upload-modal", handler);
  }, []);

  // Transition to complete state when pipeline finishes
  useEffect(() => {
    if (isCompleted && jobId) {
      const timer = setTimeout(() => {
        loadMockComplete(MOCK_COMPLETE_PAPERS);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, jobId, loadMockComplete]);

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
