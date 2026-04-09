/**
 * PropertyOwnerships Pinia store.
 *
 * Source of truth for /properties/ownerships/. Ownerships are *always* scoped
 * to a specific Property, so the canonical state shape is
 * `byProperty: Map<propertyId, Ownership[]>` rather than a flat keyed map.
 * The "current" ownership is derived (`is_current === true`) — no separate
 * Map to keep in sync.
 *
 * After every mutation we re-fetch that property's ownership history AND
 * touch both the landlords store (denormalized `property_count`) and the
 * properties store (denormalized active-ownership info on the parent).
 *
 * See `system_documentation/state_management_2026-04-09.md` for the
 * conventions every entity store follows.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import type { PropertyOwnership } from '../types/ownership'
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'
import { useLandlordsStore } from './landlords'
import { usePropertiesStore } from './properties'

export const useOwnershipsStore = defineStore('ownerships', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const byProperty = ref<Map<number, PropertyOwnership[]>>(new Map())
  const loadedAtByProperty = ref<Map<number, number>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ─── Getters ──────────────────────────────────────────────────────────────
  const list = computed(() => {
    const out: PropertyOwnership[] = []
    for (const arr of byProperty.value.values()) out.push(...arr)
    return out
  })

  function forProperty(propertyId: number): PropertyOwnership[] {
    return byProperty.value.get(propertyId) ?? []
  }

  function currentForProperty(propertyId: number): PropertyOwnership | null {
    return forProperty(propertyId).find(o => o.is_current) ?? null
  }

  // ─── Actions ──────────────────────────────────────────────────────────────
  async function fetchByProperty(
    propertyId: number,
    opts: { force?: boolean } = {},
  ): Promise<PropertyOwnership[]> {
    const cachedAt = loadedAtByProperty.value.get(propertyId)
    if (!opts.force && isFresh(cachedAt ?? null) && byProperty.value.has(propertyId)) {
      return forProperty(propertyId)
    }
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get(`/properties/ownerships/?property=${propertyId}`)
      const rows: PropertyOwnership[] = data.results ?? data
      byProperty.value.set(propertyId, rows)
      loadedAtByProperty.value.set(propertyId, Date.now())
      return rows
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load ownerships')
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Convenience: load just the current ownership. Calls the dedicated
   * endpoint (`/ownerships/current/{pid}/`) which is cheaper than the full
   * history list, and still upserts into the byProperty map so the next
   * `forProperty` / history call has at least one row.
   */
  async function fetchCurrent(propertyId: number): Promise<PropertyOwnership | null> {
    try {
      const { data } = await api.get(`/properties/ownerships/current/${propertyId}/`)
      const existing = byProperty.value.get(propertyId) ?? []
      const without = existing.filter(o => o.id !== data.id)
      // Mark this row as current; clear current flag on the rest of the list.
      const merged = [
        { ...data, is_current: true },
        ...without.map(o => ({ ...o, is_current: false })),
      ]
      byProperty.value.set(propertyId, merged)
      return merged[0]
    } catch (err: any) {
      if (err?.response?.status === 404) {
        // No current ownership — clear cached entries for this property.
        byProperty.value.set(propertyId, [])
        return null
      }
      error.value = extractApiError(err, 'Failed to load current ownership')
      throw err
    }
  }

  async function create(payload: Partial<PropertyOwnership>): Promise<PropertyOwnership> {
    try {
      const { data } = await api.post('/properties/ownerships/', payload)
      // Re-fetch the parent's full history so derived getters and the
      // "current" flag stay correct.
      if (data.property) await fetchByProperty(data.property, { force: true })
      await invalidateLinkedStores(data)
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create ownership')
      throw err
    }
  }

  async function update(
    id: number,
    propertyId: number,
    patch: Partial<PropertyOwnership>,
  ): Promise<PropertyOwnership> {
    try {
      const { data } = await api.patch(`/properties/ownerships/${id}/`, patch)
      await fetchByProperty(propertyId, { force: true })
      await invalidateLinkedStores(data)
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save ownership')
      throw err
    }
  }

  async function remove(id: number, propertyId: number): Promise<void> {
    // Capture the row so we can invalidate the right landlord after deletion.
    const cached = forProperty(propertyId).find(o => o.id === id)
    try {
      await api.delete(`/properties/ownerships/${id}/`)
      await fetchByProperty(propertyId, { force: true })
      if (cached) await invalidateLinkedStores(cached)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete ownership')
      throw err
    }
  }

  /**
   * After any ownership mutation, force-refresh the affected landlord and
   * property in their respective stores so denormalized fields
   * (`property_count`, parent property's owner info) stay in sync.
   * Both calls are best-effort — view-level error handling owns user feedback.
   */
  async function invalidateLinkedStores(ownership: any): Promise<void> {
    const landlordsStore = useLandlordsStore()
    const propertiesStore = usePropertiesStore()
    if (ownership.landlord) {
      try { await landlordsStore.fetchOne(ownership.landlord, { force: true }) } catch { /* non-fatal */ }
    }
    if (ownership.property) {
      try { await propertiesStore.fetchOne(ownership.property, { force: true }) } catch { /* non-fatal */ }
    }
  }

  function invalidate(propertyId?: number): void {
    if (propertyId === undefined) {
      byProperty.value = new Map()
      loadedAtByProperty.value = new Map()
    } else {
      byProperty.value.delete(propertyId)
      loadedAtByProperty.value.delete(propertyId)
    }
  }

  return {
    // state
    byProperty,
    loadedAtByProperty,
    loading,
    error,
    // getters
    list,
    forProperty,
    currentForProperty,
    // actions
    fetchByProperty,
    fetchCurrent,
    create,
    update,
    remove,
    invalidate,
  }
})
