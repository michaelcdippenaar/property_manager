/**
 * AI settings API client.
 *
 * Wraps GET/POST /api/v1/ai/knowledge/ for the admin-editable knowledge file.
 */
import api from '../api'

export interface KnowledgeResponse {
  content: string
}

export interface KnowledgeSaveResponse {
  detail: string
  saved_at: string
}

/** Fetch the current AI knowledge file content. Requires admin role. */
export async function fetchKnowledge(): Promise<KnowledgeResponse> {
  const { data } = await api.get<KnowledgeResponse>('/ai/knowledge/')
  return data
}

/** Save a new version of the AI knowledge file. Requires admin role.
 *  The backend busts the in-process cache immediately so the next AI Guide
 *  request picks up the new content. */
export async function saveKnowledge(content: string): Promise<KnowledgeSaveResponse> {
  const { data } = await api.post<KnowledgeSaveResponse>('/ai/knowledge/', { content })
  return data
}
