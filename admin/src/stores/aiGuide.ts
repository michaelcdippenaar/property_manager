/**
 * AI Guide store — conversation, highlight, and navigation state
 * for the in-app onboarding/guide agent.
 *
 * Feature flag: VITE_ENABLE_AI_GUIDE must equal 'true' for the widget to render.
 * API calls are mocked on the frontend until the backend endpoint is shipped.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type GuideMode = 'walkthrough' | 'do-it-for-me'
export type GuideRole = 'user' | 'assistant'

export interface GuideMessage {
  id: number
  role: GuideRole
  content: string
  action?: GuideAction | null
  createdAt: string
}

/** Structured action returned by the intent mapper (mocked until backend ships). */
export interface GuideAction {
  /** Route to navigate to, e.g. "/properties/new" */
  route?: string
  /** CSS selector of the UI element to highlight */
  elementSelector?: string
  /** Pre-fill data for do-it-for-me mode */
  preFillData?: Record<string, unknown>
  /** Whether user confirmation is required before executing */
  confirmationRequired?: boolean
  /** Human-readable label for the action */
  label?: string
}

export const useAIGuideStore = defineStore('aiGuide', () => {
  const isOpen = ref(false)
  const isLoading = ref(false)
  const mode = ref<GuideMode>('walkthrough')
  const messages = ref<GuideMessage[]>([])
  const highlightedSelector = ref<string | null>(null)
  const pendingAction = ref<GuideAction | null>(null)
  const error = ref<string | null>(null)

  let _nextId = 1

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  function setMode(m: GuideMode) {
    mode.value = m
  }

  function highlight(selector: string | null) {
    highlightedSelector.value = selector
  }

  function clearHighlight() {
    highlightedSelector.value = null
  }

  function clearHistory() {
    messages.value = []
    pendingAction.value = null
    error.value = null
  }

  function _addMessage(role: GuideRole, content: string, action?: GuideAction | null): GuideMessage {
    const msg: GuideMessage = {
      id: _nextId++,
      role,
      content,
      action: action ?? null,
      createdAt: new Date().toISOString(),
    }
    messages.value = [...messages.value, msg]
    return msg
  }

  /** Mock intent mapper — returns canned responses until `/api/v1/ai/guide/` ships. */
  function _mockIntentMapper(userMessage: string, portalRole: string): { reply: string; action: GuideAction | null } {
    const msg = userMessage.toLowerCase().trim()

    const agentRouteMap: Array<[RegExp, GuideAction, string]> = [
      [
        /create|add.*property|new property/,
        { route: '/properties', elementSelector: '[data-guide="add-property"]', label: 'Add Property', confirmationRequired: false },
        "I'll navigate you to Properties. Look for the **Add Property** button — I've highlighted it for you.",
      ],
      [
        /view|list.*properties|all properties/,
        { route: '/properties', label: 'Properties list' },
        "Let me take you to the Properties list.",
      ],
      [
        /lease|contract|tenancy/,
        { route: '/leases', label: 'Leases' },
        "Navigating to Leases — where you can draft, sign, and track all lease agreements.",
      ],
      [
        /maintenance|repair|issue|ticket/,
        { route: '/maintenance/issues', label: 'Maintenance Issues', elementSelector: '[data-guide="new-issue"]' },
        "I'll take you to Maintenance Issues.",
      ],
      [
        /dashboard|home|overview/,
        { route: '/', label: 'Dashboard' },
        "Taking you back to the Dashboard.",
      ],
      [
        /tenant|occupant/,
        { route: '/tenants', label: 'Tenants' },
        "Opening the Tenants list.",
      ],
      [
        /payment|invoice|financials?/,
        { route: '/payments', label: 'Payments' },
        "Navigating to Payments / Reconciliation.",
      ],
    ]

    const ownerRouteMap: Array<[RegExp, GuideAction, string]> = [
      [
        /property|properties/,
        { route: '/owner/properties', label: 'My Properties' },
        "Let me take you to your Properties.",
      ],
      [
        /lease|rental agreement|tenancy/,
        { route: '/owner/leases', label: 'My Leases' },
        "Opening your Leases overview.",
      ],
      [
        /dashboard|home|overview/,
        { route: '/owner', label: 'Dashboard' },
        "Taking you to your Owner Dashboard.",
      ],
    ]

    const routeMap = portalRole === 'owner' ? ownerRouteMap : agentRouteMap

    for (const [pattern, action, reply] of routeMap) {
      if (pattern.test(msg)) {
        return { reply, action }
      }
    }

    return {
      reply: "I'm not sure how to help with that yet. Try asking me to navigate somewhere, like \"show me maintenance issues\" or \"go to leases\".",
      action: null,
    }
  }

  async function sendMessage(userMessage: string, portalRole: 'agent' | 'owner'): Promise<void> {
    const trimmed = userMessage.trim()
    if (!trimmed) return

    error.value = null
    _addMessage('user', trimmed)
    isLoading.value = true

    try {
      // When backend ships, swap this for: const { data } = await api.post('/ai/guide/', { message: trimmed, portal: portalRole })
      await new Promise<void>((resolve) => setTimeout(resolve, 600))
      const { reply, action } = _mockIntentMapper(trimmed, portalRole)

      _addMessage('assistant', reply, action)

      if (action) {
        pendingAction.value = action
        if (action.elementSelector) {
          highlight(action.elementSelector)
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Something went wrong. Please try again.'
      error.value = msg
      _addMessage('assistant', `Sorry, I hit an error: ${msg}`)
    } finally {
      isLoading.value = false
    }
  }

  return {
    isOpen,
    isLoading,
    mode,
    messages,
    highlightedSelector,
    pendingAction,
    error,
    toggle,
    open,
    close,
    setMode,
    highlight,
    clearHighlight,
    clearHistory,
    sendMessage,
  }
})
