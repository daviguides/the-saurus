import type { PipelineAction, StagePipelineEvent, AgentEvent, AgentEventType } from "../core/types/pipeline";
import { PIPELINE_STAGES } from "../core/types/pipeline";

interface MockPaper {
  id: string;
  title: string;
}

function createEvent(
  eventType: StagePipelineEvent["eventType"],
  stage: string,
  message: string,
  paperId?: string,
  paperTitle?: string,
): StagePipelineEvent {
  return {
    id: crypto.randomUUID(),
    eventType,
    timestamp: Date.now(),
    stage,
    paperId,
    paperTitle,
    message,
  };
}

const STAGE_AGENT_MAP: Record<string, string> = {
  paper_analysis: "PaperAnalyzer",
  theme_dedup: "ThemeDedup",
  theme_review: "ThemeReviewer",
  aggregation: "Aggregator",
};

function createAgentEvent(
  eventType: AgentEventType,
  agentName: string,
  stage: string,
  humanMessage: string,
  extra?: Partial<AgentEvent>,
): AgentEvent {
  const base = {
    id: crypto.randomUUID(),
    eventType,
    timestamp: Date.now(),
    stage,
    message: humanMessage,
    agentName,
    humanMessage,
    technicalMessage: `[${agentName}] ${eventType}`,
  };
  // Cast through unknown to satisfy discriminated union
  return { ...base, ...extra } as unknown as AgentEvent;
}

export function startMockPipeline(
  papers: MockPaper[],
  dispatch: (action: PipelineAction) => void,
): () => void {
  const timers: ReturnType<typeof setTimeout>[] = [];
  let delay = 0;

  const schedule = (ms: number, fn: () => void) => {
    delay += ms;
    timers.push(setTimeout(fn, delay));
  };

  // Start pipeline
  schedule(100, () => {
    dispatch({ type: "START_PIPELINE", payload: { totalPapers: papers.length } });
    dispatch({
      type: "EVENT_RECEIVED",
      payload: createEvent("job_started", "", "Pipeline started"),
    });
  });

  // Process each stage
  for (const stage of PIPELINE_STAGES) {
    // Stage start
    schedule(800, () => {
      dispatch({ type: "STAGE_STARTED", payload: { stage: stage.id } });
      dispatch({
        type: "EVENT_RECEIVED",
        payload: createEvent("stage_started", stage.id, `${stage.label} started`),
      });
    });

    // Process each paper in this stage with agent events
    const agentName = STAGE_AGENT_MAP[stage.id] ?? "Agent";
    for (const paper of papers) {
      // Agent started
      schedule(100, () => {
        dispatch({
          type: "EVENT_RECEIVED",
          payload: createAgentEvent(
            "agent_started", agentName, stage.id,
            `Analyzing '${paper.title}'...`,
            { paperId: paper.id, paperTitle: paper.title, model: "gpt-4o" } as Partial<AgentEvent>,
          ),
        });
      });

      // Agent tool call
      schedule(50 + Math.random() * 100, () => {
        dispatch({
          type: "EVENT_RECEIVED",
          payload: createAgentEvent(
            "agent_tool_call", agentName, stage.id,
            "Gathering information...",
            { paperId: paper.id, toolName: "structured_output", toolArgsPreview: `{paper_id: "${paper.id}"}` } as Partial<AgentEvent>,
          ),
        });
      });

      // Agent tool result
      schedule(100 + Math.random() * 200, () => {
        dispatch({
          type: "EVENT_RECEIVED",
          payload: createAgentEvent(
            "agent_tool_result", agentName, stage.id,
            "Information retrieved",
            { paperId: paper.id, toolName: "structured_output", resultLen: 1200 + Math.round(Math.random() * 3000), elapsedMs: 200 + Math.round(Math.random() * 800) } as Partial<AgentEvent>,
          ),
        });
      });

      // Agent completed
      schedule(50, () => {
        dispatch({
          type: "EVENT_RECEIVED",
          payload: createAgentEvent(
            "agent_completed", agentName, stage.id,
            "Analysis complete",
            { paperId: paper.id, elapsedMs: 500 + Math.round(Math.random() * 1500) } as Partial<AgentEvent>,
          ),
        });
      });

      // Paper processed (stage-level)
      schedule(50, () => {
        dispatch({
          type: "PAPER_PROCESSED",
          payload: { stage: stage.id, paperId: paper.id, paperTitle: paper.title },
        });
        dispatch({
          type: "EVENT_RECEIVED",
          payload: createEvent(
            "paper_processed",
            stage.id,
            `${paper.title} processed`,
            paper.id,
            paper.title,
          ),
        });
      });
    }

    // Stage complete
    schedule(300, () => {
      dispatch({ type: "STAGE_COMPLETED", payload: { stage: stage.id } });
      dispatch({
        type: "EVENT_RECEIVED",
        payload: createEvent("stage_completed", stage.id, `${stage.label} completed`),
      });
    });
  }

  // Pipeline complete
  schedule(500, () => {
    dispatch({ type: "PIPELINE_COMPLETED" });
    dispatch({
      type: "EVENT_RECEIVED",
      payload: createEvent("job_completed", "", "Pipeline completed successfully"),
    });
  });

  return () => {
    timers.forEach(clearTimeout);
  };
}
