import TheSaurusMascot from "../shared/TheSaurusMascot";

export default function PapersView() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-4">
      <TheSaurusMascot size={140} className="text-primary/40" />
      <div>
        <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
          Feed The Saurus your papers
        </h2>
        <p className="text-text-secondary max-w-md">
          Upload scientific PDFs to build your corpus. The Saurus will extract
          themes, claims, and generate a literature review.
        </p>
      </div>
    </div>
  );
}
