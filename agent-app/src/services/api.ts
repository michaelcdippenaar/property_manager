/**
 * Typed API service layer.
 * All HTTP calls go through this module — no direct axios calls in pages/components.
 */
import { api } from '../boot/axios'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Person {
  id: number
  person_type: 'individual' | 'company'
  full_name: string
  id_number: string
  phone: string
  email: string
  address: string
  employer: string
  occupation: string
  monthly_income: string | null
  date_of_birth: string | null
  emergency_contact_name: string
  emergency_contact_phone: string
  company_reg: string
  vat_number: string
  linked_user: number | null
  created_at: string
}

export interface Property {
  id: number
  name: string
  property_type: string
  address: string
  city: string
  province: string
  postal_code: string
  description: string
  agent: number | null
  cover_photo: string | null
  unit_count: number
  units: Unit[]
  created_at: string
}

export interface Unit {
  id: number
  property: number
  unit_number: string
  bedrooms: number
  bathrooms: string
  floor_size_m2: string | null
  rent_amount: string
  status: 'available' | 'occupied' | 'maintenance'
  active_lease_info: {
    tenant_name: string | null
    monthly_rent: string
    start_date: string
    end_date: string
  } | null
}

export interface PropertyViewing {
  id: number
  property: number
  property_name: string
  unit: number | null
  unit_number: string | null
  prospect: number
  prospect_name: string
  prospect_detail: Person
  agent: number | null
  agent_name: string | null
  scheduled_at: string        // ISO 8601 datetime
  duration_minutes: number
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'converted'
  notes: string
  converted_to_lease: number | null
  created_at: string
  updated_at: string
}

export interface Lease {
  id: number
  unit: number
  primary_tenant: number
  start_date: string
  end_date: string
  monthly_rent: string
  deposit: string
  status: string
  unit_label: string
  tenant_name: string
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ─── Person ───────────────────────────────────────────────────────────────────

export const createPerson = (data: {
  full_name: string
  id_number?: string
  phone?: string
  email?: string
  address?: string
  employer?: string
  occupation?: string
  monthly_income?: string | number
}): Promise<Person> =>
  api.post<Person>('/auth/persons/', data).then((r) => r.data)

export const searchPersons = (query: string): Promise<PaginatedResponse<Person>> =>
  api.get<PaginatedResponse<Person>>('/auth/persons/', { params: { search: query } }).then((r) => r.data)

// ─── Properties ───────────────────────────────────────────────────────────────

export const listProperties = (): Promise<PaginatedResponse<Property>> =>
  api.get<PaginatedResponse<Property>>('/properties/').then((r) => r.data)

export const getProperty = (id: number): Promise<Property> =>
  api.get<Property>(`/properties/${id}/`).then((r) => r.data)

export const listUnits = (propertyId?: number): Promise<PaginatedResponse<Unit>> =>
  api.get<PaginatedResponse<Unit>>('/properties/units/', {
    params: propertyId ? { property: propertyId } : undefined,
  }).then((r) => r.data)

// ─── Viewings ─────────────────────────────────────────────────────────────────

export const listViewings = (params?: {
  property?: number
  status?: string
}): Promise<PaginatedResponse<PropertyViewing>> =>
  api.get<PaginatedResponse<PropertyViewing>>('/properties/viewings/', { params }).then((r) => r.data)

export const getViewing = (id: number): Promise<PropertyViewing> =>
  api.get<PropertyViewing>(`/properties/viewings/${id}/`).then((r) => r.data)

export const getViewingsCalendar = (from: string, to: string): Promise<PropertyViewing[]> =>
  api.get<PropertyViewing[]>('/properties/viewings/calendar/', {
    params: { from, to },
  }).then((r) => r.data)

export const createViewing = (data: {
  property: number
  unit?: number | null
  prospect: number
  scheduled_at: string
  duration_minutes?: number
  notes?: string
}): Promise<PropertyViewing> =>
  api.post<PropertyViewing>('/properties/viewings/', data).then((r) => r.data)

export const updateViewing = (
  id: number,
  data: Partial<Pick<PropertyViewing, 'status' | 'notes' | 'duration_minutes'>>,
): Promise<PropertyViewing> =>
  api.patch<PropertyViewing>(`/properties/viewings/${id}/`, data).then((r) => r.data)

export const deleteViewing = (id: number): Promise<void> =>
  api.delete(`/properties/viewings/${id}/`).then(() => undefined)

export interface ConvertViewingResult {
  lease: Lease
  auto_created_unit?: {
    id: number
    unit_number: string
    property_id: number
  }
  message?: string
}

export const convertViewingToLease = (
  id: number,
  data: {
    start_date: string
    end_date: string
    monthly_rent: string | number
    deposit: string | number
    unit?: number
  },
): Promise<ConvertViewingResult> =>
  api
    .post<ConvertViewingResult>(`/properties/viewings/${id}/convert-to-lease/`, data)
    .then((r) => r.data)

// ─── Leases ───────────────────────────────────────────────────────────────────

export interface AgentLease {
  id: number
  unit: number
  unit_label: string
  tenant_name: string
  all_tenant_names: string[]
  start_date: string   // YYYY-MM-DD
  end_date: string     // YYYY-MM-DD
  monthly_rent: string
  deposit: string
  status: string
  property_id: number
  rent_due_day: number
  lease_number: string
}

export const listLeases = (params?: {
  status?: string
  property?: number
}): Promise<PaginatedResponse<AgentLease>> =>
  api.get<PaginatedResponse<AgentLease>>('/leases/', { params }).then((r) => r.data)

export const createLeaseDirect = (data: {
  unit: number
  primary_tenant: number
  start_date: string
  end_date: string
  monthly_rent: string | number
  deposit: string | number
  rent_due_day?: number
}): Promise<AgentLease> =>
  api.post<AgentLease>('/leases/', data).then((r) => r.data)

// ─── Dashboard summary ────────────────────────────────────────────────────────

export const getDashboardSummary = async () => {
  const [viewingsResp, propertiesResp] = await Promise.all([
    listViewings({ status: 'scheduled' }),
    listProperties(),
  ])
  return {
    upcomingViewings: viewingsResp.results,
    properties:       propertiesResp.results,
    viewingCount:     viewingsResp.count,
    propertyCount:    propertiesResp.count,
  }
}
