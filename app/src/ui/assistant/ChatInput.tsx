import { useState, useCallback } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export default function ChatInput({ onSend, isStreaming, disabled }: Props) {
  const [text, setText] = useState("");

  const handleSubmit = useCallback(() => {
    if (!text.trim() || isStreaming || disabled) return;
    onSend(text.trim());
    setText("");
  }, [text, isStreaming, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-2 p-3 border-t border-border">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your papers..."
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none bg-surface border border-border text-text-primary rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-text-muted disabled:opacity-50"
      />
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || isStreaming || disabled}
        className="p-2.5 rounded-xl bg-primary text-white disabled:opacity-40 hover:bg-primary-hover transition-colors duration-200"
      >
        {isStreaming ? <Square size={16} /> : <Send size={16} />}
      </button>
    </div>
  );
}
