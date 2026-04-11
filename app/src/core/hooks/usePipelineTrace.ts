import { useReducer, useCallback, useRef } from "react";
import type {
  PipelineState,
  PipelineAction,
  PipelineStageState,
} from "../types/pipeline";
import { PIPELINE_STAGES } from "../types/pipeline";
import { startMockPipeline } from "../../mocks/pipeline-events";

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
    case "START_PIPELINE":
      return {
        ...state,
        status: "running",
        startedAt: Date.now(),
        progress: { completed: 0, total: action.payload.totalPapers },
        stages: state.stages.map((s) => ({
          ...s,
          totalPapers: action.payload.totalPapers,
          processedPapers: [],
          status: "pending",
        })),
        events: [],
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

export function usePipelineTrace() {
  const [state, dispatch] = useReducer(pipelineReducer, INITIAL_STATE);
  const cleanupRef = useRef<(() => void) | null>(null);

  const startPipeline = useCallback(
    (papers: { id: string; title: string }[]) => {
      if (cleanupRef.current) cleanupRef.current();
      cleanupRef.current = startMockPipeline(papers, dispatch);
    },
    [],
  );

  const isRunning = state.status === "running";
  const isCompleted = state.status === "completed";

  return { state, isRunning, isCompleted, startPipeline };
}
