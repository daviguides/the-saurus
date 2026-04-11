import type { ConnectionStatus } from "../../core/types/chat";

interface Props {
  status: ConnectionStatus;
}

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connecting: "bg-accent",
  connected: "bg-success",
  disconnected: "bg-text-muted",
  error: "bg-error",
};

export default function Header({ status }: Props) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-text-primary">
          AnswerThis Assistant
        </h1>
      </div>
      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <span
          className={`w-2 h-2 rounded-full ${STATUS_COLOR[status]}`}
        />
        {status}
      </div>
    </header>
  );
}
