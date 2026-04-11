import { Outlet, useLocation } from "react-router";
import clsx from "clsx";
import Header from "./Header";
import Sidebar from "./Sidebar";
import { AssistantProvider, useAssistant } from "../../core/context/AssistantContext";
import FederatedAssistant from "../assistant/FederatedAssistant";

function LayoutInner() {
  const { isOpen } = useAssistant();
  const location = useLocation();

  return (
    <div className="flex h-dvh bg-bg text-text-primary font-body">
      <Sidebar />
      <div
        className={clsx(
          "flex flex-1 flex-col min-w-0 transition-all duration-300 ease-in-out",
          isOpen && "lg:mr-[var(--drawer-width)]",
        )}
      >
        <Header />
        <main className="flex-1 overflow-y-auto">
          <div key={location.pathname} className="h-full animate-[viewFadeIn_150ms_ease]">
            <Outlet />
          </div>
        </main>
      </div>
      <FederatedAssistant />
    </div>
  );
}

export default function AppLayout() {
  return (
    <AssistantProvider>
      <LayoutInner />
    </AssistantProvider>
  );
}
