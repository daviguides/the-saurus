import { useReducer, useEffect, useRef, useState } from "react";
import type {
  PipelineState,
  PipelineAction,
  PipelineStageState,
  PipelineEvent,
  AgentEvent,
  AgentEventType,
  StagePipelineEvent,
  RawPipelineEvent,
} from "../types/pipeline";
import { PIPELINE_STAGES } from "../types/pipeline";
import {
  PIPELINE_API_URL,
  fetchPapers,
  fetchJobStatus,
  fetchEvents,
} from "../services/api";

function createInitialStages(): PipelineStageState[] {
  return PIPELINE_STAGES.map((s) => ({
    id: s.id,
    status: "pending",
    processedPapers: [],
    totalPapers: 0,
  }));
}

const INITIAL_STATE: PipelineState = {
  status: "idle",
  stages: createInitialStages(),
  events: [],
  progress: { completed: 0, total: 0 },
  startedAt: null,
};

function pipelineReducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case "RECOVERY_START":
      return { ...state, status: "recovering" };

    case "START_PIPELINE":
      return {
        ...state,
        status: "running",
        startedAt: state.startedAt ?? Date.now(),
        progress: { completed: 0, total: action.payload.totalPapers },
        stages: state.stages.map((s) => ({
          ...s,
          totalPapers: action.payload.totalPapers,
          // Preserve processedPapers during recovery replay
          processedPapers: state.status === "recovering" ? s.processedPapers : [],
          status: state.status === "recovering" ? s.status : "pending",
        })),
        // Preserve events during recovery replay
        events: state.status === "recovering" ? state.events : [],
      };

    case "STAGE_STARTED":
      return {
        ...state,
        stages: state.stages.map((s) =>
          s.id === action.payload.stage ? { ...s, status: "running" } : s,
        ),
      };

    case "STAGE_COMPLETED":
      return {
        ...state,
        stages: state.stages.map((s) =>
          s.id === action.payload.stage ? { ...s, status: "completed" } : s,
        ),
      };

    case "PAPER_PROCESSED": {
      const { stage, paperId } = action.payload;
      const newStages = state.stages.map((s) =>
        s.id === stage && !s.processedPapers.includes(paperId)
          ? { ...s, processedPapers: [...s.processedPapers, paperId] }
          : s,
      );
      const activeStage = newStages.find((s) => s.id === stage);
      return {
        ...state,
        stages: newStages,
        progress: {
          completed: activeStage?.processedPapers.length ?? 0,
          total: activeStage?.totalPapers ?? state.progress.total,
        },
      };
    }

    case "EVENT_RECEIVED":
      return {
        ...state,
        events: [...state.events, action.payload],
      };

    case "PIPELINE_COMPLETED":
      return { ...state, status: "completed" };

    case "PIPELINE_FAILED":
      return { ...state, status: "failed" };

    default:
      return state;
  }
}

// --- Event Mapping ---

function humanMessage(raw: RawPipelineEvent): string {
  const p = raw.payload;
  switch (raw.event_type) {
    case "job_started":
      return `Pipeline started (${p.paper_count} papers)`;
    case "stage_started":
      return `${p.stage} started`;
    case "paper_processed":
      return `Paper processed in ${p.stage} (${p.completed}/${p.total})`;
    case "stage_completed":
      return `${p.stage} completed`;
    case "job_completed":
      return "Pipeline completed";
    case "job_failed":
      return `Pipeline failed: ${p.error}`;
    case "paper_analyzed":
      return `${p.theme_count} themes, ${p.claim_count} claims extracted`;
    case "theme_extracted":
      return `${p.theme_count} themes extracted`;
    case "claim_extracted":
      return `${p.claim_count} claims extracted`;
    case "theme_deduplicated":
      return `Deduplicated to ${p.theme_count} themes`;
    case "review_generated":
      return `Review generated: ${p.title}`;
    default:
      return raw.event_type;
  }
}

