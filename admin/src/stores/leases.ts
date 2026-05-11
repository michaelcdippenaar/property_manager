/**
 * Leases Pinia store.
 *
 * Single source of truth for /leases/. Lease lists, individual lease reads,
 * mutations, and the per-property/per-unit "active lease" lookups go through
 * this store. View-local subresources (documents, inventory, generated PDFs,
 * import/parse, builder drafts, e-signing submissions) stay direct-axios in
 * the views that own them — see plan: state_management_2026-04-09.md.
 *
 * Cross-store invalidation: lease mutations that may reshape the parent
 * Property (auto_created_unit, status changes that flip occupancy) call
 * `usePropertiesStore().fetchOne(pid, { force: true })` from inside the
 * action body. Pinia supports this — the import is local, no module-level
 * circular dependency hazard.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import type { Lease } from '../types/lease'
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'
import { usePropertiesStore } from './properties'

export const useLeasesStore = defineStore('leases', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const items = ref<Map<number, Lease>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loadedAt = ref<number | null>(null)
  // Module-scoped (not exposed) — dedupes concurrent fetchAll() callers.
  let inflightFetchAll: Promise<void> | null = null

  // ─── Getters ──────────────────────────────────────────────────────────────
  const list = computed(() => [...items.value.values()])

  function byId(id: number): Lease | undefined {
    return items.value.get(id)
  }

  // ─── Internals ────────────────────────────────────────────────────────────
  function upsert(l: Lease): Lease {
    items.value.set(l.id, l)
    return l
  }

  // ─── Actions ──────────────────────────────────────────────────────────────
  async function fetchAll(opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && isFresh(loadedAt.value) && items.value.size > 0) return
    if (inflightFetchAll) return inflightFetchAll

    loading.value = true
    error.value = null
    inflightFetchAll = (async () => {
      try {
        const { data } = await api.get('/leases/')
        const rows: Lease[] = data.results ?? data
        const next = new Map<number, Lease>()
        for (const l of rows) next.set(l.id, l)
        items.value = next
        loadedAt.value = Date.now()
      } catch (err) {
        error.value = extractApiError(err, 'Failed to load leases')
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
  ): Promise<Lease> {
    const cached = items.value.get(id)
    if (cached && !opts.force && isFresh(loadedAt.value)) return cached
    try {
      const { data } = await api.get(`/leases/${id}/`)
      return upsert(data)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load lease')
      throw err
    }
  }

  /**
   * Lookup the active (or pending fallback) lease for a property or a unit.
   * Returns the lease or null. Does NOT cache — these are lightweight
   * single-result calls and the view that triggers them owns the local copy.
   * If the result reshapes data we already have in `items`, upsert it so list
   * consumers see the same object.
   */
  async function fetchActiveFor(
    params: { property?: number; unit?: number },
  ): Promise<Lease | null> {
    try {
      for (const statusVal of ['active', 'pending'] as const) {
        const { data } = await api.get('/leases/', {
          params: { ...params, status: statusVal, page_size: 1 },
        })
        const found: Lease | undefined = (data.results ?? data)[0]
        if (found) {
          upsert(found)
          return found
        }
      }
      return null
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load active lease')
      throw err
    }
  }

  /**
   * Fetch leases for a unit (used by PropertyDetailView's "previous leases"
   * panel). Returns the array unfiltered — the view decides what to show.
   * Upserts each into the keyed map.
   */
  async function fetchForUnit(unitId: number): Promise<Lease[]> {
    try {
      const { data } = await api.get('/leases/', {
        params: { unit: unitId, page_size: 20 },
      })
      const rows: Lease[] = data.results ?? data
      for (const l of rows) upsert(l)
      return rows
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load leases for unit')
      throw err
    }
  }

  async function create(payload: Partial<Lease> & Record<string, unknown>): Promise<Lease> {
    try {
      const { data } = await api.post('/leases/', payload)
      const created = upsert(data)
      // Invalidate the list — next fetchAll() forces a refetch.
      loadedAt.value = null
      // Cross-store: if the backend auto-created a unit, the parent Property's
      // `units` array is now stale. Force-refresh it.
      await maybeRefreshParentProperty(data)
      return created
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create lease')
      throw err
    }
  }

  /**
   * Builder finalize / import endpoint (`POST /leases/import/`). Same upsert
   * + invalidation semantics as `create`. Used by LeaseBuilderView and
   * ImportLeaseWizard which both end at the import path.
   */
  async function importLease(payload: Record<string, unknown>): Promise<Lease> {
    try {
      const { data } = await api.post('/leases/import/', payload)
      const created = upsert(data) as Lease & { matched_persons?: any[] }
      loadedAt.value = null
      // Pass through the backend's matched_persons (existing-tenant dedupe
      // signal) so the wizard can surface "Linked to existing tenant: …"
      // toasts. Not a persistent Lease field — attached on the returned
      // instance only, audit Bug 9.
      if (Array.isArray(data?.matched_persons)) {
        created.matched_persons = data.matched_persons
      }
      await maybeRefreshParentProperty(data)
      return created
    } catch (err) {
      error.value = extractApiError(err, 'Failed to import lease')
      throw err
    }
  }

  async function update(
    id: number,
    patch: Partial<Lease> & Record<string, unknown>,
  ): Promise<Lease> {
    // Strip read-only / nested fields the API does not accept on PATCH.
    const {
      unit_label: _unitLabel,
      property_id: _propertyId,
      primary_tenant_detail: _primaryTenantDetail,
      tenant_name: _tenantName,
      all_tenant_names: _allTenantNames,
      co_tenants: _coTenants,
      occupants: _occupants,
      guarantors: _guarantors,
      documents: _documents,
      document_count: _documentCount,
      landlord_info: _landlordInfo,
      ai_parse_result: _aiParseResult,
      created_at: _createdAt,
      ...clean
    } = patch as Lease
    void _unitLabel
    void _propertyId
    void _primaryTenantDetail
    void _tenantName
    void _allTenantNames
    void _coTenants
    void _occupants
    void _guarantors
    void _documents
    void _documentCount
    void _landlordInfo
    void _aiParseResult
    void _createdAt
    try {
      const { data } = await api.patch(`/leases/${id}/`, clean)
      const updated = upsert(data)
      // A status change can flip unit occupancy on the parent property.
      await maybeRefreshParentProperty(data)
      return updated
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save lease')
      throw err
    }
  }

  /**
   * Create a successor lease following the given source. Backend copies
   * property/unit/rent/deposit/terms; tenants are NOT copied (see plan).
   * Any `overrides` passed are merged on top before save (start/end dates,
   * rent, etc.).
   */
  /**
   * Fetch all leases where the given Person is the primary tenant.
   * Uses the `primary_tenant` filter exposed by the backend.
   */
  async function fetchForPerson(personId: number): Promise<Lease[]> {
    try {
      const { data } = await api.get('/leases/', {
        params: { primary_tenant: personId, page_size: 50 },
      })
      const rows: Lease[] = data.results ?? data
      for (const l of rows) upsert(l)
      return rows
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load leases for tenant')
      throw err
    }
  }

  async function createRenewal(
    sourceId: number,
    overrides: Record<string, unknown> = {},
  ): Promise<Lease> {
    try {
      const { data } = await api.post(`/leases/${sourceId}/renewal/`, overrides)
      const created = upsert(data)
      loadedAt.value = null
      await maybeRefreshParentProperty(data)
      // Refresh the source so its successor_lease_id is up to date.
      try { await fetchOne(sourceId, { force: true }) } catch { /* non-fatal */ }
      return created
    } catch (err) {
      error.value = extractApiError(err, 'Failed to draft renewal')
      throw err
    }
  }

  async function remove(id: number): Promise<void> {
    const cached = items.value.get(id)
    try {
      await api.delete(`/leases/${id}/`)
      items.value.delete(id)
      // Refresh the parent property — its active-lease info is now stale.
      if (cached) await maybeRefreshParentProperty(cached)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete lease')
      throw err
    }
  }

  /**
   * Cross-store invalidation hook. Called by `create`, `update`, and `remove`.
   * If the lease references a property we know about, force-refresh it so
   * `units[].active_lease_info` and the inline unit array stay in sync.
   *
   * `usePropertiesStore` is imported at the top of the file — Pinia handles
   * this fine because both stores are setup-style (no module-execution-order
   * traps), and the call is inside an action body, not at module load.
   */
  async function maybeRefreshParentProperty(lease: any): Promise<void> {
    const pid = lease?.property_id ?? lease?.property
    if (!pid) return
    try {
      const propertiesStore = usePropertiesStore()
      await propertiesStore.fetchOne(pid, { force: true })
    } catch {
      /* non-fatal — view-level error handling owns user feedback */
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
    // getters
    list,
    byId,
    // actions
    fetchAll,
    fetchOne,
    fetchActiveFor,
    fetchForUnit,
    fetchForPerson,
    create,
    importLease,
    update,
    remove,
    createRenewal,
    invalidate,
  }
})
