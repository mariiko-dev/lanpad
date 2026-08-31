import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  build: {
    // The agent serves from here and only from here.
    outDir: "../src/lanpad/web",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        console: resolve(__dirname, "console.html"),
      },
      output: {
        // The agent grants year-long caching only to hex-hashed names
        // (http.py `_HASHED_NAME`). Rollup's default alphabet never
        // matches, so upgrades would never reach a paired phone.
        hashCharacters: "hex",
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  test: { environment: "node" },
});
