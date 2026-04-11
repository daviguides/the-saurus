import { MessageCircle } from "lucide-react";

export default function EmptyChat() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
        <MessageCircle size={24} className="text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium text-text-primary mb-1">
          Ask about your papers, themes, or the review
        </p>
        <p className="text-xs text-text-muted">
          The assistant can help you explore findings and navigate your
          literature review.
        </p>
      </div>
    </div>
  );
}
