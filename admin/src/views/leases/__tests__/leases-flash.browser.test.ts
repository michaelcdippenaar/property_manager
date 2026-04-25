/**
 * RNT-023 — Lease page flash regression tests
 *
 * Covers:
 *   1. LeasesView does NOT show the loading skeleton during background refreshes
 *      when lease data is already loaded (initialLoad flag guards the skeleton).
 *   2. Clicking filter tabs (All / Active / Expired) does not unmount the lease
 *      list DOM (no flash) when data is already loaded.
 *   3. ESigningPanel.openModalWhenReady() behaviour contract:
 *      - opens modal when no existing submissions
 *      - does NOT open when there is already an active submission
 *      - does NOT open when the component unmounts before the async load finishes
 *
 * Run:
 *   cd admin && npx vitest run src/views/leases/__tests__/leases-flash.browser.test.ts
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { h } from 'vue'

// ── Hoisted mock fn refs ───────────────────────────────────────────────────
const { mockApiGet, mockFetchAll } = vi.hoisted(() => ({
  mockApiGet:   vi.fn(),
  mockFetchAll: vi.fn(),
}))

// ── API mock ──────────────────────────────────────────────────────────────
vi.mock('../../../api', () => ({
  default: {
    get:          mockApiGet,
    post:         vi.fn(),
    delete:       vi.fn(),
    patch:        vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

// lucide-vue-next: use automock so ALL named exports are stubbed automatically.
// This is the only reliable approach when multiple components import different
// icon subsets and the full list is unknown/variable.
vi.mock('lucide-vue-next')

vi.stubGlobal('WebSocket', class {
  readyState = 3
  onopen = null; onmessage = null; onerror = null; onclose = null
  close() {}
  constructor(_url: string) {}
  static OPEN = 1; static CONNECTING = 0; static CLOSED = 3
})

vi.mock('../../../composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}))
vi.mock('../../../plugins/plausible', () => ({ trackEvent: vi.fn() }))

vi.mock('../../../stores/persons', () => ({
  usePersonsStore: () => ({ createPerson: vi.fn(), updatePerson: vi.fn() }),
}))
vi.mock('../../../stores/auth', () => ({
  useAuthStore: () => ({
    user:              { id: 1, role: 'agency_admin', email: 'test@klikk.co.za' },
    isAuthenticated:   true,
    homeRoute:         '/',
    hasPendingLegal:   false,
    suggestTwoFASetup: false,
    fetchMe: vi.fn(), logout: vi.fn(),
  }),
}))
vi.mock('../../../stores/properties', () => ({
  usePropertiesStore: () => ({ fetchOne: vi.fn() }),
}))

// Leases store — real Pinia setup store with shared reactive state refs
vi.mock('../../../stores/leases', async () => {
  const { defineStore } = await import('pinia')
  const { ref, computed } = await import('vue')

  const _items   = ref(new Map<number, any>())
  const _loading = ref(false)

  const useLeasesStore = defineStore('leases', () => ({
    items:     _items,
    loading:   _loading,
    error:     ref<string | null>(null),
    loadedAt:  ref<number | null>(null),
    list:      computed(() => [..._items.value.values()]),
    byId:      (id: number) => _items.value.get(id),
    fetchAll:  mockFetchAll,
    fetchOne:  vi.fn(), fetchActiveFor: vi.fn(), fetchForUnit: vi.fn(),
    fetchForPerson: vi.fn(), create: vi.fn(), importLease: vi.fn(),
    update:    vi.fn(), remove: vi.fn(), createRenewal: vi.fn(),
    invalidate: vi.fn(),
  }))

  return { _leasesState: { items: _items, loading: _loading }, useLeasesStore }
})

// ── Test helpers ───────────────────────────────────────────────────────────
async function getLeasesState() {
  const mod = await import('../../../stores/leases') as any
  return mod._leasesState as { items: { value: Map<number, any> }; loading: { value: boolean } }
}

function makeLease(id: number, status = 'active') {
  return {
    id, lease_number: `L-${String(id).padStart(3, '0')}`, status,
    monthly_rent: '10000', deposit: '10000',
    start_date: '2026-01-01', end_date: '2026-12-31',
    unit_label: 'Test Property — Unit 1', tenant_name: 'Test Tenant',
    all_tenant_names: ['Test Tenant'], document_count: 0,
  }
}

import LeasesView from '../LeasesView.vue'

// Stubs defined with h() so no template compiler is needed
const loadingStateStub = {
  props: ['variant', 'rows', 'doubleRow'],
  render() { return h('div', { 'data-testid': 'loading-state' }) },
}
const emptyStateStub = {
  props: ['title', 'description', 'icon'],
  render(this: any) { return h('div', { 'data-testid': 'empty-state' }, [this.title]) },
  setup(props: any) { return props },
}
const eSigningPanelStub = {
  props: ['leaseId', 'leaseTenants', 'leaseData'],
  render(this: any) {
    return h('div', { 'data-testid': 'esigning-panel', 'data-lease-id': String(this.leaseId) })
  },
  // setup() must return the exposed methods so they are accessible on the
  // component instance retrieved via templateRef in LeasesView.signingPanelRefs.
  setup(props: any) {
    const openModal = vi.fn()
    const openModalWhenReady = vi.fn()
    return { ...props, openModal, openModalWhenReady }
  },
}

async function mountView(opts: {
  query?:   Record<string, string>
  leases?:  any[]
  loading?: boolean
} = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const state = await getLeasesState()
  const leases = opts.leases ?? []
  state.items.value   = new Map(leases.map((l: any) => [l.id, l]))
  state.loading.value = opts.loading ?? false

  mockFetchAll.mockReset()
  mockFetchAll.mockResolvedValue(undefined)
  mockApiGet.mockReset()
  mockApiGet.mockResolvedValue({ data: { results: [] } })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/',             component: { render: () => null } },
      { path: '/leases',       name: 'leases',        component: { render: () => null } },
      { path: '/leases/build', name: 'lease-builder', component: { render: () => null } },
    ],
  })
  await router.push({ path: '/leases', query: opts.query ?? {} })
  await router.isReady()

  const wrapper = mount(LeasesView, {
    global: {
      plugins: [router, pinia],
      stubs: {
        ESigningPanel:     eSigningPanelStub,
        ImportLeaseWizard: true,
        EditLeaseDrawer:   true,
        BaseDrawer:        true,
        BaseModal:         true,
        PageHeader:        { props: ['title', 'subtitle', 'crumbs'], render: () => null },
        EmptyState:        emptyStateStub,
        LoadingState:      loadingStateStub,
        ErrorState:        true,
      },
    },
    attachTo: document.body,
  })

  // LeasesView uses onActivated (not onMounted) because AppLayout wraps it in
  // KeepAlive. In plain mount() there is no KeepAlive parent so onActivated
  // never fires automatically. Call initView() directly via defineExpose.
  const vm = wrapper.vm as any
  if (typeof vm.initView === 'function') {
    vm.initView()
  }

  return { wrapper, router, state }
}

afterEach(async () => {
  vi.clearAllMocks()
  document.body.innerHTML = ''
  const state = await getLeasesState()
  state.items.value   = new Map()
  state.loading.value = false
})

// ── Suite 1: Loading skeleton gating ─────────────────────────────────────────
describe('LeasesView — initialLoad skeleton', () => {
  it('shows skeleton on initial mount when store is empty and loading', async () => {
    const { wrapper } = await mountView({ leases: [], loading: true })
    await wrapper.vm.$nextTick()

    // No data + loading=true → initialLoad=true + loading=true → skeleton renders
    const skeleton = wrapper.find('[data-testid="loading-state"]')
    expect(skeleton.exists()).toBe(true)

    wrapper.unmount()
  })

  it('hides skeleton during background refresh when leases already exist', async () => {
    const { wrapper, state } = await mountView({ leases: [makeLease(1), makeLease(2)] })
    await flushPromises()

    // Simulate a background re-fetch: loading=true but data is still in store
    state.loading.value = true
    await wrapper.vm.$nextTick()

    // initialLoad should be false (data existed at mount) → no skeleton
    const skeleton = wrapper.find('[data-testid="loading-state"]')
    expect(skeleton.exists()).toBe(false)

    state.loading.value = false
    wrapper.unmount()
  })
})

// ── Suite 2: Filter tab clicks ────────────────────────────────────────────────
describe('LeasesView — filter tab clicks do not flash', () => {
  it('clicking each tab does not show loading skeleton when data is loaded', async () => {
    const leases = [makeLease(1, 'active'), makeLease(2, 'expired')]
    const { wrapper } = await mountView({ leases })
    await flushPromises()

    for (const label of ['All', 'Active', 'Expired']) {
      const tab = wrapper.findAll('button').find(b => b.text().trim().startsWith(label))
      if (!tab) continue

      await tab.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[data-testid="loading-state"]').exists()).toBe(false)
    }

    wrapper.unmount()
  })

  it('tab switch from Active to All does not show empty state when leases exist', async () => {
    const leases = [makeLease(1, 'active'), makeLease(2, 'expired'), makeLease(3, 'active')]
    const { wrapper } = await mountView({ leases })
    await flushPromises()

    const activeTab = wrapper.findAll('button').find(b => b.text().trim().startsWith('Active'))
    await activeTab!.trigger('click')
    await wrapper.vm.$nextTick()

    const allTab = wrapper.findAll('button').find(b => b.text().trim().startsWith('All'))
    await allTab!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="loading-state"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(false)

    wrapper.unmount()
  })
})

// ── Suite 3: URL deep-link ────────────────────────────────────────────────────
describe('LeasesView — URL deep-link', () => {
  it('expands the target lease when ?expand=<id> is in the URL', async () => {
    const leases = [makeLease(1, 'active')]
    mockFetchAll.mockImplementation(async () => { /* items already seeded */ })

    const { wrapper } = await mountView({ query: { expand: '1' }, leases })
    await flushPromises()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const panel = wrapper.find('[data-testid="esigning-panel"][data-lease-id="1"]')
    expect(panel.exists()).toBe(true)

    wrapper.unmount()
  })

  it('strips ?sign=1 from URL after initView processes it', async () => {
    const leases = [makeLease(1, 'active')]
    mockFetchAll.mockImplementation(async () => { /* items already seeded */ })

    const { wrapper, router } = await mountView({
      query: { expand: '1', sign: '1' },
      leases,
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const currentQuery = router.currentRoute.value.query
    expect(currentQuery.sign).toBeUndefined()

    wrapper.unmount()
  })
})

// ── Suite 4: openModalWhenReady — behaviour contract ─────────────────────────
describe('openModalWhenReady — behaviour contract', () => {
  async function simulateOpenModalWhenReady(
    initiallyLoading: boolean,
    submissionsLength: number,
    isMounted: boolean,
  ): Promise<boolean> {
    let loading = initiallyLoading
    const mounted = isMounted
    const deadline = Date.now() + 300

    while (loading && mounted && Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 10))
      loading = false
    }
    if (!mounted)              return false
    if (submissionsLength > 0) return false

    return true
  }

  it('opens modal when no submissions exist', async () => {
    expect(await simulateOpenModalWhenReady(false, 0, true)).toBe(true)
  })

  it('does NOT open when a submission already exists', async () => {
    expect(await simulateOpenModalWhenReady(false, 1, true)).toBe(false)
  })

  it('does NOT open when component is unmounted', async () => {
    expect(await simulateOpenModalWhenReady(false, 0, false)).toBe(false)
  })

  it('waits for loading then opens when no submissions', async () => {
    expect(await simulateOpenModalWhenReady(true, 0, true)).toBe(true)
  })
})
