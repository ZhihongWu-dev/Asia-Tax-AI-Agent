import { defineConfig, devices } from "@playwright/test";

const apiPort = process.env.FSIE_TEST_API_PORT || "8001";
const webPort = process.env.FSIE_TEST_WEB_PORT || "5174";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: { baseURL: `http://127.0.0.1:${webPort}`, trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
      },
    },
  ],
  webServer: [
    {
      command: `"${process.env.FSIE_TEST_PYTHON || "python"}" ../../tests/chat/serve_browser.py`,
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: false,
    },
    {
      command:
        `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${webPort}`,
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      env: { FSIE_WEB_API_URL: `http://127.0.0.1:${apiPort}` },
    },
  ],
});
