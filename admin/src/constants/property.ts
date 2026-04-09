/**
 * Property constants — single source of truth for the admin UI.
 *
 * Mirrors `Property.PropertyType` in `backend/apps/properties/models.py`.
 * Update both sides if the backend choices change.
 */

export interface PropertyTypeOption {
  value: string
  label: string
}

export const PROPERTY_TYPES: readonly PropertyTypeOption[] = [
  { value: 'apartment',  label: 'Apartment'  },
  { value: 'house',      label: 'House'      },
  { value: 'townhouse',  label: 'Townhouse'  },
  { value: 'commercial', label: 'Commercial' },
] as const

export const PROPERTY_TYPE_VALUES = PROPERTY_TYPES.map((t) => t.value)

export function propertyTypeLabel(value?: string | null): string {
  if (!value) return '—'
  return PROPERTY_TYPES.find((t) => t.value === value)?.label ?? value
}
