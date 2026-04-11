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
      h2: ({ children }) => (
        <h2 className="text-xl font-heading font-semibold text-text-primary mt-10 mb-4 first:mt-0">
          {children}
        </h2>
      ),
      h3: ({ children }) => (
        <h3 className="text-lg font-heading font-medium text-text-primary mt-6 mb-3">
          {children}
        </h3>
      ),
      p: ({ children }) => (
        <p className="mb-4 leading-[1.7]">{children}</p>
      ),
    }),
    [papers],
  );

  return (
    <article className="font-heading text-base text-text-primary max-w-prose">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </Markdown>
    </article>
  );
}
