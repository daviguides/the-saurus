import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Terminal } from "lucide-react";
import type { PipelineEvent } from "../../core/types/pipeline";

interface Props {
  events: PipelineEvent[];
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour12: false });
}

export default function EventStream({ events }: Props) {
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  useEffect(() => {
    if (expanded && isAtBottomRef.current && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [events, expanded]);

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface mt-4">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-bg/50 transition-colors"
      >
        <Terminal size={14} className="text-text-muted" />
        <span className="text-sm font-medium text-text-primary flex-1">
          Event Stream
        </span>
        <span className="text-xs font-mono text-text-muted bg-bg px-1.5 py-0.5 rounded">
          {events.length}
        </span>
        {expanded ? (
          <ChevronDown size={14} className="text-text-muted" />
        ) : (
          <ChevronRight size={14} className="text-text-muted" />
        )}
      </button>

      {/* Animated expand/collapse via CSS grid trick */}
      <div
        className="grid transition-[grid-template-rows] duration-200 ease"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden min-h-0">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="max-h-48 overflow-y-auto border-t border-border bg-bg/30 px-4 py-2 space-y-0.5"
          >
            {events.map((event) => (
              <div key={event.id} className="flex gap-2 text-xs font-mono leading-5">
                <span className="text-text-muted flex-shrink-0">
                  [{formatTime(event.timestamp)}]
                </span>
                <span className="text-primary/70 flex-shrink-0">
                  {event.eventType}
                </span>
                <span className="text-text-secondary truncate">
                  {event.message}
                </span>
              </div>
            ))}
            {events.length === 0 && (
              <p className="text-xs text-text-muted italic">
                Waiting for events...
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
