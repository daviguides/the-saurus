import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";
import { pluginModuleFederation } from "@module-federation/rsbuild-plugin";
import path from "path";

const isFederatedBuild = process.env.RSBUILD_MF_REMOTE === "true";
const isDev = process.env.NODE_ENV !== "production";

const moduleFederationConfig = {
  name: "theSaurusAssistant",
  filename: "remoteEntry.js",
  dts: isDev ? false : { generateTypes: true },
  exposes: {
    "./EmbeddedApp": "./src/shells/embedded/App.tsx",
    "./config": "./src/core/config/ShellConfig.ts",
  },
  shared: {
    react: {
      singleton: true,
      eager: true,
      requiredVersion: "^19.0.0",
    },
    "react-dom": {
      singleton: true,
      eager: true,
      requiredVersion: "^19.0.0",
    },
    "socket.io-client": {
      singleton: true,
      eager: true,
      requiredVersion: "^4.0.0",
    },
  },
};

export default defineConfig({
  plugins: [
    pluginReact(),
    ...(isFederatedBuild
      ? [pluginModuleFederation(moduleFederationConfig)]
      : []),
  ],

  source: {
    entry: {
      index: "./src/main.tsx",
    },
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  server: {
    port: 5174,
    headers: {
      "Access-Control-Allow-Origin": "*",
    },
  },

  dev: {
    client: isFederatedBuild ? { overlay: false } : undefined,
  },

  output: {
    injectStyles: isFederatedBuild && isDev,
  },

  html: {
    title: "AnswerThis Assistant",
  },
});
