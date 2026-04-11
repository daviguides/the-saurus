import { useEffect, useRef, useState } from "react";
import { BookOpen, Loader2, AlertCircle, Copy, Check } from "lucide-react";
import { useReview } from "../../core/hooks/useReview";
import { useJobId } from "../../core/hooks/useJobId";
import StatsHeader from "../review/StatsHeader";
import ReviewBody from "../review/ReviewBody";
import ReferencesSection from "../review/ReferencesSection";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  const Icon = copied ? Check : Copy;

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? "Copied!" : "Copy review text"}
      className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-primary transition-colors"
    >
      <Icon size={14} />
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

function EmptyState() {
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
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-4">
      <Loader2 size={32} className="text-primary animate-spin" />
      <p className="text-text-secondary text-sm">Loading review...</p>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
      <AlertCircle size={48} className="text-red-500" />
      <div>
        <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
          Failed to load review
        </h2>
        <p className="text-text-secondary max-w-md text-sm">{message}</p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-2 px-4 py-2 text-sm rounded-lg border border-border text-text-secondary hover:text-primary hover:border-primary transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

export default function ReviewView() {
  const { review, hasReview, loading, error, fetchAndLoad } = useReview();
  const jobId = useJobId();
  const attemptedRef = useRef(false);

  // Auto-fetch review on mount if not already loaded
  useEffect(() => {
    if (!hasReview && !loading && jobId && !attemptedRef.current) {
      attemptedRef.current = true;
      fetchAndLoad(jobId);
    }
  }, [hasReview, loading, jobId, fetchAndLoad]);

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          if (jobId) fetchAndLoad(jobId);
        }}
      />
    );
  }

  if (!hasReview || !review) {
    return <EmptyState />;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center border-b border-border bg-surface">
        <StatsHeader stats={review.stats} />
        <div className="ml-auto px-8">
          <CopyButton text={review.markdown} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scroll-smooth">
        <div className="px-8 py-6">
          <ReviewBody markdown={review.markdown} papers={review.papers} />
          <ReferencesSection papers={review.papers} />
        </div>
      </div>
    </div>
  );
}
