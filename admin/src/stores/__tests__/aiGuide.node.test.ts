/**
 * RNT-AI-004 — AI Guide store: close() regression test
 *
 * Verifies that calling close() after open() fully resets all UI-side-effect
 * state so that navigating away after closing the panel doesn't leave a stale
 * highlight, pending action, or error behind.
 *
 * Run:
 *   cd admin && npx vitest run --config vitest.node.config.ts src/stores/__tests__/aiGuide.node.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// ── Mock api before importing the store ──────────────────────────────────────
// The store imports api (axios instance) which touches localStorage at module
// init time. We stub the entire module so Node doesn't need a DOM.
vi.mock('../../api', () => ({
  default: {
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

// ── Import store after the mock is in place ───────────────────────────────────
import { useAIGuideStore } from '../aiGuide'

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('useAIGuideStore — close()', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('resets isOpen to false', () => {
    const store = useAIGuideStore()
    store.open()
    expect(store.isOpen).toBe(true)
    store.close()
    expect(store.isOpen).toBe(false)
  })

  it('clears highlightedSelector on close', () => {
    const store = useAIGuideStore()
    store.open()
    store.highlight('[data-guide="add-property"]')
    expect(store.highlightedSelector).toBe('[data-guide="add-property"]')
    store.close()
    expect(store.highlightedSelector).toBeNull()
  })

  it('clears pendingAction on close', () => {
    const store = useAIGuideStore()
    store.open()
    store.pendingAction = { route: '/properties', label: 'Properties', confirmationRequired: false }
    expect(store.pendingAction).not.toBeNull()
    store.close()
    expect(store.pendingAction).toBeNull()
  })

  it('clears error on close', () => {
    const store = useAIGuideStore()
    store.open()
    store.error = 'Network error'
    expect(store.error).toBe('Network error')
    store.close()
    expect(store.error).toBeNull()
  })

  it('resets all four state pieces in a single close() call (regression: close→navigate crash)', () => {
    // Simulates the crash scenario: open chat, receive a response that sets
    // highlightedSelector + pendingAction, then close and navigate away.
    // All four pieces must be clean so the route-change watcher in AIGuide.vue
    // does not try to query a stale selector on the new route's DOM.
    const store = useAIGuideStore()
    store.open()
    store.highlight('[data-guide="add-property"]')
    store.pendingAction = { route: '/properties', label: 'Add Property', confirmationRequired: false }
    store.error = 'Some stale error'

    store.close()

    expect(store.isOpen).toBe(false)
    expect(store.highlightedSelector).toBeNull()
    expect(store.pendingAction).toBeNull()
    expect(store.error).toBeNull()
  })
})
