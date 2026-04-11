import type { ReactNode } from "react";
import type { ReviewPaper } from "../../core/types/review";
import Tooltip from "../shared/Tooltip";

interface Props {
  href?: string;
  title?: string;
  children?: ReactNode;
  papers: ReviewPaper[];
  refToPaperIndex?: Record<number, number>;
}

export default function CitationLink({ href, title, children, papers, refToPaperIndex }: Props) {
  if (!href?.startsWith("cite:")) {
    return (
      <a href={href} title={title} target="_blank" rel="noopener noreferrer" className="text-primary underline">
        {children}
      </a>
    );
  }

  const refNumber = parseInt(href.slice(5), 10);
  // Map ref_number → paper index via citation mapping, fallback to direct match
  const paperIndex = refToPaperIndex?.[refNumber] ?? refNumber;
  const paper = papers.find((p) => p.index === paperIndex);
  const position = title || "";

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    const el = document.getElementById(`ref-${paperIndex}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.add("ref-highlight");
      setTimeout(() => el.classList.remove("ref-highlight"), 2000);
    }
  };

  const tooltipContent = paper ? (
    <div>
      <p className="font-heading font-semibold text-xs">{paper.title}</p>
      {paper.claims.length > 0 && (
        <p className="mt-1 text-xs opacity-80 line-clamp-3">{paper.claims[0].text}</p>
      )}
    </div>
  ) : null;

  const link = (
    <a
      href={`#ref-${paperIndex}`}
      onClick={handleClick}
      className="text-primary font-medium no-underline hover:underline cursor-pointer"
    >
      {children}
      {position && (
        <span className="font-mono text-text-muted text-xs ml-0.5">({position})</span>
      )}
    </a>
  );

  if (!tooltipContent) return link;

  return <Tooltip content={tooltipContent}>{link}</Tooltip>;
}
