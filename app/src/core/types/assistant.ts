export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  references?: ReferenceItem[];
  isStreaming?: boolean;
}

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

export interface TokenEvent {
  content: string;
}

export interface StepEvent {
  step: string;
  agent?: string;
  tool?: string;
}

export interface DoneEvent {
  metrics: {
    elapsed_time_ms: number;
  };
}

export interface ReferenceItem {
  title: string;
  authors?: string[];
  year?: number;
  doi?: string;
  snippet?: string;
  score?: number;
}

export interface ReferencesEvent {
  references: ReferenceItem[];
}

export interface ErrorEvent {
  message: string;
}
