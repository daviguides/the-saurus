import { useMemo } from "react";
import type { PipelineState } from "../../core/types/pipeline";
import ProgressBar from "./ProgressBar";
import StageItem from "./StageItem";
import EventStream from "./EventStream";

interface Props {
  state: PipelineState;
}

export default function PipelineTrace({ state }: Props) {
  // Build paper ID → title map from events
  const paperTitles = useMemo(() => {
    const map = new Map<string, string>();
    for (const event of state.events) {
      if (event.paperId && event.paperTitle) {
        map.set(event.paperId, event.paperTitle);
      }
    }
    return map;
  }, [state.events]);

  return (
    <div className="flex flex-col h-full p-6">
      <h2 className="text-lg font-heading font-semibold text-text-primary mb-4">
        Generating Literature Review
      </h2>

      <ProgressBar
        completed={state.progress.completed}
        total={state.progress.total}
        startedAt={state.startedAt}
      />

      <div className="flex-1 overflow-y-auto -mx-2 px-2">
        {state.stages.map((stage) => (
          <StageItem key={stage.id} stage={stage} paperTitles={paperTitles} />
        ))}
      </div>

      <EventStream events={state.events} />
    </div>
  );
}
