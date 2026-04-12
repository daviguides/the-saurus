import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useJobId } from "../../core/hooks/useJobId";
import { fetchEnrichedPapers, fetchJobStatus } from "../../core/services/api";
import { transformPapers } from "../../core/transforms/papers";
import type { Paper } from "../../core/types/paper";
import PaperCards from "../papers/PaperCards";
import TheSaurusMascot from "../shared/TheSaurusMascot";

export default function PapersView() {
  const jobId = useJobId();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchPapers = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const status = await fetchJobStatus(id);
      if (status.status !== "completed") {
        setPapers([]);
        return;
      }
      const enriched = await fetchEnrichedPapers(id);
      setPapers(transformPapers(enriched));
    } catch (e) {
      console.error("Failed to fetch papers:", e);
      setPapers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (jobId) {
      fetchPapers(jobId);
    } else {
      setPapers([]);
    }
  }, [jobId, fetchPapers]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={32} className="text-primary animate-spin" />
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4 gap-4">
        <TheSaurusMascot size={160} className="animate-[breathe_3s_ease-in-out_infinite]" />
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
