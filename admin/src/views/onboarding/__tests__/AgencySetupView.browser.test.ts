/**
 * AgencySetupView — onboarding wizard smoke test.
 *
 * Covers:
 *   1. Component mounts and pre-fills `name` from the auth store agency
 *   2. Step 1 → Step 2 transition (PUTs /auth/agency/)
 *   3. Step 2 → Step 3 transition (agency flow)
 *   4. Step 3 finish → POSTs /auth/agency/onboarding/complete/ with no invites
 *   5. Individual flow finishes after step 2 (no team step)
 *
 * Run:
 *   cd admin && npx vitest run src/views/onboarding/AgencySetupView.browser.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'

const { mockGet, mockPost, mockPut, mockIcons } = vi.hoisted(() => {
  return {
    mockGet: vi.fn(),
    mockPost: vi.fn(),
    mockPut: vi.fn(),
    mockIcons: {
      AlertCircle: { template: '<span />' },
      ChevronLeft: { template: '<span />' },
      ChevronRight: { template: '<span />' },
      Loader2: { template: '<span />' },
      Plus: { template: '<span />' },
      X: { template: '<span />' },
    },
  }
})

vi.mock('../../../api', () => ({
  default: {
    get: mockGet,
    post: mockPost,
    put: mockPut,
  },
}))
vi.mock('lucide-vue-next', () => mockIcons)

import AgencySetupView from '../AgencySetupView.vue'
import { useAuthStore } from '../../../stores/auth'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/onboarding', name: 'onboarding', component: AgencySetupView },
    ],
  })
}

async function mountView(accountType: 'agency' | 'individual' = 'agency') {
  const router = makeRouter()
  const pinia = createPinia()
  setActivePinia(pinia)

  // Hydrate the auth store BEFORE mount so onMounted picks up the agency.
  const auth = useAuthStore()
  auth.user = { id: 1, email: 't@t.com', full_name: 'T T', role: 'agency_admin' } as any
  auth.agency = {
    id: 1,
    account_type: accountType,
    name: 'Acme Estates',
    onboarding_completed_at: null,
  } as any

  await router.push('/onboarding')
  await router.isReady()

  const wrapper = mount(AgencySetupView, {
    global: { plugins: [router, pinia] },
  })

  await flushPromises()
  return { wrapper, router, auth }
}

beforeEach(() => {
  mockGet.mockReset()
  mockPost.mockReset()
  mockPut.mockReset()
})

describe('AgencySetupView — mount', () => {
  it('mounts and pre-fills name from the auth store agency', async () => {
    const { wrapper } = await mountView('agency')
    const nameInput = wrapper.find<HTMLInputElement>('input[type="text"]')
    expect(nameInput.exists()).toBe(true)
    expect(nameInput.element.value).toBe('Acme Estates')
  })
})

describe('AgencySetupView — agency 3-step flow', () => {
  it('walks through all 3 steps and POSTs onboarding/complete at the end', async () => {
    mockPut.mockResolvedValue({ data: {} })
    mockPost.mockResolvedValue({ data: {} })
    mockGet.mockResolvedValue({ data: { id: 1, account_type: 'agency', name: 'Acme', onboarding_completed_at: '2026-05-07T12:00:00Z' } })

    const { wrapper, router } = await mountView('agency')

    // Step 1 → Step 2
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(mockPut).toHaveBeenCalledWith('/auth/agency/', expect.any(FormData), expect.any(Object))

    // Step 2 → Step 3
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // Step 3 → finish
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const completeCalls = mockPost.mock.calls.filter(([url]) => url === '/auth/agency/onboarding/complete/')
    expect(completeCalls).toHaveLength(1)
    expect(router.currentRoute.value.path).toBe('/')
  })
})

describe('AgencySetupView — individual flow', () => {
  it('finishes after step 2 (no team step)', async () => {
    mockPut.mockResolvedValue({ data: {} })
    mockPost.mockResolvedValue({ data: {} })
    mockGet.mockResolvedValue({ data: { id: 1, account_type: 'individual', name: 'Sam Properties', onboarding_completed_at: '2026-05-07T12:00:00Z' } })

    const { wrapper, router } = await mountView('individual')

    // Step 1 → Step 2
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    // Step 2 → finish (only 2 steps for individual)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const completeCalls = mockPost.mock.calls.filter(([url]) => url === '/auth/agency/onboarding/complete/')
    expect(completeCalls).toHaveLength(1)
    expect(router.currentRoute.value.path).toBe('/')
  })
})
