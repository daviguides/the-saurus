export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface StageEvent {
  stage: string;
  status: StageStatus;
  paper_id?: string;
  message?: string;
}

export interface ProgressEvent {
  completed: number;
  total: number;
  stage: string;
}

export interface PipelineErrorEvent {
  stage: string;
  message: string;
  paper_id?: string;
}

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";