function mapAgentEvent(raw: RawPipelineEvent, paperLookup: Map<string, string>): AgentEvent {
  const p = raw.payload;
  const eventType = raw.event_type as AgentEventType;
  const base = {
    id: raw.event_id,
    eventType,
    timestamp: new Date(raw.timestamp).getTime(),
    stage: (p.stage as string) ?? undefined,
    paperId: (p.paper_id as string) ?? undefined,
    paperTitle: paperLookup.get((p.paper_id as string) ?? ""),
    message: (p.message as string) ?? raw.event_type,
    agentName: (p.agent_name as string) ?? "Unknown",
    humanMessage: (p.message as string) ?? raw.event_type,
    technicalMessage: (p.technical_message as string) ?? raw.event_type,
  };

  switch (eventType) {
    case "agent_started":
      return { ...base, eventType: "agent_started", model: (p.model as string) ?? undefined };
    case "agent_tool_call":
      return {
        ...base,
        eventType: "agent_tool_call",
        toolName: (p.tool_name as string) ?? "",
        toolArgsPreview: (p.tool_args_preview as string) ?? undefined,
      };
    case "agent_tool_result":
      return {
        ...base,
        eventType: "agent_tool_result",
        toolName: (p.tool_name as string) ?? "",
        resultLen: (p.result_len as number) ?? 0,
        elapsedMs: (p.elapsed_ms as number) ?? undefined,
      };
    case "agent_content":
      return {
        ...base,
        eventType: "agent_content",
        contentLen: (p.content_len as number) ?? 0,
        contentType: (p.content_type as string) ?? "text",
      };
    case "agent_completed":
      return { ...base, eventType: "agent_completed", elapsedMs: (p.elapsed_ms as number) ?? undefined };
    case "agent_error":
      return {
        ...base,
        eventType: "agent_error",
        error: (p.error as string) ?? "Unknown error",
        errorType: (p.error_type as string) ?? "",
        elapsedMs: (p.elapsed_ms as number) ?? undefined,
      };
    default:
      return { ...base, eventType: "agent_completed" } as AgentEvent;
  }
}

function mapEventToActions(
  raw: RawPipelineEvent,
  paperLookup: Map<string, string>,
): PipelineAction[] {
  const actions: PipelineAction[] = [];
  const p = raw.payload;

  // Agent-level events: construct typed AgentEvent, no reducer side-effects
  if (raw.event_type.startsWith("agent_")) {
    const agentEvent = mapAgentEvent(raw, paperLookup);
    actions.push({ type: "EVENT_RECEIVED", payload: agentEvent });
    return actions;
  }

  // Stage-level events: existing behavior
  const streamEvent: StagePipelineEvent = {
    id: raw.event_id,
    eventType: raw.event_type as StagePipelineEvent["eventType"],
    timestamp: new Date(raw.timestamp).getTime(),
    stage: (p.stage as string) ?? undefined,
    paperId: (p.item_id as string) ?? (p.paper_id as string) ?? undefined,
    paperTitle: paperLookup.get((p.item_id as string) ?? (p.paper_id as string) ?? ""),
    message: humanMessage(raw),
  };
  actions.push({ type: "EVENT_RECEIVED", payload: streamEvent });

  switch (raw.event_type) {
    case "job_started":
      actions.push({
        type: "START_PIPELINE",
        payload: { totalPapers: (p.paper_count as number) ?? 0 },
      });
      break;
    case "stage_started":
      actions.push({ type: "STAGE_STARTED", payload: { stage: p.stage as string } });
      break;
    case "paper_processed":
      actions.push({
        type: "PAPER_PROCESSED",
        payload: {
          stage: p.stage as string,
          paperId: p.item_id as string,
          paperTitle: paperLookup.get(p.item_id as string) ?? (p.item_id as string),
        },
      });
      break;
    case "stage_completed":
      actions.push({ type: "STAGE_COMPLETED", payload: { stage: p.stage as string } });
      break;
    case "job_completed":
      actions.push({ type: "PIPELINE_COMPLETED" });
      break;
    case "job_failed":
      actions.push({ type: "PIPELINE_FAILED", payload: { message: (p.error as string) ?? "Unknown error" } });
      break;
  }

  return actions;
}

