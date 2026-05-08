/**
 * Feature 2 — Confirm save-draft on route exit when lease has unsaved changes.
 *
 * Verifies the dirty-tracking guard pattern used in LeaseBuilderView /
 * EditLeaseDrawer: when isDirty is true and the user attempts to leave, a
 * confirmation modal is shown (router blocks navigation until resolved).
 *
 * This test exercises the *behaviour contract* of the guard via a minimal
 * mock component, rather than mounting the full ~1.3k-line LeaseBuilderView
 * (which has dozens of unrelated dependencies). The contract:
 *   1. clean state → router push proceeds without prompt
 *   2. dirty state + click "Save as draft" → saveDraft called, navigation proceeds
 *   3. dirty state + click "Discard"      → no save, navigation proceeds
 *   4. dirty state + click "Cancel"       → user stays on page (next(false))
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h, ref, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

vi.mock('lucide-vue-next')

function makeGuardComponent(saveDraft: () => Promise<void>) {
  return defineComponent({
    name: 'GuardHarness',
    setup() {
      const isDirty = ref(false)
      const showLeaveConfirm = ref(false)
      let pendingNext: ((v?: any) => void) | null = null

      onBeforeRouteLeave((_to, _from, next) => {
        if (!isDirty.value) return next()
        showLeaveConfirm.value = true
        pendingNext = next
      })

      function onBeforeUnload(e: BeforeUnloadEvent) {
        if (!isDirty.value) return
        e.preventDefault()
        e.returnValue = ''
      }
      window.addEventListener('beforeunload', onBeforeUnload)
      onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

      async function leaveSaveDraft() {
        await saveDraft()
        isDirty.value = false
        showLeaveConfirm.value = false
        pendingNext?.()
        pendingNext = null
      }
      function leaveDiscard() {
        showLeaveConfirm.value = false
        pendingNext?.()
        pendingNext = null
      }
      function leaveCancel() {
        showLeaveConfirm.value = false
        pendingNext?.(false)
        pendingNext = null
      }

      function markDirty() { isDirty.value = true }

      return { isDirty, showLeaveConfirm, leaveSaveDraft, leaveDiscard, leaveCancel, markDirty }
    },
    render() {
      return h('div', [
        h('button', { 'data-testid': 'mark-dirty', onClick: () => (this as any).markDirty() }, 'dirty'),
        (this as any).showLeaveConfirm
          ? h('div', { 'data-testid': 'leave-modal' }, [
              h('button', { 'data-testid': 'btn-save',    onClick: () => (this as any).leaveSaveDraft() }, 'Save'),
              h('button', { 'data-testid': 'btn-discard', onClick: () => (this as any).leaveDiscard() },   'Discard'),
              h('button', { 'data-testid': 'btn-cancel',  onClick: () => (this as any).leaveCancel() },    'Cancel'),
            ])
          : null,
      ])
    },
  })
}

async function mountWithRouter(saveDraft = vi.fn().mockResolvedValue(undefined)) {
  const Guarded = makeGuardComponent(saveDraft)
  const Other   = defineComponent({ render: () => h('div', { 'data-testid': 'other' }, 'other') })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/build', name: 'build', component: Guarded },
      { path: '/other', name: 'other', component: Other },
    ],
  })
  await router.push('/build')
  await router.isReady()

  // Use a real <RouterView> host so onBeforeRouteLeave is wired into the
  // route record (it only registers when the component is rendered via
  // RouterView, not via plain mount()).
  const { RouterView } = await import('vue-router')
  const Host = defineComponent({ render: () => h(RouterView) })

  const wrapper = mount(Host, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  await wrapper.vm.$nextTick()
  return { wrapper, router, saveDraft }
}

describe('Lease builder unsaved-changes guard', () => {
  it('navigates freely when state is clean', async () => {
    const { wrapper, router } = await mountWithRouter()
    await router.push('/other')
    await flushPromises()
    expect(wrapper.find('[data-testid="other"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="leave-modal"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the modal and blocks navigation when dirty', async () => {
    const { wrapper, router } = await mountWithRouter()
    await wrapper.find('[data-testid="mark-dirty"]').trigger('click')

    // Fire navigation — should be intercepted
    const nav = router.push('/other')
    await flushPromises()

    expect(wrapper.find('[data-testid="leave-modal"]').exists()).toBe(true)
    expect(router.currentRoute.value.path).toBe('/build')

    // Cancel — stay on /build
    await wrapper.find('[data-testid="btn-cancel"]').trigger('click')
    await nav.catch(() => {/* navigation aborted */})
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/build')
    wrapper.unmount()
  })

  it('Save-as-draft path calls saveDraft then proceeds', async () => {
    const saveDraft = vi.fn().mockResolvedValue(undefined)
    const { wrapper, router } = await mountWithRouter(saveDraft)
    await wrapper.find('[data-testid="mark-dirty"]').trigger('click')

    const nav = router.push('/other')
    await flushPromises()
    expect(wrapper.find('[data-testid="leave-modal"]').exists()).toBe(true)

    await wrapper.find('[data-testid="btn-save"]').trigger('click')
    await nav
    await flushPromises()

    expect(saveDraft).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.path).toBe('/other')
    wrapper.unmount()
  })

  it('Discard path proceeds without saving', async () => {
    const saveDraft = vi.fn()
    const { wrapper, router } = await mountWithRouter(saveDraft)
    await wrapper.find('[data-testid="mark-dirty"]').trigger('click')

    const nav = router.push('/other')
    await flushPromises()
    await wrapper.find('[data-testid="btn-discard"]').trigger('click')
    await nav
    await flushPromises()

    expect(saveDraft).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/other')
    wrapper.unmount()
  })
})
