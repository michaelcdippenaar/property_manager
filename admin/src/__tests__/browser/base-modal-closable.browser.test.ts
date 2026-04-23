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
import { describe, it, expect, vi } from 'vitest'
import { render } from 'vitest-browser-vue'
import { userEvent } from '@vitest/browser/context'
import { h, defineComponent } from 'vue'
import BaseModal from '../../components/BaseModal.vue'

// ---------------------------------------------------------------------------
// Helper — wrap BaseModal in a parent that records emitted 'close' events
// ---------------------------------------------------------------------------
function mountModal(props: { closable?: boolean } = {}) {
  const closeCalls = vi.fn()

  const wrapper = render(BaseModal, {
    props: {
      open: true,
      title: 'Test Modal',
      ...props,
    },
    attrs: {
      onClose: closeCalls,
    },
  })

  return { wrapper, closeCalls }
}

// ---------------------------------------------------------------------------
// closable=false — backdrop click must NOT emit close
// ---------------------------------------------------------------------------
describe('BaseModal :closable="false"', () => {
  it('backdrop click does not emit close', async () => {
    const { wrapper, closeCalls } = mountModal({ closable: false })

    // The backdrop is the first absolute div inside the modal wrapper
    const backdrop = wrapper.container.querySelector('.absolute.inset-0.bg-black\\/40')
    expect(backdrop).not.toBeNull()

    await userEvent.click(backdrop as Element)

    expect(closeCalls).not.toHaveBeenCalled()
  })

  it('Escape key does not emit close', async () => {
    const { closeCalls } = mountModal({ closable: false })

    await userEvent.keyboard('{Escape}')

    expect(closeCalls).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// closable=true (default) — backdrop click and Escape MUST still emit close
// ---------------------------------------------------------------------------
describe('BaseModal :closable="true" (default)', () => {
  it('backdrop click emits close', async () => {
    const { wrapper, closeCalls } = mountModal({ closable: true })

    const backdrop = wrapper.container.querySelector('.absolute.inset-0.bg-black\\/40')
    expect(backdrop).not.toBeNull()

    await userEvent.click(backdrop as Element)

    expect(closeCalls).toHaveBeenCalledOnce()
  })

  it('Escape key emits close after focus trap activates', async () => {
    const { closeCalls } = mountModal({ closable: true })

    // Give the transition's @after-enter a tick to fire activate()
    await new Promise((r) => setTimeout(r, 250))

    await userEvent.keyboard('{Escape}')

    expect(closeCalls).toHaveBeenCalledOnce()
  })
})
