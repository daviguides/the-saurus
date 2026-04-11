/**
 * Shell configuration types and presets for standalone/embedded modes.
 *
 * Exposed as federated module `./config` for host-side type access.
 */

export type RuntimeMode = "standalone" | "embedded";

export interface ShellFeatures {
  darkModeToggle: boolean;
  orchestrationTrace: boolean;
}

export interface ShellConfig {
  runtime: RuntimeMode;
  features: ShellFeatures;
}

export const STANDALONE_CONFIG: ShellConfig = {
  runtime: "standalone",
  features: {
    darkModeToggle: true,
    orchestrationTrace: true,
  },
};

export const EMBEDDED_CONFIG: ShellConfig = {
  runtime: "embedded",
  features: {
    darkModeToggle: false,
    orchestrationTrace: false,
  },
};
