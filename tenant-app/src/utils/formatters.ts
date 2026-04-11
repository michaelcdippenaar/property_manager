// ─── Shared formatters & color maps for the Tenant App ───────────────────────

/** Maintenance status → Quasar color name */
export function maintenanceStatusColor(status: string): string {
  const map: Record<string, string> = {
    open: 'info',
    in_progress: 'warning',
    resolved: 'positive',
    closed: 'grey-5',
  }
  return map[status] || 'grey'
}

/** Priority → Quasar color name */
export function priorityColor(priority: string): string {
  const map: Record<string, string> = {
    urgent: 'negative',
    high: 'warning',
    medium: 'info',
    low: 'grey-5',
  }
  return map[priority] || 'grey'
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

/** Signer status → Quasar color name */
export function signerStatusColor(status: string): string {
  const map: Record<string, string> = {
    completed: 'positive',
    pending: 'warning',
    declined: 'negative',
  }
  return map[status] || 'grey'
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

/** ZAR currency format: "R 12,500.00" */
export function formatCurrency(val: string | number): string {
  return `R ${Number(val).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}`
}

/** Ordinal suffix: 1st, 2nd, 3rd, 4th... */
export function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}
