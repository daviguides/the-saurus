import { useEffect, useRef, useState, useCallback } from "react";
import type { Socket } from "socket.io-client";
import { createSocket, storeSessionId } from "../services/socket";
import type { ConnectionStatus } from "../types/chat";

export function useWebSocket() {
  const socketRef = useRef<Socket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    const socket = createSocket();
    socketRef.current = socket;

    socket.on("connect", () => setStatus("connected"));
    socket.on("disconnect", () => setStatus("disconnected"));
    socket.on("connect_error", () => setStatus("error"));

    socket.on("session_created", (data: { session_id: string }) => {
      setSessionId(data.session_id);
      storeSessionId(data.session_id);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("connect_error");
      socket.off("session_created");
    };
  }, []);

  const send = useCallback((text: string) => {
    socketRef.current?.emit("message", { text });
  }, []);

  return { socket: socketRef.current, status, sessionId, send };
}
