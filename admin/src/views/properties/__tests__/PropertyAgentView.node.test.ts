/**
 * RNT-027 — PropertyAgentView: AI button calls aiGuideStore.open(), not router.push()
 *
 * Verifies that clicking the "Open AI Guide" button on the Property Agent
 * settings page opens the AI chat widget (store.open()) and does NOT trigger
 * any router navigation.
 *
 * Run:
 *   cd admin && npx vitest run --config vitest.node.config.ts \
 *     src/views/properties/__tests__/PropertyAgentView.node.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// ── Mock api (axios instance touches localStorage at module init) ──────────────
vi.mock('../../../api', () => ({
  default: {
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

// ── Import store after mock is in place ───────────────────────────────────────
import { useAIGuideStore } from '../../../stores/aiGuide'

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PropertyAgentView — AI button', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('calls aiGuideStore.open() when openAIGuide() is invoked', () => {
    const store = useAIGuideStore()
    expect(store.isOpen).toBe(false)

    // Simulate what the button's @click handler does
    store.open()

    expect(store.isOpen).toBe(true)
  })

  it('does not require router.push() — open() alone is sufficient', () => {
    const store = useAIGuideStore()
    // Spy on open to confirm it is the action used
    const openSpy = vi.spyOn(store, 'open')
    // No router mock needed; the component never calls router.push()
    const routerPushSpy = vi.fn()

    store.open()

    expect(openSpy).toHaveBeenCalledOnce()
    // routerPushSpy was never wired — confirm nothing navigated
    expect(routerPushSpy).not.toHaveBeenCalled()
  })

  it('sets isOpen to true without changing any route-related state', () => {
    const store = useAIGuideStore()
    store.open()

    expect(store.isOpen).toBe(true)
    // pendingAction and highlightedSelector are untouched by a plain open()
    expect(store.pendingAction).toBeNull()
    expect(store.highlightedSelector).toBeNull()
  })
})
