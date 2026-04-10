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

export interface SessionCreatedEvent {
  session_id: string;
}
