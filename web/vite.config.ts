import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

const HOST_API = process.env.CAMERACOMMANDER_HOST ?? "http://localhost:8000";
const HOST_WS = HOST_API.replace(/^http/, "ws");

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: HOST_API, changeOrigin: true },
      "/ws": { target: HOST_WS, ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.{test,spec}.ts"],
  },
});
