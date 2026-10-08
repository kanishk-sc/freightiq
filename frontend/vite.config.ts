import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: {
        "/api/review-tasks": {
          target: env.REVIEW_PROXY_TARGET || "http://127.0.0.1:8001",
          changeOrigin: true,
        },
        "/api": {
          target: env.FASTAPI_PROXY_TARGET || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
