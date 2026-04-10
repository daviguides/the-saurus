import { io, Socket } from "socket.io-client";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || "http://localhost:8001";

let socketInstance: Socket | null = null;

export function getStoredSessionId(): string | null {
  return localStorage.getItem("at_session_id");
}

export function storeSessionId(id: string): void {
  localStorage.setItem("at_session_id", id);
}

export function createSocket(): Socket {
  if (socketInstance?.connected) {
    return socketInstance;
  }

  socketInstance = io(SOCKET_URL, {
    auth: {
      session_id: getStoredSessionId(),
    },
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 10_000,
  });

  return socketInstance;
}

export function getSocket(): Socket | null {
  return socketInstance;
}
