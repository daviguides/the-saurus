import type { ConnectionStatus } from "../../core/types/chat";

interface Props {
  status: ConnectionStatus;
}

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connecting: "bg-yellow-500",
  connected: "bg-green-500",
  disconnected: "bg-gray-500",
  error: "bg-red-500",
};

export default function Header({ status }: Props) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-gray-100">
          AnswerThis Assistant
        </h1>
      </div>
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <span
          className={`w-2 h-2 rounded-full ${STATUS_COLOR[status]}`}
        />
        {status}
      </div>
    </header>
  );
}
