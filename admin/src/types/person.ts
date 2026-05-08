/**
 * Person / Tenant types — mirrors apps/accounts/serializers.py::PersonSerializer
 * and the simpler tenant projection returned from /auth/tenants/.
 */

export type PersonType = 'individual' | 'company'

export interface Person {
  id: number
  person_type: PersonType
  full_name: string
  id_number: string
  phone: string
  phone_country_code: string
  email: string
  country: string
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

/** Lighter shape returned by /auth/tenants/. */
export interface Tenant {
  id: number
  email: string
  full_name: string | null
  phone: string | null
  id_number: string | null
  date_joined: string
  is_active: boolean
}
