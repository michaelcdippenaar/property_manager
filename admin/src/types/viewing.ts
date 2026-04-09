/**
 * PropertyViewing types — mirrors apps/properties/serializers.py::PropertyViewingSerializer.
 */

export type ViewingStatus =
  | 'scheduled'
  | 'confirmed'
  | 'completed'
  | 'cancelled'
  | 'converted'

export interface PropertyViewing {
  id: number
  property: number
  property_name: string
  unit: number | null
  unit_number: string | null
  prospect: number
  prospect_name: string
  agent: number | null
  agent_name: string | null
  scheduled_at: string
  duration_minutes: number
  status: ViewingStatus
  notes: string
  converted_to_lease: number | null
  created_at: string
  updated_at: string
}
