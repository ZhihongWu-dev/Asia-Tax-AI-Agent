import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests', testMatch: 'consultation.spec.ts', workers: 1, timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:5185', ...devices['Desktop Chrome'], channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
  webServer: [
    {command: `"${process.env.FSIE_TEST_PYTHON || '../../.venv/bin/python'}" ../../tests/consultation/serve_browser.py`, url:'http://127.0.0.1:8012/health', reuseExistingServer:false},
    {command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5185', url:'http://127.0.0.1:5185', reuseExistingServer:false, env:{FSIE_WEB_API_URL:'http://127.0.0.1:8012'}},
  ],
});
