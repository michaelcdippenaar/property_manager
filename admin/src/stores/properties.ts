/**
 * Properties (and units) Pinia store.
 *
 * Single source of truth for /properties/. Every list, detail, edit and unit
 * sub-resource read goes through this store. Photos and documents stay
 * view-local in PropertyDetailView (large lists, only ever read in one place).
 *
 * See `system_documentation/state_management_2026-04-09.md` for the
 * conventions every entity store follows.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import type { Property, Unit } from '../types/property'

export interface PortfolioMaintenanceItem {
  id: number
  title: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: string
  created_at: string
  days_open: number
}

export interface PortfolioActiveLease {
  id: number
  lease_number: string
  status: string
  start_date: string | null
  end_date: string | null
  signed_at: string | null
  monthly_rent: string | null
  deposit: string | null
  notice_period_days: number
  notice_window_date: string | null
  tenant_name: string
  all_tenant_names: string[]
  successor_lease_id: number | null
}

export interface PortfolioEntry {
  property_id: number
  property_name: string
  property_address: string
  property_type: string
  units_total: number
  units_occupied: number
  active_lease: PortfolioActiveLease | null
  top_maintenance: PortfolioMaintenanceItem[]
  open_maintenance_count: number
}
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'

// We page-size up to 500 to match the prior behaviour of every list view.
// Document the limitation in `state_management_2026-04-09.md`.
const PAGE_SIZE = 500

export const usePropertiesStore = defineStore('properties', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const items = ref<Map<number, Property>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loadedAt = ref<number | null>(null)
  // Module-scoped (not exposed) — dedupes concurrent fetchAll() callers.
  let inflightFetchAll: Promise<void> | null = null

  // ─── Getters ──────────────────────────────────────────────────────────────
  const list = computed(() => [...items.value.values()])

  function byId(id: number): Property | undefined {
    return items.value.get(id)
  }

  // ─── Internals ────────────────────────────────────────────────────────────
  function upsert(p: Property): Property {
    items.value.set(p.id, p)
    return p
  }

  // ─── Actions ──────────────────────────────────────────────────────────────
  async function fetchAll(opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && isFresh(loadedAt.value) && items.value.size > 0) return
    if (inflightFetchAll) return inflightFetchAll

    loading.value = true
    error.value = null
    inflightFetchAll = (async () => {
      try {
        const { data } = await api.get(`/properties/?page_size=${PAGE_SIZE}`)
        const rows: Property[] = data.results ?? data
        const next = new Map<number, Property>()
        for (const p of rows) next.set(p.id, p)
        items.value = next
        loadedAt.value = Date.now()
      } catch (err) {
        error.value = extractApiError(err, 'Failed to load properties')
        throw err
      } finally {
        loading.value = false
        inflightFetchAll = null
      }
    })()
    return inflightFetchAll
  }

  async function fetchOne(
    id: number,
    opts: { force?: boolean } = {},
  ): Promise<Property> {
    const cached = items.value.get(id)
    if (cached && !opts.force && isFresh(loadedAt.value)) return cached
    try {
      const { data } = await api.get(`/properties/${id}/`)
      return upsert(data)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load property')
      throw err
    }
  }

  async function create(payload: Partial<Property>): Promise<Property> {
    try {
      const { data } = await api.post('/properties/', payload)
      const created = upsert(data)
      // Invalidate the list — next fetchAll() forces a refetch.
      loadedAt.value = null
      return created
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create property')
      throw err
    }
  }

  async function update(
    id: number,
    patch: Partial<Property>,
  ): Promise<Property> {
    // Strip read-only / nested fields the API does not accept on PATCH.
    const {
      units: _units,
      unit_count: _unitCount,
      nearest_lease_expiry: _nle,
      property_active_lease_info: _pali,
      created_at: _createdAt,
      ...clean
    } = patch as Property
    void _units
    void _unitCount
    void _nle
    void _pali
    void _createdAt
    try {
      const { data } = await api.patch(`/properties/${id}/`, clean)
      return upsert(data)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save property')
      throw err
    }
  }

  async function remove(id: number): Promise<void> {
    try {
      await api.delete(`/properties/${id}/`)
      items.value.delete(id)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete property')
      throw err
    }
  }

  // ─── Dashboard portfolio ────────────────────────────────────────────────
  // Lightweight rollup for DashboardView — returns per-property lifecycle
  // snapshot (active lease, top maintenance, notice window). View-local cache.

  const portfolio = ref<PortfolioEntry[]>([])
  const portfolioLoading = ref(false)
  const portfolioLoadedAt = ref<number | null>(null)

  async function fetchPortfolio(opts: { force?: boolean } = {}): Promise<PortfolioEntry[]> {
    if (!opts.force && isFresh(portfolioLoadedAt.value) && portfolio.value.length > 0) {
      return portfolio.value
    }
    portfolioLoading.value = true
    try {
      const { data } = await api.get('/dashboard/portfolio/')
      const rows: PortfolioEntry[] = Array.isArray(data) ? data : (data.results ?? [])
      portfolio.value = rows
      portfolioLoadedAt.value = Date.now()
      return rows
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load portfolio')
      throw err
    } finally {
      portfolioLoading.value = false
    }
  }

  // ─── Unit sub-resource ───────────────────────────────────────────────────
  // Units are returned inline on the parent Property. After every mutation
  // we re-fetch the parent so its `units` array stays in sync — keeps the
  // store as the single source of truth without a parallel unit map.

  async function updateUnit(
    unitId: number,
    propertyId: number,
    patch: Partial<Unit>,
  ): Promise<Property> {
    try {
      await api.patch(`/properties/units/${unitId}/`, patch)
      return fetchOne(propertyId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save unit')
      throw err
    }
  }

  async function createUnit(
    propertyId: number,
    payload: Partial<Unit>,
  ): Promise<Property> {
    try {
      await api.post('/properties/units/', { ...payload, property: propertyId })
      return fetchOne(propertyId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create unit')
      throw err
    }
  }

  async function deleteUnit(
    unitId: number,
    propertyId: number,
  ): Promise<Property> {
    try {
      await api.delete(`/properties/units/${unitId}/`)
      return fetchOne(propertyId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete unit')
      throw err
    }
  }

  function invalidate(id?: number): void {
    if (id === undefined) {
      loadedAt.value = null
    } else {
      items.value.delete(id)
      loadedAt.value = null
    }
  }

  return {
    // state
    items,
    loading,
    error,
    loadedAt,
    portfolio,
    portfolioLoading,
    // getters
    list,
    byId,
    // actions
    fetchAll,
    fetchOne,
    fetchPortfolio,
    create,
    update,
    remove,
    updateUnit,
    createUnit,
    deleteUnit,
    invalidate,
  }
})
