/**
 * Embedded shell — entry point for federated embedding in host app drawer.
 *
 * Exposed as federated module `./EmbeddedApp` for host consumption.
 * Accepts props from host (theme, open state, context) and manages its
 * own WebSocket connection to assistant-ws on port 8001.
 */
import "../../index.css";

import { useEffect, useRef, useCallback } from "react";
import { useWebSocket } from "../../core/hooks/useWebSocket";
import { useChat } from "../../core/hooks/useChat";
import MessageBubble from "../../ui/chat/MessageBubble";
import ChatInput from "../../ui/components/ChatInput";
import WelcomeContent from "../../ui/components/WelcomeContent";

export interface EmbeddedAppProps {
  isOpen?: boolean;
  isDark?: boolean;
  context?: {
    jobId: string | null;
    currentView: "papers" | "review";
  };
}

export default function EmbeddedApp({
  isOpen = true,
  isDark = false,
  context,
}: EmbeddedAppProps) {
  const { socket, status } = useWebSocket();
  const { messages, isStreaming, currentStep, sendMessage } = useChat(socket);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  // Track scroll position
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
  }, []);

  // Auto-scroll on new messages (skip when hidden)
  useEffect(() => {
    if (!isOpen || !isAtBottomRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [isOpen, messages, currentStep]);

  const handleSend = useCallback(
    (text: string) => {
      sendMessage(text, context ? { jobId: context.jobId, currentView: context.currentView } : undefined);
    },
    [sendMessage, context],
  );

  const isConnected = status === "connected";

  return (
    <div
      className={`h-full w-full flex flex-col bg-bg ${isDark ? "dark" : ""} ${!isOpen ? "hidden" : ""}`}
    >
      {/* Connection status banner — only when not connected */}
      {!isConnected && (
        <div className="px-4 py-2 text-xs text-center shrink-0 bg-surface border-b border-border text-text-muted">
          {status === "connecting" && "Connecting to assistant..."}
          {status === "disconnected" && "Disconnected — reconnecting..."}
          {status === "error" && "Connection error — retrying..."}
        </div>
      )}

      {/* Messages area */}
      <div
        className="flex-1 overflow-y-auto px-4 py-4"
        onScroll={handleScroll}
      >
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && isConnected && (
            <WelcomeContent onSuggestionClick={handleSend} />
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
      </div>

      {/* Chat input */}
      <div className="max-w-3xl mx-auto w-full">
        <ChatInput onSend={handleSend} isStreaming={isStreaming} />
      </div>
    </div>
  );
}
