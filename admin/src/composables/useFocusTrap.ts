/**
 * useFocusTrap — lightweight focus-trap composable for BaseModal and BaseDrawer.
 *
 * Usage:
 *   const { trapRef, activate, deactivate } = useFocusTrap(emit)
 *
 *   - Bind `trapRef` to the dialog panel element.
 *   - Call `activate()` after the panel is rendered (watch open → true + nextTick).
 *   - Call `deactivate()` before/after the panel closes.
 *   - Escape key calls emit('close') and deactivates automatically.
 */

import { ref, onUnmounted, type Ref } from 'vue'

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([tabindex="-1"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
  'details > summary',
].join(', ')

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)).filter(
    (el) => !el.closest('[inert]') && el.offsetParent !== null,
  )
}

export function useFocusTrap(emit: (event: 'close') => void): {
  trapRef: Ref<HTMLElement | null>
  activate: () => void
  deactivate: () => void
} {
  const trapRef = ref<HTMLElement | null>(null)
  let previouslyFocused: HTMLElement | null = null

  function handleKeyDown(e: KeyboardEvent) {
    const container = trapRef.value
    if (!container) return

    if (e.key === 'Escape') {
      e.preventDefault()
      emit('close')
      return
    }

    if (e.key !== 'Tab') return

    const focusable = getFocusable(container)
    if (focusable.length === 0) {
      e.preventDefault()
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement as HTMLElement

    if (e.shiftKey) {
      // Shift+Tab: if on first, wrap to last
      if (active === first || !container.contains(active)) {
        e.preventDefault()
        last.focus()
      }
    } else {
      // Tab: if on last, wrap to first
      if (active === last || !container.contains(active)) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  function activate() {
    previouslyFocused = document.activeElement as HTMLElement
    document.addEventListener('keydown', handleKeyDown)

    const container = trapRef.value
    if (container) {
      const focusable = getFocusable(container)
      if (focusable.length > 0) {
        focusable[0].focus()
      } else {
        // Fallback: make the container itself focusable so keyboard events still work
        container.setAttribute('tabindex', '-1')
        container.focus()
      }
    }
  }

  function deactivate() {
    document.removeEventListener('keydown', handleKeyDown)
    if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
      previouslyFocused.focus()
    }
    previouslyFocused = null
  }

  onUnmounted(deactivate)

  return { trapRef, activate, deactivate }
}
