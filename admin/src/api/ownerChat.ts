/**
 * Owner onboarding chat API client.
 *
 * Thin wrapper around POST/GET /properties/landlords/{id}/chat/.
 * See backend/apps/properties/chat_view.py.
 */
import api from '../api'

export type ChatRole = 'user' | 'assistant' | 'system'

export interface ContentBlock {
  type: 'text' | 'tool_use' | 'tool_result' | string
  text?: string
  id?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: unknown
}

export interface ChatMessage {
  id: number
  role: ChatRole
  content: string
  tool_calls: ContentBlock[] | null
  created_at: string
}

export interface ChatPostResponse {
  landlord_id: number
  reply: string
  content: ContentBlock[]
}

export interface ChatHistoryResponse {
  landlord_id: number
  messages: ChatMessage[]
}

export async function fetchChatHistory(landlordId: number): Promise<ChatHistoryResponse> {
  const { data } = await api.get<ChatHistoryResponse>(
    `/properties/landlords/${landlordId}/chat/`,
  )
  return data
}

export async function sendChatMessage(
  landlordId: number,
  message: string,
): Promise<ChatPostResponse> {
  const { data } = await api.post<ChatPostResponse>(
    `/properties/landlords/${landlordId}/chat/`,
    { message },
  )
  return data
}
