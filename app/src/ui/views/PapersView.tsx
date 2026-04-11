import { usePapers } from "../../core/hooks/usePapers";
import PaperCards from "../papers/PaperCards";
import TheSaurusMascot from "../shared/TheSaurusMascot";

export default function PapersView() {
  const { papers, viewState } = usePapers();

  if (viewState !== "complete" || papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4 gap-4">
        <TheSaurusMascot size={120} className="animate-[breathe_3s_ease-in-out_infinite]" />
        <div>
          <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
            No papers analyzed yet
          </h2>
          <p className="text-text-secondary max-w-md">
            Upload papers and run the pipeline. Extracted themes and claims
            for each paper will appear here.
          </p>
        </div>
      </div>
    );
  }

  return <PaperCards papers={papers} />;
}
