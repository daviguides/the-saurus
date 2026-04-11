import { usePapers } from "../../core/hooks/usePapers";
import PaperCards from "../papers/PaperCards";

export default function PapersView() {
  const { papers, viewState } = usePapers();

  if (viewState !== "complete" || papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4">
        <p className="text-text-muted text-sm">
          No papers processed yet. Upload papers to get started.
        </p>
      </div>
    );
  }

  return <PaperCards papers={papers} />;
}
