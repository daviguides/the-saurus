import { useEffect, useRef, useState } from "react";
import type { Socket } from "socket.io-client";
import { createAssistantSocket } from "../services/socket";
import type { ConnectionStatus } from "../types/assistant";

export function useAssistantSocket(enabled: boolean) {
  const socketRef = useRef<Socket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  useEffect(() => {
    if (!enabled) return;

    const socket = createAssistantSocket();
    socketRef.current = socket;

    const onConnect = () => setStatus("connected");
    const onDisconnect = () => setStatus("disconnected");
    const onConnectError = () => setStatus("error");

    setStatus("connecting");
    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("connect_error", onConnectError);

    if (socket.connected) setStatus("connected");

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("connect_error", onConnectError);
    };
  }, [enabled]);

  return { socket: socketRef.current, status };
}
