/**
 * useTier — pricing-tier awareness composable.
 *
 * Fetches /api/v1/auth/agency/billing/ once and exposes reactive helpers
 * for feature-flag checks and quota status.
 *
 * Usage:
 *   const { hasFeature, quotaFor, isLoading, billingInfo, refresh } = useTier()
 *   if (!hasFeature('ai_lease_generation')) { showUpgradeCTA() }
 */
import { ref, computed } from 'vue'
import api from '../api'

// ── Types ────────────────────────────────────────────────────────────────────

export interface QuotaStatus {
  key: string
  used: number
  limit: number | null
  fraction: number | null
  warning: boolean
  blocked: boolean
  unlimited: boolean
}

export interface TierInfo {
  slug: string
  name: string
  price_monthly: number | null
  features: Record<string, boolean>
}

export interface BillingInfo {
  tier: TierInfo | null
  quotas: QuotaStatus[]
  upgrade_url: string
  all_tiers: Array<{
    slug: string
    name: string
    price_monthly: number | null
    price_label: string
    highlight: boolean
  }>
}

// ── Module-level singleton state (shared across component instances) ──────────

const billingInfo = ref<BillingInfo | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)
let _fetchPromise: Promise<void> | null = null

// ── Composable ───────────────────────────────────────────────────────────────

export function useTier() {
  /**
   * Fetch billing info from the API. Deduplicates concurrent calls.
   * Silently no-ops for non-admin users (403 is expected).
   */
  async function refresh(): Promise<void> {
    if (_fetchPromise) return _fetchPromise
    isLoading.value = true
    error.value = null
    _fetchPromise = api
      .get('/auth/agency/billing/')
      .then(({ data }) => {
        billingInfo.value = data
      })
      .catch((err) => {
        // 403 = not an admin/agency_admin — not an error we surface to users
        if (err?.response?.status !== 403) {
          error.value = err?.response?.data?.detail ?? 'Failed to load billing info'
        }
      })
      .finally(() => {
        isLoading.value = false
        _fetchPromise = null
      })
    return _fetchPromise
  }

  /**
   * Check whether the current agency's tier includes a feature.
   * Returns true when billing info is not yet loaded (optimistic — avoids
   * flash-of-upgrade-CTA while loading).
   */
  function hasFeature(featureSlug: string): boolean {
    if (!billingInfo.value) return true  // loading / not available → optimistic
    const tier = billingInfo.value.tier
    if (!tier) return true               // no tier set → all features enabled
    return tier.features[featureSlug] !== false
  }

  /**
   * Get the quota status for a named dimension.
   * Returns null if not found or billing not loaded.
   */
  function quotaFor(key: string): QuotaStatus | null {
    return billingInfo.value?.quotas.find((q) => q.key === key) ?? null
  }

  const tierSlug = computed(() => billingInfo.value?.tier?.slug ?? null)
  const tierName = computed(() => billingInfo.value?.tier?.name ?? 'Pro')
  const upgradeUrl = computed(
    () => billingInfo.value?.upgrade_url ?? 'https://klikk.co.za/pricing'
  )

  return {
    billingInfo,
    isLoading,
    error,
    tierSlug,
    tierName,
    upgradeUrl,
    hasFeature,
    quotaFor,
    refresh,
  }
}
