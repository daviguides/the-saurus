import { useCallback, useEffect, useState } from "react";
import { usePapers } from "../../core/hooks/usePapers";
import { useUpload } from "../../core/hooks/useUpload";
import { usePipelineTrace } from "../../core/hooks/usePipelineTrace";
import { PIPELINE_STAGES } from "../../core/types/pipeline";
import type { PipelineState } from "../../core/types/pipeline";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PaperList from "../papers/PaperList";
import PaperCards from "../papers/PaperCards";
import PipelineTrace from "../pipeline/PipelineTrace";
import Toast from "../shared/Toast";
import { MOCK_COMPLETE_PAPERS } from "../../mocks/papers";

const INITIAL_PIPELINE_STATE: PipelineState = {
  status: "running",
  stages: PIPELINE_STAGES.map((s) => ({
    id: s.id,
    status: "pending",
    processedPapers: [],
    totalPapers: 0,
  })),
  events: [],
  progress: { completed: 0, total: 0 },
  startedAt: Date.now(),
};

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

  const { state: pipelineState, isRunning, isCompleted, startPipeline } =
    usePipelineTrace();

  const {
    status: uploadStatus,
    progress: uploadProgress,
    error: uploadError,
    upload,
    reset: resetUpload,
  } = useUpload();

  const [modalOpen, setModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const handler = () => setModalOpen(true);
    window.addEventListener("open-upload-modal", handler);
    return () => window.removeEventListener("open-upload-modal", handler);
  }, []);

  // Transition to complete state when pipeline finishes
  useEffect(() => {
    if (isCompleted && isProcessing) {
      const timer = setTimeout(() => {
        loadMockComplete(MOCK_COMPLETE_PAPERS);
        setIsProcessing(false);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, isProcessing, loadMockComplete]);

  const handleFilesAdded = useCallback(
    (files: File[]) => {
      upload(files);
    },
    [upload],
  );

  const handleGenerate = () => {
    const selectedPapers = papers
      .filter((p) => selectedIds.has(p.id))
      .map((p) => ({ id: p.id, title: p.title }));
    if (selectedPapers.length === 0) return;
    setIsProcessing(true);
    startPipeline(selectedPapers);
  };

  const isUploading = uploadStatus === "uploading";

  // Upload succeeded — show pipeline trace with initial pending state
  if (uploadStatus === "processing") {
    return <PipelineTrace state={INITIAL_PIPELINE_STATE} />;
  }

  // Pipeline running via mock (existing flow) — show pipeline trace
  if (isProcessing || isRunning) {
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
        onGenerate={handleGenerate}
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
