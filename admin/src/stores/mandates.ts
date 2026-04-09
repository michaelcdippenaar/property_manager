/**
 * RentalMandates Pinia store.
 *
 * Source of truth for /properties/mandates/. Mandates authorise an agency to
 * manage a landlord's property and are scoped per Property — the canonical
 * shape is `byProperty: Map<propertyId, RentalMandate[]>`. Most properties
 * have at most one or two mandates (current + historical), so we keep the
 * full list per property rather than indexing by mandate id.
 *
 * The signing-action subresource (`POST /mandates/{id}/send-for-signing/`)
 * lives here too — it mutates state (status flips to `sent_for_signing`),
 * so it warrants a store action that re-fetches the affected property's
 * mandate list afterwards.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'

// The view uses an extended shape (mandate_type, exclusivity, commission_rate,
// commission_period, notice_period_days, maintenance_threshold) that's not yet
// captured in `types/mandate.ts`. Until that type is finalized we accept `any`.
type Mandate = any

export const useMandatesStore = defineStore('mandates', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const byProperty = ref<Map<number, Mandate[]>>(new Map())
  const loadedAtByProperty = ref<Map<number, number>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ─── Getters ──────────────────────────────────────────────────────────────
  const list = computed(() => {
    const out: Mandate[] = []
    for (const arr of byProperty.value.values()) out.push(...arr)
    return out
  })

  function forProperty(propertyId: number): Mandate[] {
    return byProperty.value.get(propertyId) ?? []
  }

  // ─── Actions ──────────────────────────────────────────────────────────────
  async function fetchByProperty(
    propertyId: number,
    opts: { force?: boolean } = {},
  ): Promise<Mandate[]> {
    const cachedAt = loadedAtByProperty.value.get(propertyId)
    if (!opts.force && isFresh(cachedAt ?? null) && byProperty.value.has(propertyId)) {
      return forProperty(propertyId)
    }
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/properties/mandates/', { params: { property: propertyId } })
      const rows: Mandate[] = data.results ?? data
      byProperty.value.set(propertyId, rows)
      loadedAtByProperty.value.set(propertyId, Date.now())
      return rows
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load mandates')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Partial<Mandate>): Promise<Mandate> {
    try {
      const { data } = await api.post('/properties/mandates/', payload)
      if (data.property) await fetchByProperty(data.property, { force: true })
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create mandate')
      throw err
    }
  }

  async function update(
    id: number,
    propertyId: number,
    patch: Partial<Mandate>,
  ): Promise<Mandate> {
    try {
      const { data } = await api.patch(`/properties/mandates/${id}/`, patch)
      await fetchByProperty(propertyId, { force: true })
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save mandate')
      throw err
    }
  }

  async function remove(id: number, propertyId: number): Promise<void> {
    try {
      await api.delete(`/properties/mandates/${id}/`)
      await fetchByProperty(propertyId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete mandate')
      throw err
    }
  }

  /**
   * Trigger the e-signing flow for a mandate. Backend flips the mandate's
   * status, so we re-fetch the parent property's list to pick up the new
   * state.
   */
  async function sendForSigning(id: number, propertyId: number): Promise<void> {
    try {
      await api.post(`/properties/mandates/${id}/send-for-signing/`)
      await fetchByProperty(propertyId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to send mandate for signing')
      throw err
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
    // actions
    fetchByProperty,
    create,
    update,
    remove,
    sendForSigning,
    invalidate,
  }
})
