/**
 * Extract a user-friendly message from an API error.
 *
 * Handles:
 *  - DRF `{detail: 'message'}` shape
 *  - DRF field errors `{field: ['err1', 'err2'], …}`
 *  - Plain string responses
 *  - Network / unknown errors
 */
export function extractApiError(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  // Axios error shape
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const e = err as any
  const data = e?.response?.data

  if (!data) {
    return e?.message || fallback
  }

  // Plain string body
  if (typeof data === 'string') return data

  // DRF detail
  if (typeof data.detail === 'string') return data.detail

  // DRF non_field_errors
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return String(data.non_field_errors[0])
  }

  // DRF field errors — flatten "field: message"
  if (typeof data === 'object') {
    const parts: string[] = []
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        parts.push(`${key}: ${value.join(', ')}`)
      } else if (typeof value === 'string') {
        parts.push(`${key}: ${value}`)
      }
    }
    if (parts.length) return parts.join(' · ')
  }

  return fallback
}
