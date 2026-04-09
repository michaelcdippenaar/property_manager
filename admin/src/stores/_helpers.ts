/**
 * Shared helpers for entity Pinia stores.
 *
 * See `system_documentation/state_management_2026-04-09.md` for the
 * conventions every entity store follows.
 */

/** How long a `loadedAt` timestamp is considered fresh — skips refetch within this window. */
export const STALENESS_TTL_MS = 30_000

/** True if the cache is still within the staleness window. */
export function isFresh(loadedAt: number | null | undefined): boolean {
  if (!loadedAt) return false
  return Date.now() - loadedAt < STALENESS_TTL_MS
}
