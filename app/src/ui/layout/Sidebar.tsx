import { NavLink } from "react-router";
import { Upload, FileText, BookOpen } from "lucide-react";
import clsx from "clsx";
import { useReview } from "../../core/hooks/useReview";

const navItems = [
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/papers", label: "Papers", icon: FileText },
  { to: "/review", label: "Review", icon: BookOpen },
];

export default function Sidebar() {
  const { hasReview } = useReview();

  return (
    <aside
      className="flex flex-col items-center border-r border-border bg-surface shrink-0 py-3 gap-1"
      style={{ width: "var(--sidebar-width)" }}
    >
      <nav className="flex flex-col items-center gap-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              clsx(
                "relative flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200",
                isActive
                  ? "bg-primary text-white"
                  : "text-text-secondary hover:text-primary hover:bg-primary/10",
              )
            }
          >
            <Icon size={20} />
            {to === "/review" && hasReview && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent animate-[scaleIn_300ms_ease-out]" />
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
