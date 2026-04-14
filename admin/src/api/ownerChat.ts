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

/** Upload one or more files to the landlord's FICA document collection.
 *  Reuses the existing bulk upload endpoint — the same one the FICA tab
 *  uses. Returns nothing meaningful; caller should re-fetch gap analysis. */
export async function uploadLandlordDocuments(
  landlordId: number,
  files: File[] | FileList,
): Promise<void> {
  const form = new FormData()
  const arr = Array.from(files)
  for (const f of arr) form.append('files', f)
  await api.post(
    `/properties/landlords/${landlordId}/fica-documents/`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

/** Run the Claude Vision classifier on all uploaded documents. */
export async function classifyLandlord(landlordId: number): Promise<void> {
  await api.post(`/properties/landlords/${landlordId}/classify/`)
}