// --- WebSocket URL ---

function getWsUrl(jobId: string): string {
  const base = PIPELINE_API_URL.replace(/^http/, "ws");
  return `${base}/jobs/${jobId}/stream`;
}

// --- Reconnection constants ---

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_DELAY = 1000;
const MAX_DELAY = 30000;

// --- Hook ---

export function usePipelineTrace(jobId: string | null) {
  const [state, dispatch] = useReducer(pipelineReducer, INITIAL_STATE);
  const [connectionLost, setConnectionLost] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const terminalRef = useRef(false);
  const hasConnectedRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const paperLookupRef = useRef<Map<string, string>>(new Map());
  const seenEventsRef = useRef(new Set<string>());

  useEffect(() => {
    if (!jobId) return;

    terminalRef.current = false;
    attemptRef.current = 0;
    hasConnectedRef.current = false;
    seenEventsRef.current.clear();
    setConnectionLost(false);

    let cancelled = false;

    function dispatchEvent(raw: RawPipelineEvent) {
      if (seenEventsRef.current.has(raw.event_id)) return;
      seenEventsRef.current.add(raw.event_id);

      const actions = mapEventToActions(raw, paperLookupRef.current);
      for (const action of actions) {
        dispatch(action);
      }

      if (raw.event_type === "job_completed" || raw.event_type === "job_failed") {
        terminalRef.current = true;
      }
    }

    async function init() {
      // Fetch paper titles for lookup
      const papers = await fetchPapers(jobId!);
      if (cancelled) return;
      const lookup = new Map<string, string>();
      for (const p of papers) {
        lookup.set(p.paper_id, p.title || p.filename);
      }
      paperLookupRef.current = lookup;

      // Check job status to determine recovery path
      let status: Awaited<ReturnType<typeof fetchJobStatus>>;
      try {
        status = await fetchJobStatus(jobId!);
      } catch {
        // Job not found — clear and stay idle
        return;
      }
      if (cancelled) return;

      if (status.status === "completed") {
        dispatch({ type: "PIPELINE_COMPLETED" });
        terminalRef.current = true;
        return;
      }

      if (status.status === "failed") {
        dispatch({
          type: "PIPELINE_FAILED",
          payload: { message: status.error ?? "Pipeline failed" },
        });
        terminalRef.current = true;
        return;
      }

      // Running or pending — recover: replay history then connect WS
      dispatch({ type: "RECOVERY_START" });

      try {
        const events = await fetchEvents(jobId!);
        if (cancelled) return;
        for (const event of events) {
          dispatchEvent(event);
        }
      } catch {
        // If events fetch fails, still connect WS to get live events
      }

      if (cancelled) return;
      connect();
    }

    function connect() {
      if (cancelled || terminalRef.current) return;

      const ws = new WebSocket(getWsUrl(jobId!));
      wsRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0;
        hasConnectedRef.current = true;
        setConnectionLost(false);
      };

      ws.onmessage = (e) => {
        let raw: RawPipelineEvent;
        try {
          raw = JSON.parse(e.data);
        } catch {
          return;
        }
        dispatchEvent(raw);
      };

      ws.onclose = () => {
        if (cancelled || terminalRef.current) return;
        if (hasConnectedRef.current) setConnectionLost(true);
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    function scheduleReconnect() {
      if (attemptRef.current >= MAX_RECONNECT_ATTEMPTS) return;
      const delay = Math.min(BASE_DELAY * 2 ** attemptRef.current, MAX_DELAY);
      attemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(connect, delay);
    }

    init();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [jobId]);

  return {
    state,
    connectionLost,
    isRecovering: state.status === "recovering",
    isRunning: state.status === "running",
    isCompleted: state.status === "completed",
    isFailed: state.status === "failed",
  };
}
