import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import clsx from "clsx";
import { useAssistant } from "../../core/context/AssistantContext";
import { useAssistantSocket } from "../../core/hooks/useAssistantSocket";
import { useAssistantChat } from "../../core/hooks/useAssistantChat";
import type { ConnectionStatus } from "../../core/types/assistant";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import EmptyChat from "./EmptyChat";

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connecting: "bg-accent",
  connected: "bg-green-500",
  disconnected: "bg-text-muted",
  error: "bg-red-500",
};

export default function AssistantDrawer() {
  const { isOpen, close } = useAssistant();
  const hasOpened = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  if (isOpen) hasOpened.current = true;

  const { socket, status } = useAssistantSocket(hasOpened.current);
  const { messages, isStreaming, currentStep, sendMessage } =
    useAssistantChat(socket);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStep]);

  const isConnected = status === "connected";

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={close}
        />
      )}

      {/* Drawer panel */}
      <aside
        className={clsx(
          "fixed top-0 right-0 h-full z-40 flex flex-col bg-surface border-l border-border",
          "w-[85vw] max-w-[var(--drawer-width)] lg:w-[var(--drawer-width)]",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Drawer header */}
        <div
          className="flex items-center justify-between px-4 border-b border-border shrink-0"
          style={{ height: "var(--header-height)" }}
        >
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-text-primary">
              Assistant
            </h2>
            <span
              className={clsx("w-2 h-2 rounded-full", STATUS_COLOR[status])}
              title={status}
            />
          </div>
          <button
            type="button"
            onClick={close}
            className="flex items-center justify-center w-7 h-7 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg transition-colors duration-200"
          >
            <X size={16} />
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-3 py-4">
          {messages.length === 0 ? (
            <EmptyChat />
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Step indicator */}
        {currentStep && (
          <div className="px-4 py-1.5 text-xs text-text-muted animate-pulse truncate">
            {currentStep}
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          disabled={!isConnected}
        />
      </aside>
    </>
  );
}
