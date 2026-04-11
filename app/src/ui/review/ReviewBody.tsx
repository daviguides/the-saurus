import { useMemo, type ComponentProps } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReviewPaper } from "../../core/types/review";
import CitationLink from "./CitationLink";
import { slugify, extractText } from "./slugify";

interface Props {
  markdown: string;
  papers: ReviewPaper[];
  refToPaperIndex?: Record<number, number>;
}

export default function ReviewBody({ markdown, papers, refToPaperIndex }: Props) {
  const components = useMemo(
    (): ComponentProps<typeof Markdown>["components"] => ({
      a: ({ href, title, children }) => (
        <CitationLink href={href} title={title} papers={papers} refToPaperIndex={refToPaperIndex}>
          {children}
        </CitationLink>
      ),
      h2: ({ children }) => {
        const id = slugify(extractText(children));
        return (
          <h2 id={id} className="scroll-mt-4 transition-colors duration-500">
            {children}
          </h2>
        );
      },
    }),
    [papers, refToPaperIndex],
  );

  return (
    <article className="prose-content max-w-prose">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </Markdown>
    </article>
  );
}
