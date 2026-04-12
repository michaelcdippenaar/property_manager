// ─── Shared design tokens for consistent sizing across the Agent App ─────────

/** Full-page loading spinners (centre of page) */
export const SPINNER_SIZE_PAGE = '36px'

/** Inline/tab loading spinners (within a card or section) */
export const SPINNER_SIZE_INLINE = '24px'

/** Empty-state illustration icons */
export const EMPTY_ICON_SIZE = '48px'

/** Profile / hero avatars (settings, detail page headers) */
export const AVATAR_PROFILE = '48px'

/** Standard list-item avatars (viewings, contacts, properties) */
export const AVATAR_LIST = '40px'

/** Compact list-item avatars (dense lists, tab content) */
export const AVATAR_COMPACT = '36px'

// ─── Validation rules (reusable across all forms) ────────────────────────────

export const RULES = {
  required: (v: unknown) => !!v || 'Required',
  requiredSelect: (v: unknown) => !!v || 'Please select an option',
  positiveNumber: (v: unknown) => (!!v && Number(v) > 0) || 'Enter a valid amount',
  email: (v: string) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Enter a valid email',
} as const

// ─── Currency formatter ──────────────────────────────────────────────────────

/** Format a number as ZAR with locale grouping: 12500 → "12,500" */
export function formatZAR(amount: string | number): string {
  return Number(amount).toLocaleString('en-ZA')
}
