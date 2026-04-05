import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { playwright } from '@vitest/browser-playwright'

export default defineConfig({
  plugins: [vue()],
  define: {
    'process.env': {},
  },
  test: {
    browser: {
      enabled: true,
      provider: playwright(),
      instances: [
        { browser: 'chromium' },
      ],
    },
    include: ['src/**/*.browser.test.ts'],
    // Give TipTap pagination time to settle
    testTimeout: 30_000,
  },
})
