import { MessageCircle } from "lucide-react";

export default function Header() {
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
        className="flex items-center justify-center w-8 h-8 rounded-md text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors duration-200"
        title="Open Assistant"
        disabled
      >
        <MessageCircle size={18} />
      </button>
    </header>
  );
}
