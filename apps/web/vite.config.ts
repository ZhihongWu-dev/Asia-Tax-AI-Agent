import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// /api goes to the web host (apps/api/server.py); TAXRORA_API_URL points it elsewhere.
export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, ".", "TAXRORA_").TAXRORA_API_URL || "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: { "/api": { target, changeOrigin: false } },
    },
  };
});
