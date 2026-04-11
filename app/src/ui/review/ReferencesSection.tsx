import type { ReviewPaper } from "../../core/types/review";
import { slugify } from "./slugify";

interface Props {
  papers: ReviewPaper[];
}

function scrollToSection(sectionLabel: string) {
  const el = document.getElementById(slugify(sectionLabel));
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.add("ref-highlight");
    setTimeout(() => el.classList.remove("ref-highlight"), 2000);
  }
}

function ReferenceEntry({ paper }: { paper: ReviewPaper }) {
  return (
    <li id={`ref-${paper.index}`} className="py-3 transition-colors duration-500">
      <div className="text-sm text-text-primary">
        <span className="font-semibold text-primary mr-1">[{paper.index}]</span>
        {paper.authors} ({paper.year}).{" "}
        <span className="italic">{paper.title}</span>.{" "}
        <span className="text-text-secondary">{paper.journal}</span>.
      </div>
      {paper.citedIn.length > 0 && (
        <p className="mt-1 text-xs text-text-muted">
          Cited in:{" "}
          {paper.citedIn.map((section, i) => (
            <span key={section}>
              {i > 0 && ", "}
              <a
                href={`#${slugify(section)}`}
                onClick={(e) => {
                  e.preventDefault();
                  scrollToSection(section);
                }}
                className="text-primary hover:underline cursor-pointer"
              >
                {section}
              </a>
            </span>
          ))}
        </p>
      )}
    </li>
  );
}

export default function ReferencesSection({ papers }: Props) {
  if (papers.length === 0) return null;

  return (
    <section className="mt-12 pt-8 border-t border-border">
      <h2 className="text-xl font-heading font-semibold text-text-primary mb-4">
        References
      </h2>
      <ol className="list-none divide-y divide-border/50">
        {papers.map((paper) => (
          <ReferenceEntry key={paper.id} paper={paper} />
        ))}
      </ol>
    </section>
  );
}
