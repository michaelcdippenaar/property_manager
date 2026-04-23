/**
 * useFeatureFlags — Feature-gating convention for the Klikk Admin SPA
 *
 * ## Convention
 * All features are defined in `content/product/features.yaml` (source of truth).
 * Status values: BUILT | IN_PROGRESS | PLANNED | BETA
 *
 * Any feature with status PLANNED must be hidden or disabled in the UI.
 * Do NOT show PLANNED features as active nav items, action buttons, or menu
 * items — agents must never encounter a dead-end workflow.
 *
 * ## How to gate a new PLANNED feature
 * 1. Add its slug to PLANNED_FEATURES below (copy the slug from features.yaml).
 * 2. In the component, call `isPlanned('your-feature-slug')` and hide/disable
 *    the element conditionally.
 * 3. When the feature ships, remove the slug from PLANNED_FEATURES and set
 *    `status: BUILT` + `shipped_date` in features.yaml.
 *
 * ## Why a static map instead of importing the YAML at runtime?
 * The features.yaml is the authoring source of truth, not a runtime config.
 * Importing and parsing YAML adds a runtime dependency and bundle weight.
 * Instead, the implementer syncs the PLANNED list here when adding/shipping
 * a feature — the same discipline as updating features.yaml.
 *
 * Sourced from content/product/features.yaml — last synced 2026-04-23.
 */

/**
 * Feature slugs (from features.yaml) whose status is currently PLANNED.
 * These will be hidden or shown as "Coming soon" in the admin SPA.
 *
 * Rentals PLANNED:
 *   vacancy-advertising, tenant-screening, deposit-management,
 *   incoming-inspection, notice-management, outgoing-inspection, deposit-refund
 *
 * Real Estate PLANNED: all (seller-prospecting, property-valuation, ...)
 * BI PLANNED: all (market-analytics, agency-dashboard, lead-analytics)
 *
 * Only rentals slugs are relevant to this SPA's current scope.
 */
const PLANNED_FEATURES = new Set<string>([
  // ── Rentals ──
  'vacancy-advertising',
  'tenant-screening',
  'deposit-management',
  'incoming-inspection',
  'notice-management',
  'outgoing-inspection',
  'deposit-refund',
  // ── Real Estate (not yet in this SPA, listed for completeness) ──
  'seller-prospecting',
  'property-valuation',
  'mandate-signing',
  'sales-listing-marketing',
  'sales-viewings',
  'offer-negotiation',
  'otp-signing',
  'buyer-documentation',
  'bond-approval-tracking',
  'legal-compliance-certs',
  'property-transfer',
  // ── BI ──
  'market-analytics',
  'agency-dashboard',
  'lead-analytics',
])

/**
 * Returns true when the given feature slug has status PLANNED and therefore
 * should be hidden or disabled in the UI.
 *
 * Usage:
 *   const { isPlanned } = useFeatureFlags()
 *   // In template: v-if="!isPlanned('vacancy-advertising')"
 */
export function useFeatureFlags() {
  function isPlanned(slug: string): boolean {
    return PLANNED_FEATURES.has(slug)
  }

  return { isPlanned }
}
