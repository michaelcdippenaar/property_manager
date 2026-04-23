import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for the Klikk Admin SPA E2E suite.
 *
 * Two named projects:
 *   - "local"   — dev server (localhost:5173 + localhost:8000 API)
 *   - "staging" — staging environment (env vars override URLs)
 *
 * Screenshots and video are captured on failure automatically.
 * The "e2e" CI workflow runs the "staging" project nightly and on deploy.
 */

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";

export default defineConfig({
  testDir: ".",
  outputDir: "test-results",
  fullyParallel: false, // golden-path tests depend on shared state; run serially
  retries: process.env.CI ? 1 : 0,
  workers: 1,

  use: {
    baseURL: BASE_URL,
    // Attach to every test via fixture
    extraHTTPHeaders: {
      Accept: "application/json",
    },
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "local",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "staging",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.E2E_BASE_URL ?? "https://app.klikk.co.za",
      },
    },
  ],
});

export { API_URL };
