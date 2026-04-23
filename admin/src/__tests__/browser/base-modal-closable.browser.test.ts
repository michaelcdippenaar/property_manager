/**
 * BaseModal — closable=false guard tests
 *
 * Verifies that when `:closable="false"` is set on BaseModal:
 *   1. Clicking the backdrop does NOT emit 'close'
 *   2. Pressing Escape does NOT emit 'close'
 *
 * Also verifies the default (closable=true) behaviour is unaffected:
 *   3. Clicking the backdrop DOES emit 'close'
 *   4. Pressing Escape DOES emit 'close'
 *
 * Run:
 *   npx vitest run src/__tests__/browser/base-modal-closable.browser.test.ts
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from '../../components/BaseModal.vue'

// ---------------------------------------------------------------------------
// Helper — mount BaseModal and record emitted 'close' events.
// We use @vue/test-utils mount (not vitest-browser-vue render) so that we
// have access to vm.activate() exposed via defineExpose, which we call
// explicitly to arm the focus trap without relying on the CSS Transition's
// @after-enter hook (unreliable in headless Playwright).
// ---------------------------------------------------------------------------
function mountModal(props: { closable?: boolean } = {}) {
  const wrapper = mount(BaseModal, {
    props: {
      open: true,
      title: 'Test Modal',
      ...props,
    },
    // Attach to document.body so Teleport can render into it
    attachTo: document.body,
  })

  return { wrapper }
}

// Convenience: fire a backdrop click via native DOM event to bypass Playwright
// visibility checks (backdrop sits behind the panel in z-order).
function clickBackdrop() {
  const backdrop = document.body.querySelector<HTMLElement>('.absolute.inset-0.bg-black\\/40')
  expect(backdrop).not.toBeNull()
  backdrop!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

// Convenience: fire Escape on document (where the focus trap listener lives).
function pressEscape() {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
}

// ---------------------------------------------------------------------------
// closable=false — backdrop click must NOT emit close
// ---------------------------------------------------------------------------
describe('BaseModal :closable="false"', () => {
  it('backdrop click does not emit close', () => {
    const { wrapper } = mountModal({ closable: false })

    clickBackdrop()

    expect(wrapper.emitted('close')).toBeFalsy()

    wrapper.unmount()
  })

  it('Escape key does not emit close', () => {
    const { wrapper } = mountModal({ closable: false })

    // Activate the focus trap explicitly — BaseModal exposes activate() via
    // defineExpose so tests can arm the trap without CSS transition hooks.
    ;(wrapper.vm as any).activate()

    pressEscape()

    expect(wrapper.emitted('close')).toBeFalsy()

    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// closable=true (default) — backdrop click and Escape MUST still emit close
// ---------------------------------------------------------------------------
describe('BaseModal :closable="true" (default)', () => {
  it('backdrop click emits close', () => {
    const { wrapper } = mountModal({ closable: true })

    clickBackdrop()

    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('close')!.length).toBe(1)

    wrapper.unmount()
  })

  it('Escape key emits close after focus trap activates', () => {
    const { wrapper } = mountModal({ closable: true })

    // Explicitly activate the focus trap instead of waiting for the CSS
    // Transition's @after-enter hook, which does not fire reliably in Playwright.
    ;(wrapper.vm as any).activate()

    pressEscape()

    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('close')!.length).toBe(1)

    wrapper.unmount()
  })
})
