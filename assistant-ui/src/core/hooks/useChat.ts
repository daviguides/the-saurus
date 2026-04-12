import { useEffect, useRef, useState, useCallback } from "react";
import type { Socket } from "socket.io-client";
import type { Message } from "../types/chat";
import type {
  TokenEvent,
  StepEvent,
  DoneEvent,
  ReferenceItem,
  ReferencesEvent,
  ErrorEvent,
} from "../types/websocket";

export function useChat(socket: Socket | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const streamBuffer = useRef("");
  const refsBuffer = useRef<ReferenceItem[]>([]);

  useEffect(() => {
    if (!socket) return;

    const onToken = (data: TokenEvent) => {
      streamBuffer.current += data.content;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, content: streamBuffer.current },
          ];
        }
        return prev;
      });
    };

    const onStep = (data: StepEvent) => {
      setCurrentStep(data.step);
    };

    const onReferences = (data: ReferencesEvent) => {
      refsBuffer.current = [...refsBuffer.current, ...data.references];
    };

    const onDone = (_data: DoneEvent) => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              isStreaming: false,
              references: refsBuffer.current.length
                ? refsBuffer.current
                : undefined,
            },
          ];
        }
        return prev;
      });
      setIsStreaming(false);
      setCurrentStep(null);
      streamBuffer.current = "";
      refsBuffer.current = [];
    };

    const onError = (data: ErrorEvent) => {
      setIsStreaming(false);
      setCurrentStep(null);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: last.content
                ? `${last.content}\n\nError: ${data.message}`
                : `Error: ${data.message}`,
              isStreaming: false,
            },
          ];
        }
        return prev;
      });
    };

    socket.on("token", onToken);
    socket.on("step", onStep);
    socket.on("references", onReferences);
    socket.on("done", onDone);
    socket.on("error", onError);

    return () => {
      socket.off("token", onToken);
      socket.off("step", onStep);
      socket.off("references", onReferences);
      socket.off("done", onDone);
      socket.off("error", onError);
    };
  }, [socket]);

  const sendMessage = useCallback(
    (text: string, context?: Record<string, unknown>) => {
      if (!socket || !text.trim() || isStreaming) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      streamBuffer.current = "";
      refsBuffer.current = [];

      socket.emit("message", { text, ...(context && { context }) });
    },
    [socket, isStreaming],
  );

  return { messages, isStreaming, currentStep, sendMessage };
}
