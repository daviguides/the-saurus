import { useEffect, useState } from "react";
import { usePapers } from "../../core/hooks/usePapers";
import { usePipelineTrace } from "../../core/hooks/usePipelineTrace";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PaperList from "../papers/PaperList";
import PaperCards from "../papers/PaperCards";
import PipelineTrace from "../pipeline/PipelineTrace";
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

  const { state: pipelineState, isRunning, isCompleted, startPipeline } =
    usePipelineTrace();

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

  const handleGenerate = () => {
    const selectedPapers = papers
      .filter((p) => selectedIds.has(p.id))
      .map((p) => ({ id: p.id, title: p.title }));
    if (selectedPapers.length === 0) return;
    setIsProcessing(true);
    startPipeline(selectedPapers);
  };

  // Processing state — show pipeline trace
  if (isProcessing || isRunning) {
    return <PipelineTrace state={pipelineState} />;
  }

  if (viewState === "empty") {
    return (
      <>
        <EmptyState
          onUpload={() => setModalOpen(true)}
          onFilesAdded={addPapers}
        />
        <UploadModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onFilesAdded={addPapers}
        />
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
        onFilesAdded={addPapers}
      />
    </>
  );
}
