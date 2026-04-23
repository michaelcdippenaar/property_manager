/**
 * Vitest config for Node-environment tests (no browser / DOM needed).
 *
 * These tests need filesystem access (e.g. reading content/product/features.yaml)
 * and must NOT run in the browser sandbox used by vitest.config.ts.
 *
 * Run all node tests:
 *   cd admin && npx vitest run --config vitest.node.config.ts
 *
 * Run a specific test:
 *   cd admin && npx vitest run --config vitest.node.config.ts src/composables/__tests__/useFeatureFlags.drift.test.ts
 */
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.node.test.ts', 'src/**/*.drift.test.ts'],
    testTimeout: 10_000,
  },
})
