/**
 * RentalMandate types — landlord-to-agency authorisation to manage a property.
 * Mirrors apps/properties/serializers.py::RentalMandateSerializer.
 */

export type MandateStatus = 'draft' | 'active' | 'expired' | 'terminated'

export interface RentalMandate {
  id: number
  property: number
  property_name?: string
  landlord: number
  landlord_name?: string
  start_date: string
  end_date: string | null
  commission_pct: string
  status: MandateStatus
  document: string | null
  document_name: string | null
  notes: string
  created_at: string
  updated_at: string
}
