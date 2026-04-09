/**
 * Shared formatting helpers used across views.
 *
 * Always import from here — never redefine inline. (See properties_audit_2026-04-09.md.)
 */

/** Two-character initials from a full name or email. Falls back to '?'. */
export function initials(name?: string | null): string {
  if (!name?.trim()) return '?'
  const cleaned = name.includes('@') ? name.split('@')[0] : name
  return cleaned
    .trim()
    .split(/[\s._-]+/)
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

/** Format an ISO date string in en-ZA short format. */
export function formatDate(iso?: string | null, opts?: Intl.DateTimeFormatOptions): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-ZA', opts)
  } catch {
    return '—'
  }
}

/** Format an ISO date+time string in en-ZA short format. */
export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-ZA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

/** Format a number as ZAR currency, e.g. R 12 500. */
export function fmtMoney(value?: number | string | null): string {
  if (value == null || value === '') return '—'
  const n = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(n)) return '—'
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    maximumFractionDigits: 0,
  }).format(n as number)
}
