/**
 * Property + Unit types — shape mirrors apps/properties/serializers.py::PropertySerializer / UnitSerializer.
 */

export type UnitStatus = 'available' | 'occupied' | 'maintenance'

export type InformationCategory =
  | 'utilities' | 'safety' | 'access' | 'rules' | 'contacts' | 'waste' | 'other'

export interface PropertyInformationItem {
  id: string
  label: string
  body: string
  category: InformationCategory
  updated_at?: string | null
}

export interface ActiveLeaseInfo {
  start_date: string
  end_date: string
  tenant_name: string | null
  monthly_rent: string
  status: string
}

export interface Unit {
  id: number
  property: number
  unit_number: string
  bedrooms: number | null
  bathrooms: string | number | null
  toilets: number | null
  floor: number | null
  floor_size_m2: string | number | null
  rent_amount: string
  status: UnitStatus
  ad_description: string
  active_lease_info: ActiveLeaseInfo | null
  open_maintenance_count: number
}

export interface NearestLeaseExpiry {
  start_date: string
  end_date: string
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
  house_rules: string
  information_items: PropertyInformationItem[]
  agent: number | null
  owner: number | null
  cover_photo: string | null
  /** Legacy field still returned for some endpoints */
  image: string | null
  unit_count: number
  units: Unit[]
  nearest_lease_expiry: NearestLeaseExpiry | null
  /** Used when the property has no units (single-unit fallback) */
  property_active_lease_info: ActiveLeaseInfo | null
  created_at: string
}
