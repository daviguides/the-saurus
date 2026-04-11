import type { Message } from "../../core/types/assistant";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary text-white"
            : "bg-bg border border-border border-l-2 border-l-primary text-text-primary"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {message.references && message.references.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-text-muted mb-1">Sources:</p>
            {message.references.map((ref, i) => (
              <div key={i} className="text-xs text-text-secondary mb-1">
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
          <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 rounded-sm" />
        )}
      </div>
    </div>
  );
}
