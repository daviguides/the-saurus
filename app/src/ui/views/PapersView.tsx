import { useEffect, useState } from "react";
import { usePapers } from "../../core/hooks/usePapers";
import UploadModal from "../papers/UploadModal";
import EmptyState from "../papers/EmptyState";
import PaperList from "../papers/PaperList";
import PaperCards from "../papers/PaperCards";

export default function PapersView() {
  const {
    papers,
    viewState,
    selectedIds,
    addPapers,
    removePaper,
    toggleSelect,
  } = usePapers();

  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const handler = () => setModalOpen(true);
    window.addEventListener("open-upload-modal", handler);
    return () => window.removeEventListener("open-upload-modal", handler);
  }, []);

  const handleGenerate = () => {
    // Pipeline trigger — wired in pipeline-trace-view task
  };

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
