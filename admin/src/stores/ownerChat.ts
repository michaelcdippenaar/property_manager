/**
 * Owner chat store — conversation state per landlord.
 *
 * Keyed by landlord_id so multiple tabs/panels can coexist. The backend
 * persists every turn, so on panel open we just pull history.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  fetchChatHistory,
  sendChatMessage,
  type ChatMessage,
} from '../api/ownerChat'
import { extractApiError } from '../utils/api-errors'

export const useOwnerChatStore = defineStore('ownerChat', () => {
  const messagesByLandlord = ref<Map<number, ChatMessage[]>>(new Map())
  const loadingByLandlord = ref<Map<number, boolean>>(new Map())
  const sendingByLandlord = ref<Map<number, boolean>>(new Map())
  const errorByLandlord = ref<Map<number, string | null>>(new Map())

  function messages(id: number): ChatMessage[] {
    return messagesByLandlord.value.get(id) ?? []
  }
  function isLoading(id: number): boolean {
    return !!loadingByLandlord.value.get(id)
  }
  function isSending(id: number): boolean {
    return !!sendingByLandlord.value.get(id)
  }
  function error(id: number): string | null {
    return errorByLandlord.value.get(id) ?? null
  }

  async function load(landlordId: number): Promise<void> {
    loadingByLandlord.value.set(landlordId, true)
    errorByLandlord.value.set(landlordId, null)
    try {
      const resp = await fetchChatHistory(landlordId)
      messagesByLandlord.value.set(landlordId, resp.messages)
    } catch (e) {
      errorByLandlord.value.set(landlordId, extractApiError(e))
    } finally {
      loadingByLandlord.value.set(landlordId, false)
    }
  }

  async function send(landlordId: number, message: string): Promise<void> {
    sendingByLandlord.value.set(landlordId, true)
    errorByLandlord.value.set(landlordId, null)

    // Optimistically render the user's message
    const existing = messagesByLandlord.value.get(landlordId) ?? []
    if (message.trim()) {
      const optimistic: ChatMessage = {
        id: -Date.now(),
        role: 'user',
        content: message,
        tool_calls: null,
        created_at: new Date().toISOString(),
      }
      messagesByLandlord.value.set(landlordId, [...existing, optimistic])
    }

    try {
      await sendChatMessage(landlordId, message)
      // Server-of-truth: re-fetch so tool calls and IDs are consistent
      const resp = await fetchChatHistory(landlordId)
      messagesByLandlord.value.set(landlordId, resp.messages)
    } catch (e) {
      errorByLandlord.value.set(landlordId, extractApiError(e))
    } finally {
      sendingByLandlord.value.set(landlordId, false)
    }
  }

  return { messages, isLoading, isSending, error, load, send }
})
