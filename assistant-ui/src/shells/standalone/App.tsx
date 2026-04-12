import { useEffect, useRef, useCallback } from "react";
import { useWebSocket } from "../../core/hooks/useWebSocket";
import { useChat } from "../../core/hooks/useChat";
import Header from "../../ui/shared/Header";
import MessageBubble from "../../ui/chat/MessageBubble";
import ChatInput from "../../ui/components/ChatInput";
import WelcomeContent from "../../ui/components/WelcomeContent";

export default function App() {
  const { socket, status } = useWebSocket();
  const { messages, isStreaming, currentStep, sendMessage } = useChat(socket);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
  }, []);

  useEffect(() => {
    if (!isAtBottomRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStep]);

  return (
    <div className="flex flex-col h-screen bg-bg">
      <Header status={status} />

      <main className="flex-1 overflow-y-auto px-6 py-4" onScroll={handleScroll}>
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && (
            <WelcomeContent onSuggestionClick={sendMessage} />
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {currentStep && (
            <div className="text-sm text-text-muted animate-pulse mb-2">
              {currentStep}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      <div className="max-w-3xl mx-auto w-full">
        <ChatInput onSend={sendMessage} isStreaming={isStreaming} />
      </div>
    </div>
  );
}
