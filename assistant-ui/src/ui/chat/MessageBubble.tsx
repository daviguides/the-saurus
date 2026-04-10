import type { Message } from "../../core/types/chat";
import ReactMarkdown from "react-markdown";
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
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-100"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <ReactMarkdown
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "");
                const inline = !match;
                return inline ? (
                  <code
                    className="bg-gray-700 px-1.5 py-0.5 rounded text-sm"
                    {...props}
                  >
                    {children}
                  </code>
                ) : (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}

        {message.references && message.references.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-700">
            <p className="text-xs text-gray-400 mb-1">Sources:</p>
            {message.references.map((ref, i) => (
              <div key={i} className="text-xs text-gray-300 mb-1">
                <span className="font-medium">{ref.title}</span>
                {ref.year && <span> ({ref.year})</span>}
                {ref.doi && (
                  <span className="text-blue-400 ml-1">{ref.doi}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {message.isStreaming && (
          <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1" />
        )}
      </div>
    </div>
  );
}
