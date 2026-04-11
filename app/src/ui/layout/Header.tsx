import { MessageCircle, Sun, Moon } from "lucide-react";
import clsx from "clsx";
import { useAssistant } from "../../core/context/AssistantContext";
import { useTheme } from "../../core/hooks/useTheme";

export default function Header() {
  const { isOpen, toggle } = useAssistant();
  const { theme, toggle: toggleTheme } = useTheme();

  const iconButtonClass =
    "flex items-center justify-center w-8 h-8 rounded-md transition-colors duration-200 text-text-secondary hover:text-primary hover:bg-primary/10";

  return (
    <header
      className="flex items-center justify-between px-4 border-b border-border shrink-0"
      style={{ height: "var(--header-height)" }}
    >
      <h1 className="text-lg font-semibold font-heading text-text-primary tracking-tight">
        The Saurus
      </h1>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={toggleTheme}
          className={iconButtonClass}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
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
      </div>
    </header>
  );
}
