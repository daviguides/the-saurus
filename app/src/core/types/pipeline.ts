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
  { id: "paper_analysis", label: "Paper Analysis", icon: "Tags" },
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

// --- Event Type Literals ---

/** Stage-level event types emitted by the pipeline. */
export type StageEventType =
  | "job_created"
  | "job_started"
  | "job_completed"
  | "job_failed"
  | "stage_started"
  | "stage_completed"
  | "stage_failed"
  | "paper_ingested"
  | "paper_processed"
  | "paper_analyzed"
  | "theme_extracted"
  | "theme_deduplicated"
  | "claim_extracted"
  | "review_generated";

/** Agent-level event types from Agno event streaming. */
export type AgentEventType =
  | "agent_started"
  | "agent_tool_call"
  | "agent_tool_result"
  | "agent_content"
  | "agent_completed"
  | "agent_error";

// --- Pipeline Event Discriminated Union ---

/** Fields shared by all pipeline events (stage and agent). */
export interface PipelineEventBase {
  id: string;
  timestamp: number;
  stage?: string;
  paperId?: string;
  paperTitle?: string;
  message: string;
}

/** Stage-level pipeline event. Same shape as the original PipelineEvent. */
export interface StagePipelineEvent extends PipelineEventBase {
  eventType: StageEventType;
}

/** Fields shared by all agent-level events. */
export interface AgentEventBase extends PipelineEventBase {
  eventType: AgentEventType;
  agentName: string;
  humanMessage: string;
  technicalMessage: string;
}

export interface AgentStartedEvent extends AgentEventBase {
  eventType: "agent_started";
  model?: string;
}

export interface AgentToolCallEvent extends AgentEventBase {
  eventType: "agent_tool_call";
  toolName: string;
  toolArgsPreview?: string;
}

export interface AgentToolResultEvent extends AgentEventBase {
  eventType: "agent_tool_result";
  toolName: string;
  resultLen: number;
  elapsedMs?: number;
}

export interface AgentContentEvent extends AgentEventBase {
  eventType: "agent_content";
  contentLen: number;
  contentType: string;
}

export interface AgentCompletedEvent extends AgentEventBase {
  eventType: "agent_completed";
  elapsedMs?: number;
}

export interface AgentErrorEvent extends AgentEventBase {
  eventType: "agent_error";
  error: string;
  errorType: string;
  elapsedMs?: number;
}

/** Union of all agent-level event types. */
export type AgentEvent =
  | AgentStartedEvent
  | AgentToolCallEvent
  | AgentToolResultEvent
  | AgentContentEvent
  | AgentCompletedEvent
  | AgentErrorEvent;

/** Union of all pipeline events (stage + agent). Discriminate on `eventType`. */
export type PipelineEvent = StagePipelineEvent | AgentEvent;

/** Type guard: checks if a pipeline event is an agent-level event. */
export function isAgentEvent(event: PipelineEvent): event is AgentEvent {
  return event.eventType.startsWith("agent_");
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

/** Raw event JSON from the backend WebSocket. */
export interface RawPipelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  job_id: string;
  payload: Record<string, unknown>;
}
