/**
 * RNT-027 — PropertyAgentView: AI button calls aiGuideStore.open(), not router.push()
 *
 * Mounts the real PropertyAgentView component in a Playwright browser context,
 * clicks the [data-testid="open-ai-guide"] button, and asserts:
 *   1. aiGuideStore.isOpen flips to true  (store.open() was invoked via @click)
 *   2. useRouter().push() is never called (no route navigation)
 *   3. Idempotent: clicking while already open leaves isOpen === true
 *
 * Run:
 *   cd admin && npx vitest run \
 *     src/__tests__/browser/PropertyAgentView-ai-button.browser.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ── Mock the api module (axios touches localStorage at module-init time) ──────
vi.mock('../../api', () => ({
  default: {
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

// ── Mock vue-router: provides a push spy the component could call ─────────────
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: {}, query: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

// ── Imports after mocks ───────────────────────────────────────────────────────
import PropertyAgentView from '../../views/properties/PropertyAgentView.vue'
import { useAIGuideStore } from '../../stores/aiGuide'

// ── Helpers ───────────────────────────────────────────────────────────────────

function mountView() {
  return mount(PropertyAgentView, { attachTo: document.body })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PropertyAgentView — AI button', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    mockPush.mockClear()
  })

  it('clicking the button opens the AI guide widget (isOpen becomes true)', async () => {
    const wrapper = mountView()
    const store = useAIGuideStore()

    expect(store.isOpen).toBe(false)

    const btn = wrapper.find('[data-testid="open-ai-guide"]')
    expect(btn.exists()).toBe(true)

    await btn.trigger('click')

    expect(store.isOpen).toBe(true)

    wrapper.unmount()
  })

  it('clicking the button does NOT call router.push()', async () => {
    const wrapper = mountView()

    await wrapper.find('[data-testid="open-ai-guide"]').trigger('click')

    expect(mockPush).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('clicking when already open leaves isOpen === true (idempotent open)', async () => {
    const wrapper = mountView()
    const store = useAIGuideStore()

    // First click — opens
    await wrapper.find('[data-testid="open-ai-guide"]').trigger('click')
    expect(store.isOpen).toBe(true)

    // Second click — open() is idempotent; isOpen must remain true
    await wrapper.find('[data-testid="open-ai-guide"]').trigger('click')
    expect(store.isOpen).toBe(true)

    wrapper.unmount()
  })
})
