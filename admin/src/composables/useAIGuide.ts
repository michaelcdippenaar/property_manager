/**
 * useAIGuide — composable that bridges the aiGuide Pinia store
 * with the router for navigation actions.
 *
 * Exposes: sendMessage, highlight, clearHighlight, isOpen, toggle
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAIGuideStore, type GuideMode } from '../stores/aiGuide'

/** Whether the AI guide feature is enabled via env var. */
export const AI_GUIDE_ENABLED = import.meta.env.VITE_ENABLE_AI_GUIDE === 'true'

export function useAIGuide(portalRole: 'agent' | 'owner' = 'agent') {
  const store = useAIGuideStore()
  const router = useRouter()

  const isOpen = computed(() => store.isOpen)
  const isLoading = computed(() => store.isLoading)
  const messages = computed(() => store.messages)
  const mode = computed(() => store.mode)
  const highlightedSelector = computed(() => store.highlightedSelector)
  const error = computed(() => store.error)

  function toggle() {
    store.toggle()
  }

  function open() {
    store.open()
  }

  function close() {
    store.close()
  }

  function setMode(m: GuideMode) {
    store.setMode(m)
  }

  function highlight(selector: string | null) {
    store.highlight(selector)
  }

  function clearHighlight() {
    store.clearHighlight()
  }

  /**
   * Send a message and, after receiving a response, execute any navigation
   * action returned by the guide backend/mock.
   */
  async function sendMessage(userMessage: string): Promise<void> {
    await store.sendMessage(userMessage, portalRole)

    // Execute navigation after assistant responds
    const action = store.pendingAction
    if (action?.route) {
      await router.push(action.route)
      store.pendingAction = null
    }
  }

  /**
   * Execute a pending action (called when user confirms in walkthrough mode).
   */
  async function executeAction(): Promise<void> {
    const action = store.pendingAction
    if (!action) return

    if (action.route) {
      await router.push(action.route)
    }
    store.pendingAction = null
  }

  return {
    isOpen,
    isLoading,
    messages,
    mode,
    highlightedSelector,
    error,
    toggle,
    open,
    close,
    setMode,
    highlight,
    clearHighlight,
    sendMessage,
    executeAction,
  }
}
