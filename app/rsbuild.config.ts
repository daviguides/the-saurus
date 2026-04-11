import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";
import { pluginModuleFederation } from "@module-federation/rsbuild-plugin";

export default defineConfig({
  plugins: [
    pluginReact(),
    pluginModuleFederation({
      name: "theSaurusApp",
      dts: false,
      remotes: {
        theSaurusAssistant:
          "theSaurusAssistant@http://localhost:5174/remoteEntry.js",
      },
      shared: {
        react: { singleton: true, requiredVersion: "^19.0.0", eager: true },
        "react-dom": {
          singleton: true,
          requiredVersion: "^19.0.0",
          eager: true,
        },
        "socket.io-client": {
          singleton: true,
          requiredVersion: "^4.0.0",
          eager: true,
        },
      },
    }),
  ],
  source: {
    entry: {
      index: "./src/main.tsx",
    },
  },
  server: {
    port: 5173,
    historyApiFallback: true,
  },
  html: {
    title: "The Saurus",
    tags: [
      {
        tag: "script",
        children: `(function(){var t=localStorage.getItem('thesaurus:theme');if(t==='light')return;if(t==='dark'||window.matchMedia('(prefers-color-scheme:dark)').matches||!window.matchMedia('(prefers-color-scheme:light)').matches){document.documentElement.classList.add('dark')}})()`,
        append: false,
        head: true,
      },
    ],
  },
});
