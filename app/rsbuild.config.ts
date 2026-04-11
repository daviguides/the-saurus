import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";

export default defineConfig({
  plugins: [pluginReact()],
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
