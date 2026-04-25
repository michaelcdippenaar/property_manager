/**
 * EmailOtpVerifyView — unit tests
 *
 * Covers:
 *   1. Component mounts cleanly (no thrown errors)
 *   2. Calls POST /auth/2fa/email-send/ on mount (auto-send OTP)
 *   3. Renders the 6-digit code input
 *   4. Auto-submits (calls /auth/2fa/email-verify/) when 6 digits are entered
 *   5. Displays the resend cooldown timer after OTP is sent
 *   6. Shows error state on a failed verify response
 *
 * Run:
 *   cd admin && npx vitest run src/views/auth/EmailOtpVerifyView.browser.test.ts
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'

// ---------------------------------------------------------------------------
// vi.hoisted ensures the mock function reference is available when vi.mock
// factory is hoisted to the top of the file by the Playwright browser mocker.
// ---------------------------------------------------------------------------
const { mockPost, mockIcons } = vi.hoisted(() => {
  return {
    mockPost: vi.fn(),
    mockIcons: {
      AlertCircle: { template: '<span data-testid="icon-alert" />' },
      Loader2: { template: '<span data-testid="icon-loader" />' },
      Mail: { template: '<span data-testid="icon-mail" />' },
    },
  }
})

// ---------------------------------------------------------------------------
// Mock the api module before importing the component.
// ---------------------------------------------------------------------------
vi.mock('../../api', () => ({
  default: {
    post: mockPost,
  },
}))

// ---------------------------------------------------------------------------
// Mock lucide-vue-next icons — not relevant to behaviour, can cause SVG
// import issues in the headless test environment.
// ---------------------------------------------------------------------------
vi.mock('lucide-vue-next', () => mockIcons)

import EmailOtpVerifyView from './EmailOtpVerifyView.vue'

// ---------------------------------------------------------------------------
// Minimal router
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/auth/login', name: 'login', component: { template: '<div>login</div>' } },
      { path: '/auth/email-verify', name: 'email-verify', component: EmailOtpVerifyView },
    ],
  })
}

// ---------------------------------------------------------------------------
// Mount helper
// ---------------------------------------------------------------------------
async function mountView(token = 'test-two-fa-token') {
  const router = makeRouter()
  const pinia = createPinia()

  await router.push({ path: '/auth/email-verify', query: { token } })
  await router.isReady()

  const wrapper = mount(EmailOtpVerifyView, {
    global: {
      plugins: [router, pinia],
    },
  })

  return { wrapper, router }
}

// ---------------------------------------------------------------------------
// Lifecycle: fake timers + mock reset
// ---------------------------------------------------------------------------
beforeEach(() => {
  mockPost.mockReset()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// 1. Component mounts cleanly
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — mount', () => {
  it('mounts without throwing when a two_fa_token is present', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    let caughtError: unknown = null
    try {
      const { wrapper } = await mountView('valid-token')
      await flushPromises()
      expect(wrapper.exists()).toBe(true)
    } catch (e) {
      caughtError = e
    }

    expect(caughtError).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// 2. Calls /auth/2fa/email-send/ on mount
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — auto-send on mount', () => {
  it('POSTs to /auth/2fa/email-send/ immediately on mount', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    await mountView('my-token')
    await flushPromises()

    expect(mockPost).toHaveBeenCalledWith('/auth/2fa/email-send/', {
      two_fa_token: 'my-token',
    })
  })

  it('calls email-send exactly once on initial mount', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    await mountView('token-abc')
    await flushPromises()

    const sendCalls = mockPost.mock.calls.filter(([url]: [string]) => url === '/auth/2fa/email-send/')
    expect(sendCalls).toHaveLength(1)
  })
})

// ---------------------------------------------------------------------------
// 3. Renders the 6-digit input
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — 6-digit input', () => {
  it('renders an input with maxlength 6 and numeric inputmode', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    const { wrapper } = await mountView()
    await flushPromises()

    const input = wrapper.find('input[maxlength="6"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('inputmode')).toBe('numeric')
  })

  it('input starts empty', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    const { wrapper } = await mountView()
    await flushPromises()

    const input = wrapper.find<HTMLInputElement>('input[maxlength="6"]')
    expect(input.element.value).toBe('')
  })
})

// ---------------------------------------------------------------------------
// 4. Auto-submits when 6 digits are entered
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — auto-submit on 6 digits', () => {
  it('calls /auth/2fa/email-verify/ when 6 digits are set and @input fires', async () => {
    // Mount-time email-send
    mockPost.mockResolvedValueOnce({ data: {} })
    // Verify call — returns tokens
    mockPost.mockResolvedValueOnce({
      data: {
        access: 'acc-token',
        refresh: 'ref-token',
        user: { id: 1, email: 'test-user@example.com', full_name: 'Agent A', role: 'agent' },
      },
    })

    const { wrapper } = await mountView('token-xyz')
    await flushPromises()

    const input = wrapper.find('input[maxlength="6"]')
    // setValue sets the value AND fires input/change events — no need for
    // an extra trigger('input') which would double-fire onCodeInput.
    await input.setValue('123456')
    await flushPromises()

    const verifyCalls = mockPost.mock.calls.filter(([url]: [string]) => url === '/auth/2fa/email-verify/')
    expect(verifyCalls).toHaveLength(1)
    expect(verifyCalls[0][1]).toEqual({ two_fa_token: 'token-xyz', code: '123456' })
  })
})

// ---------------------------------------------------------------------------
// 5. Resend cooldown timer
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — resend cooldown', () => {
  it('shows a countdown after OTP is sent', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    const { wrapper } = await mountView()
    await flushPromises()

    // After mount, cooldown (60 s) should be active — resend button is disabled
    const buttons = wrapper.findAll('button')
    const resendBtn = buttons.find((b) => b.text().includes('Resend'))
    expect(resendBtn?.attributes('disabled')).toBeDefined()
    expect(resendBtn?.text()).toMatch(/Resend in \d+s/)
  })

  it('re-enables the resend button after cooldown expires', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })

    const { wrapper } = await mountView()
    await flushPromises()

    // Advance past the 60-second cooldown
    vi.advanceTimersByTime(61_000)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const resendBtn = buttons.find((b) => b.text().includes('Resend'))
    expect(resendBtn?.text()).toBe('Resend code')
    expect(resendBtn?.attributes('disabled')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// 6. Error state on failed verify
// ---------------------------------------------------------------------------
describe('EmailOtpVerifyView — error state', () => {
  it('shows an error message when /email-verify/ returns 400', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })
    mockPost.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Invalid or expired OTP code.' } },
    })

    const { wrapper } = await mountView('err-token')
    await flushPromises()

    const input = wrapper.find('input[maxlength="6"]')
    await input.setValue('000000')
    await flushPromises()

    const errorEl = wrapper.find('[class*="danger"]')
    expect(errorEl.exists()).toBe(true)
    expect(errorEl.text()).toContain('Invalid or expired OTP code.')
  })

  it('clears the code input after a failed verify', async () => {
    mockPost.mockResolvedValueOnce({ data: {} })
    mockPost.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Invalid or expired OTP code.' } },
    })

    const { wrapper } = await mountView()
    await flushPromises()

    const input = wrapper.find<HTMLInputElement>('input[maxlength="6"]')
    await input.setValue('111111')
    await flushPromises()

    expect(input.element.value).toBe('')
  })
})
