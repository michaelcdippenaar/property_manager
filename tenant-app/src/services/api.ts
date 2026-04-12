import { api } from '../boot/axios'

// ─── Type definitions ────────────────────────────────────────────────────────

export interface MaintenanceIssue {
  id: number
  title: string
  description: string
  status: string
  priority: string
  category: string
  ticket_ref: string
  created_at: string
  updated_at: string
}

export interface MaintenanceActivity {
  id: number
  activity_type: string
  message: string
  file_url: string | null
  created_by_name: string
  created_by_role: string
  metadata: Record<string, unknown> | null
  created_at: string
  is_system?: boolean
}

export interface ClassifyResult {
  category: string
  priority: string
  confidence: number
  rag_matches: number
  skill_matches: number
}

export interface TenantLease {
  id: number
  status: string
  unit_label: string
  property_name: string
  start_date: string
  end_date: string
  monthly_rent: string
  deposit: string
  rent_due_day: number
  water_included: boolean
  water_limit_litres: number | null
  electricity_prepaid: boolean
}

export interface ESigningSubmission {
  id: number
  lease_id: number
  lease_label: string
  status: string
  signing_mode: string
  signers: ESigningSigner[]
  signed_pdf_url: string | null
  template_name: string | null
  created_at: string
}

export interface ESigningSigner {
  id: number
  name: string
  email: string
  role: string
  status: string
  signing_url: string | null
  order: number
}

export interface UnitInfoItem {
  id: number
  icon_type: string
  label: string
  value: string
  category?: string
  is_sensitive?: boolean
}

// Tenant AI Conversations (triage before ticket creation)
export interface Conversation {
  id: number
  title: string
  maintenance_report_suggested: boolean
  maintenance_request_id: number | null
  agent_question_id: number | null
  messages: ConversationMessage[]
}

export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  attachment_url: string | null
  attachment_kind: string
  created_at?: string
}

export interface ConversationMessageResponse {
  user_message: ConversationMessage
  ai_message: ConversationMessage
  conversation: { id: number; title: string }
  maintenance_request: { id: number; title: string; priority: string; category: string; status: string } | null
  maintenance_report_suggested: boolean
  interaction_type: 'general' | 'maintenance'
  severity: string
  maintenance_request_id: number | null
}

// ─── API functions ───────────────────────────────────────────────────────────

// Conversations (AI triage)
export function createConversation(data?: { title?: string }) {
  return api.post<Conversation>('/tenant-portal/conversations/', data || {})
}

export function getConversation(id: number) {
  return api.get<Conversation>(`/tenant-portal/conversations/${id}/`)
}

export function sendConversationMessage(id: number, data: FormData | { content: string }) {
  const isFormData = data instanceof FormData
  return api.post<ConversationMessageResponse>(
    `/tenant-portal/conversations/${id}/messages/`,
    data,
    isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined,
  )
}

// Maintenance
export function listIssues(params?: { status?: string; page_size?: number }) {
  return api.get<{ results: MaintenanceIssue[] }>('/maintenance/', { params })
}

export function getIssue(id: number) {
  return api.get<MaintenanceIssue>(`/maintenance/${id}/`)
}

export function createIssue(data: { title: string; description: string; category: string; priority: string; conversation_id?: number }) {
  return api.post<MaintenanceIssue>('/maintenance/', data)
}

export function updateIssue(id: number, data: Partial<Pick<MaintenanceIssue, 'title' | 'description' | 'status' | 'priority' | 'category'>>) {
  return api.patch<MaintenanceIssue>(`/maintenance/${id}/`, data)
}

export function classifyIssue(data: { title: string; description: string; property_id?: number }) {
  return api.post<ClassifyResult>('/maintenance/classify/', data)
}

export function listActivities(issueId: number) {
  return api.get<{ results: MaintenanceActivity[] }>(`/maintenance/${issueId}/activity/`)
}

export function postActivity(issueId: number, form: FormData) {
  return api.post<MaintenanceActivity>(`/maintenance/${issueId}/activity/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Leases
export function listLeases() {
  return api.get<{ results: TenantLease[] }>('/leases/')
}

// E-Signing
export function listSubmissions(params?: { lease?: number }) {
  return api.get<{ results: ESigningSubmission[] }>('/esigning/submissions/', { params })
}

export function getSubmission(id: number) {
  return api.get<ESigningSubmission>(`/esigning/submissions/${id}/`)
}

// Property Info
export function listUnitInfo() {
  return api.get<{ results: UnitInfoItem[] }>('/properties/unit-info/')
}
