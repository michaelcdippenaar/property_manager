/**
 * PropertyOwnership types — links a Landlord to a Property over time.
 * Mirrors apps/properties/serializers.py::PropertyOwnershipSerializer.
 */

export interface PropertyOwnership {
  id: number
  property: number
  property_name?: string
  landlord: number
  landlord_name?: string
  ownership_pct: string
  start_date: string
  end_date: string | null
  is_current: boolean
  created_at: string
}
