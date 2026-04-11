import { useMemo } from "react";
import { Loader2, WifiOff } from "lucide-react";
import type { PipelineState } from "../../core/types/pipeline";
import ProgressBar from "./ProgressBar";
import StageItem from "./StageItem";
import OrchestrationTrace from "./OrchestrationTrace";

interface Props {
  state: PipelineState;
  connectionLost?: boolean;
}

export default function PipelineTrace({ state, connectionLost }: Props) {
  const hasEvents = state.events.length > 0;
  const isLoading = !hasEvents && state.status !== "completed";

  // Track last processed paper title per stage
  const lastProcessedPerStage = useMemo(() => {
    const map = new Map<string, string>();
    for (const event of state.events) {
      if (event.eventType === "paper_processed" && event.stage && event.paperTitle) {
        map.set(event.stage, event.paperTitle);
      }
    }
    return map;
  }, [state.events]);

  return (
    <div className="relative flex flex-col h-full p-6">
      {/* Connection lost banner */}
      <div
        className={`overflow-hidden transition-all duration-300 ease ${
          connectionLost
            ? "max-h-12 opacity-100 mb-3"
            : "max-h-0 opacity-0 mb-0"
        }`}
      >
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-accent-bg border border-accent/30 text-sm text-text-secondary">
          <WifiOff size={14} className="text-accent shrink-0" />
          Connection lost — Reconnecting...
        </div>
      </div>

      {/* Loading state — crossfades out when first event arrives */}
      <div
        className={`absolute inset-0 flex flex-col items-center justify-center gap-3 transition-opacity duration-300 ease ${
          isLoading ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        <Loader2 size={32} className="text-primary animate-spin" />
        <p className="text-sm text-text-secondary">Starting pipeline...</p>
      </div>

      {/* Main content — crossfades in when first event arrives */}
      <div
        className={`flex flex-col h-full transition-opacity duration-300 ease ${
          hasEvents ? "opacity-100" : "opacity-0"
        }`}
      >
        <h2 className="text-lg font-heading font-semibold text-text-primary mb-4">
          Generating Literature Review
        </h2>

        <ProgressBar
          stages={state.stages}
          startedAt={state.startedAt}
          totalPapers={state.progress.total}
        />

        <div className="flex-1 overflow-y-auto -mx-2 px-2">
          {state.stages.map((stage) => (
            <StageItem
              key={stage.id}
              stage={stage}
              lastProcessedTitle={lastProcessedPerStage.get(stage.id)}
            />
          ))}
        </div>

        <OrchestrationTrace
          events={state.events}
          isActive={state.status === "running"}
        />
      </div>
    </div>
  );
}
