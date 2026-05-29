import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxyTarget = process.env.E2E_API_PROXY ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": apiProxyTarget,
      "/employees": apiProxyTarget,
      "/skills": apiProxyTarget,
      "/jobs": apiProxyTarget,
      "/dispatch-runs": apiProxyTarget,
      "/settings": apiProxyTarget,
      "/health": apiProxyTarget,
      "/backups": apiProxyTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    exclude: ["**/node_modules/**", "**/e2e/**"],
  },
});
