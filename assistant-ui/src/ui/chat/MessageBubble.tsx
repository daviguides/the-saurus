import type { Message } from "../../core/types/chat";
import ReactMarkdown from "react-markdown";
import type { ExtraProps } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary text-white"
            : "bg-bg text-text-primary"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose-content">
            <ReactMarkdown
              components={{
                code({ className, children, node, ...props }: React.ComponentPropsWithRef<"code"> & ExtraProps) {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !node?.properties?.className;
                  return isInline ? (
                    <code {...props}>
                      {children}
                    </code>
                  ) : (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match?.[1] ?? "text"}
                      PreTag="div"
                      customStyle={{ background: "transparent" }}
                    >
                      {String(children).replace(/\n$/, "")}
                    </SyntaxHighlighter>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {message.references && message.references.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-text-muted mb-1">Sources:</p>
            {message.references.map((ref, i) => (
              <div key={ref.doi || ref.title || i} className="text-xs text-text-secondary mb-1">
                <span className="font-medium">{ref.title}</span>
                {ref.year && <span> ({ref.year})</span>}
                {ref.doi && (
                  <span className="text-primary ml-1">{ref.doi}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {message.isStreaming && (
          <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
        )}
      </div>
    </div>
  );
}
