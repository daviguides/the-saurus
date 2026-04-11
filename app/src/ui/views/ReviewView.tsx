import { BookOpen } from "lucide-react";
import { useReview } from "../../core/hooks/useReview";
import { MOCK_REVIEW } from "../../mocks/review";
import StatsHeader from "../review/StatsHeader";
import ReviewBody from "../review/ReviewBody";
import ReferencesSection from "../review/ReferencesSection";

function EmptyState({ onLoadMock }: { onLoadMock: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
      <BookOpen size={48} className="text-text-muted" />
      <div>
        <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
          No review yet
        </h2>
        <p className="text-text-secondary max-w-md">
          Upload papers and run the pipeline to generate a literature review.
        </p>
      </div>
      <button
        type="button"
        onClick={onLoadMock}
        className="mt-2 px-4 py-2 text-sm rounded-lg border border-border text-text-secondary hover:text-primary hover:border-primary transition-colors"
      >
        Load mock review
      </button>
    </div>
  );
}

export default function ReviewView() {
  const { review, hasReview, loadReview } = useReview();

  if (!hasReview || !review) {
    return <EmptyState onLoadMock={() => loadReview(MOCK_REVIEW)} />;
  }

  return (
    <div className="flex flex-col h-full">
      <StatsHeader stats={review.stats} />
      <div className="flex-1 overflow-y-auto scroll-smooth">
        <div className="px-8 py-6">
          <ReviewBody markdown={review.markdown} papers={review.papers} />
          <ReferencesSection papers={review.papers} />
        </div>
      </div>
    </div>
  );
}
