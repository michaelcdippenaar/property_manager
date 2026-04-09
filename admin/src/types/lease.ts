/**
 * Lease types — shape mirrors apps/leases/serializers.py::LeaseSerializer.
 *
 * Lease.status occupancy rule (see CONTEXT.md → "Lease status & unit occupancy"):
 *   - 'pending'    → future/unsigned. Does NOT occupy the unit.
 *   - 'active'     → signed AND in-progress. The ONLY status that occupies.
 *   - 'expired'    → past end date.
 *   - 'terminated' → cancelled.
 */

export type LeaseStatus = 'pending' | 'active' | 'expired' | 'terminated'

export interface LeaseTenantBrief {
  id: number
  full_name: string
  email?: string
  phone?: string
}

export interface LeaseDocumentBrief {
  id: number
  description: string
  file: string | null
  uploaded_at: string
}

export interface Lease {
  id: number
  unit: number
  unit_label: string
  property_id: number
  primary_tenant: number | null
  primary_tenant_detail: LeaseTenantBrief | null
  tenant_name: string
  all_tenant_names: string[]
  co_tenants: LeaseTenantBrief[]
  occupants: LeaseTenantBrief[]
  guarantors: LeaseTenantBrief[]
  start_date: string
  end_date: string
  monthly_rent: string
  deposit: string
  status: LeaseStatus
  lease_number: string
  rent_due_day: number
  payment_reference: string
  max_occupants: number
  water_included: boolean
  water_limit_litres: number
  electricity_prepaid: boolean
  notice_period_days: number
  early_termination_penalty_months: number
  renewal_start_date: string | null
  documents: LeaseDocumentBrief[]
  document_count: number
  landlord_info: { id: number; name: string } | null
  ai_parse_result: Record<string, unknown> | null
  created_at: string
}
