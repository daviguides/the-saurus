import type { PipelineAction, PipelineEvent } from "../core/types/pipeline";
import { PIPELINE_STAGES } from "../core/types/pipeline";

interface MockPaper {
  id: string;
  title: string;
}

function createEvent(
  eventType: string,
  stage: string,
  message: string,
  paperId?: string,
  paperTitle?: string,
): PipelineEvent {
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

    // Process each paper in this stage
    for (const paper of papers) {
      const paperDelay = 200 + Math.random() * 400;
      schedule(paperDelay, () => {
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
