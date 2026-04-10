import { BookOpen } from "lucide-react";

export default function ReviewView() {
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
