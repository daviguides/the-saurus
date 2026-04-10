import { io, type Socket } from "socket.io-client";

const PIPELINE_URL =
  import.meta.env.VITE_PIPELINE_URL || "http://localhost:8002";
const ASSISTANT_URL =
  import.meta.env.VITE_ASSISTANT_URL || "http://localhost:8001";

const RECONNECTION_OPTS = {
  reconnectionAttempts: 10,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 10_000,
  timeout: 10_000,
};

let pipelineSocket: Socket | null = null;
let assistantSocket: Socket | null = null;

export function createPipelineSocket(): Socket {
  if (pipelineSocket?.connected) return pipelineSocket;

  pipelineSocket = io(PIPELINE_URL, {
    ...RECONNECTION_OPTS,
    autoConnect: true,
  });

  return pipelineSocket;
}

export function createAssistantSocket(): Socket {
  if (assistantSocket?.connected) return assistantSocket;

  assistantSocket = io(ASSISTANT_URL, {
    ...RECONNECTION_OPTS,
    autoConnect: true,
  });

  return assistantSocket;
}

export function getPipelineSocket(): Socket | null {
  return pipelineSocket;
}

export function getAssistantSocket(): Socket | null {
  return assistantSocket;
}
