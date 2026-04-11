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

export interface Conversation {
  id: number
  title: string
  messages: Message[]
  maintenance_report_suggested: boolean
  maintenance_request_id: number | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role?: string
  content?: string
  type?: string
  file_url?: string | null
  attachment_kind?: string | null
  severity?: string | null
  skills_used?: Record<string, unknown> | null
  created_at: string
  // Client-side helpers
  skills?: string[]
  draft?: Record<string, unknown>
  interaction_type?: string
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

// ─── API functions ───────────────────────────────────────────────────────────

// Maintenance
export function listIssues(params?: { status?: string; page_size?: number }) {
  return api.get<{ results: MaintenanceIssue[] }>('/maintenance/', { params })
}

export function getIssue(id: number) {
  return api.get<MaintenanceIssue>(`/maintenance/${id}/`)
}

export function createIssue(data: { title: string; description: string; category: string; priority: string }) {
  return api.post<MaintenanceIssue>('/maintenance/', data)
}

export function listActivities(issueId: number) {
  return api.get<{ results: MaintenanceActivity[] }>(`/maintenance/${issueId}/activity/`)
}

export function postActivity(issueId: number, form: FormData) {
  return api.post<MaintenanceActivity>(`/maintenance/${issueId}/activity/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Conversations
export function listConversations() {
  return api.get<{ results: Conversation[] }>('/tenant-portal/conversations/')
}

export function getConversation(id: number) {
  return api.get<Conversation>(`/tenant-portal/conversations/${id}/`)
}

export function createConversation() {
  return api.post<Conversation>('/tenant-portal/conversations/', {})
}

export function sendMessage(convId: number, form: FormData) {
  return api.post(`/tenant-portal/conversations/${convId}/messages/`, form, {
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
