import { NavLink } from "react-router";
import { Upload, FileText, BookOpen } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/papers", label: "Papers", icon: FileText },
  { to: "/review", label: "Review", icon: BookOpen },
];

export default function Sidebar() {
  const handleUploadClick = () => {
    window.dispatchEvent(new CustomEvent("open-upload-modal"));
  };

  return (
    <aside
      className="flex flex-col items-center border-r border-border bg-surface shrink-0 py-3 gap-1"
      style={{ width: "var(--sidebar-width)" }}
    >
      <button
        type="button"
        onClick={handleUploadClick}
        className="flex items-center justify-center w-10 h-10 rounded-lg text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors duration-200 mb-2"
        title="Upload Papers"
      >
        <Upload size={20} />
      </button>

      <div className="w-8 border-t border-border mb-2" />

      <nav className="flex flex-col items-center gap-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              clsx(
                "flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200",
                isActive
                  ? "bg-primary text-white"
                  : "text-text-secondary hover:text-primary hover:bg-primary/10",
              )
            }
          >
            <Icon size={20} />
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
