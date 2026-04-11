import { MessageCircle } from "lucide-react";
import clsx from "clsx";
import { useAssistant } from "../../core/context/AssistantContext";

export default function Header() {
  const { isOpen, toggle } = useAssistant();

  return (
    <header
      className="flex items-center justify-between px-4 border-b border-border shrink-0"
      style={{ height: "var(--header-height)" }}
    >
      <h1 className="text-lg font-semibold font-heading text-text-primary tracking-tight">
        The Saurus
      </h1>
      <button
        type="button"
        onClick={toggle}
        className={clsx(
          "flex items-center justify-center w-8 h-8 rounded-md transition-colors duration-200",
          isOpen
            ? "text-primary bg-primary/10"
            : "text-text-secondary hover:text-primary hover:bg-primary/10",
        )}
        title={isOpen ? "Close Assistant" : "Open Assistant"}
      >
        <MessageCircle size={18} />
      </button>
    </header>
  );
}
