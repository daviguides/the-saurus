declare module "theSaurusAssistant/EmbeddedApp" {
  import { ComponentType } from "react";

  export interface EmbeddedAppProps {
    isOpen?: boolean;
    isDark?: boolean;
    onClose?: () => void;
    context?: {
      jobId: string | null;
      currentView: "papers" | "review";
    };
  }

  const EmbeddedApp: ComponentType<EmbeddedAppProps>;
  export default EmbeddedApp;
}
