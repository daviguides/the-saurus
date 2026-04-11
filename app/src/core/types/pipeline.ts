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

// --- Pipeline Trace Types ---

export interface PipelineStageConfig {
  id: string;
  label: string;
  icon: string;
}

export const PIPELINE_STAGES: PipelineStageConfig[] = [
  { id: "theme_extraction", label: "Theme Extraction", icon: "Tags" },
  { id: "claim_extraction", label: "Claim Extraction", icon: "Quote" },
  { id: "theme_dedup", label: "Theme Deduplication", icon: "GitMerge" },
  { id: "theme_review", label: "Theme Review", icon: "BookOpen" },
  { id: "aggregation", label: "Review Generation", icon: "FileText" },
];

export interface PipelineStageState {
  id: string;
  status: StageStatus;
  processedPapers: string[];
  totalPapers: number;
}

export interface PipelineEvent {
  id: string;
  eventType: string;
  timestamp: number;
  stage?: string;
  paperId?: string;
  paperTitle?: string;
  message: string;
}

export interface PipelineState {
  status: "idle" | "recovering" | "running" | "completed" | "failed";
  stages: PipelineStageState[];
  events: PipelineEvent[];
  progress: { completed: number; total: number };
  startedAt: number | null;
}

export type PipelineAction =
  | { type: "START_PIPELINE"; payload: { totalPapers: number } }
  | { type: "STAGE_STARTED"; payload: { stage: string } }
  | { type: "STAGE_COMPLETED"; payload: { stage: string } }
  | { type: "PAPER_PROCESSED"; payload: { stage: string; paperId: string; paperTitle: string } }
  | { type: "EVENT_RECEIVED"; payload: PipelineEvent }
  | { type: "PIPELINE_COMPLETED" }
  | { type: "PIPELINE_FAILED"; payload: { message: string } }
  | { type: "RECOVERY_START" };

/** Response from GET /jobs/{id}/status. */
export interface JobStatusResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  stage: string;
  progress: number;
  paper_count: number;
  created_at: string;
  updated_at: string;
  error: string | null;
}

/** Raw event JSON from the backend WebSocket. */
export interface RawPipelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  job_id: string;
  payload: Record<string, unknown>;
}
