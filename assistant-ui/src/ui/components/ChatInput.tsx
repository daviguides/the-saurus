import { useState, useCallback } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  isStreaming: boolean;
}

export default function ChatInput({ onSend, isStreaming }: Props) {
  const [text, setText] = useState("");

  const handleSubmit = useCallback(() => {
    if (!text.trim() || isStreaming) return;
    onSend(text.trim());
    setText("");
  }, [text, isStreaming, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-2 p-4 border-t border-gray-800">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about scientific papers..."
        rows={1}
        className="flex-1 resize-none bg-gray-800 text-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-500"
      />
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || isStreaming}
        className="p-3 rounded-xl bg-blue-600 text-white disabled:opacity-40 hover:bg-blue-500 transition-colors"
      >
        {isStreaming ? <Square size={18} /> : <Send size={18} />}
      </button>
    </div>
  );
}
