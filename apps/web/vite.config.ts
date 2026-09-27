import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target:
          loadEnv(mode, ".", "FSIE_WEB_").FSIE_WEB_API_URL ||
          "http://127.0.0.1:8000",
        changeOrigin: false,
        timeout: 65000,
        proxyTimeout: 60000,
      },
    },
  },
}));
