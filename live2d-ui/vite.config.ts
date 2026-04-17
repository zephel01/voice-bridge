import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Electron からは file:// でビルド後の dist/ を読むため base を './' にする
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  optimizeDeps: {
    include: [
      "pixi.js",
      "pixi-live2d-display/cubism4",
    ],
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    target: "chrome122",
    rollupOptions: {
      output: {
        manualChunks: {
          pixi: ["pixi.js"],
          live2d: ["pixi-live2d-display"],
        },
      },
    },
  },
});
