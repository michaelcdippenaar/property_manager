import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    toHaveScreenshot: {
      // Allow some pixel difference — signing fields are intentionally different
      maxDiffPixelRatio: 0.05,
      threshold: 0.3,
    },
  },
  use: {
    baseURL: 'http://localhost:5173',
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  // Don't start dev server — expect it to be running
  webServer: undefined,
})
