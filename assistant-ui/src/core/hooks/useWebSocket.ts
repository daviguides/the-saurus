import { useEffect, useState } from "react";
import type { Socket } from "socket.io-client";
import { createSocket, disconnectSocket, storeSessionId } from "../services/socket";
import type { ConnectionStatus } from "../types/chat";
import type { SessionCreatedEvent } from "../types/websocket";

export function useWebSocket() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    const s = createSocket();
    setSocket(s);

    s.on("connect", () => setStatus("connected"));
    s.on("disconnect", () => setStatus("disconnected"));
    s.on("connect_error", () => setStatus("error"));

    s.on("session_created", (data: SessionCreatedEvent) => {
      setSessionId(data.session_id);
      storeSessionId(data.session_id);
    });

    s.io.on("reconnect_failed", () => {
      setStatus("error");
    });

    return () => {
      s.off("connect");
      s.off("disconnect");
      s.off("connect_error");
      s.off("session_created");
      s.io.off("reconnect_failed");
      disconnectSocket();
    };
  }, []);

  return { socket, status, sessionId };
}
