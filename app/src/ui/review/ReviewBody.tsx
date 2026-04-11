import { useMemo, type ComponentProps } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReviewPaper } from "../../core/types/review";
import CitationLink from "./CitationLink";

interface Props {
  markdown: string;
  papers: ReviewPaper[];
}

export default function ReviewBody({ markdown, papers }: Props) {
  const components = useMemo(
    (): ComponentProps<typeof Markdown>["components"] => ({
      a: ({ href, title, children }) => (
        <CitationLink href={href} title={title} papers={papers}>
          {children}
        </CitationLink>
      ),
    }),
    [papers],
  );

  return (
    <article className="prose-content max-w-prose">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </Markdown>
    </article>
  );
}
