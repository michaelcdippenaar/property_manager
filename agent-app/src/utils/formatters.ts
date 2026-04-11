// ─── Shared formatters & color maps for the Agent App ────────────────────────

/** Viewing status → Quasar color name */
export function statusColor(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'info',
    confirmed: 'primary',
    completed: 'positive',
    cancelled: 'negative',
    converted: 'secondary',
  }
  return map[status] || 'grey'
}

/** Lease status → Quasar color name */
export function leaseStatusColor(status: string): string {
  const map: Record<string, string> = {
    active: 'positive',
    pending: 'warning',
    expired: 'grey-5',
    terminated: 'negative',
  }
  return map[status] || 'grey-5'
}

/** Unit status → Quasar color name */
export function unitStatusColor(status: string): string {
  return status === 'available' ? 'positive' : status === 'occupied' ? 'grey-6' : 'warning'
}

/** Viewing status → Material icon name */
export function statusIcon(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'event',
    confirmed: 'event_available',
    completed: 'check_circle',
    cancelled: 'cancel',
    converted: 'description',
  }
  return map[status] || 'info'
}

/**
 * Viewing status → hex color for calendar dots.
 * Uses the same palette as Quasar variables to stay in sync.
 */
export function statusDotColor(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'var(--q-info)',
    confirmed: 'var(--q-primary)',
    completed: 'var(--q-positive)',
    cancelled: 'var(--q-negative)',
    converted: 'var(--q-secondary)',
  }
  return map[status] || '#9e9e9e'
}

/** Short date: "10 Apr 2026" */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-ZA', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** Full date-time: "Thursday, 10 April, 09:00" */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-ZA', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Short date-time: "Thu, 10 Apr, 09:00" */
export function formatDateTimeShort(iso: string): string {
  return new Date(iso).toLocaleString('en-ZA', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Time only: "09:00" */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-ZA', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Days remaining until a date, or null if already passed */
export function daysRemaining(endDate: string): number | null {
  const diff = Math.ceil((new Date(endDate).getTime() - Date.now()) / 86400000)
  return diff > 0 ? diff : null
}
