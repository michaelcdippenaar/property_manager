/**
 * Landlord (property owner) types — shape mirrors apps/properties/serializers.py::LandlordSerializer.
 */

export type LandlordType = 'individual' | 'company' | 'trust' | 'cc' | 'partnership'

export interface LandlordAddress {
  line1?: string
  line2?: string
  suburb?: string
  city?: string
  province?: string
  postal_code?: string
  country?: string
  [key: string]: unknown
}

export interface BankAccount {
  id: number
  landlord: number
  label: string
  bank_name: string
  account_holder: string
  account_number: string
  branch_code: string
  account_type: string
  is_default: boolean
  created_at: string
}

export interface LandlordProperty {
  id: number
  name: string
  [key: string]: unknown
}

export interface Landlord {
  id: number
  name: string
  landlord_type: LandlordType
  registration_number: string
  id_number: string
  vat_number: string
  email: string
  phone: string
  address: LandlordAddress
  /** Trust/company representative details */
  representative_name: string
  representative_email: string
  representative_phone: string
  representative_id_number: string
  /** Whether this individual landlord owns property via a trust */
  owned_by_trust: boolean
  /** Linked Person record for individuals */
  person: number | null
  /** Documents */
  registration_document: string | null
  registration_document_name: string | null
  mandate_document: string | null
  mandate_document_name: string | null
  /** Mandate dates / status */
  mandate_status: string | null
  mandate_start_date: string | null
  mandate_end_date: string | null
  /** Computed / read-only */
  property_count: number
  properties: LandlordProperty[]
  bank_accounts: BankAccount[]
  classification_data: Record<string, unknown> | null
  created_at: string
  updated_at: string
}
