/**
 * Persons & Tenants Pinia store.
 *
 * Two related collections live here:
 *
 *  - `persons`: keyed `Map<number, Person>` backed by `/auth/persons/`. These
 *    are the rich Person records (tenants, occupants, guarantors) attached to
 *    leases. Mutations are surgical (`updatePerson(id, patch)`) — there is no
 *    list endpoint we use for the full set, so the map is populated on-demand.
 *
 *  - `tenants`: plain array backed by `/auth/tenants/`, the lighter projection
 *    consumed by TenantsView. Refreshed via `fetchTenants()`; respects 30s
 *    staleness window like every other store.
 *
 * `createPerson()` invalidates `tenantsLoadedAt` so the next visit to
 * TenantsView refetches and shows the new tenant. View-level error handling
 * owns the toast — the store re-throws.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import type { Person, Tenant } from '../types/person'
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'

export const usePersonsStore = defineStore('persons', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const persons = ref<Map<number, Person>>(new Map())
  const tenants = ref<Tenant[]>([])
  const tenantsLoadedAt = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let inflightFetchTenants: Promise<void> | null = null

  // ─── Getters ──────────────────────────────────────────────────────────────
  const tenantsList = computed(() => tenants.value)

  function personById(id: number): Person | undefined {
    return persons.value.get(id)
  }

  // ─── Actions: tenants ─────────────────────────────────────────────────────
  async function fetchTenants(opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && isFresh(tenantsLoadedAt.value) && tenants.value.length > 0) return
    if (inflightFetchTenants) return inflightFetchTenants

    loading.value = true
    error.value = null
    inflightFetchTenants = (async () => {
      try {
        const { data } = await api.get('/auth/tenants/')
        tenants.value = data.results ?? data
        tenantsLoadedAt.value = Date.now()
      } catch (err) {
        error.value = extractApiError(err, 'Failed to load tenants')
        throw err
      } finally {
        loading.value = false
        inflightFetchTenants = null
      }
    })()
    return inflightFetchTenants
  }

  // ─── Actions: persons ─────────────────────────────────────────────────────
  async function createPerson(payload: Partial<Person>): Promise<Person> {
    try {
      const { data } = await api.post('/auth/persons/', payload)
      persons.value.set(data.id, data)
      // A new Person may show up in /auth/tenants/ — invalidate so the next
      // TenantsView visit refetches.
      tenantsLoadedAt.value = null
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create person')
      throw err
    }
  }

  async function fetchPerson(id: number): Promise<Person> {
    try {
      const { data } = await api.get(`/auth/persons/${id}/`)
      persons.value.set(data.id, data)
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load person')
      throw err
    }
  }

  async function updatePerson(id: number, patch: Partial<Person>): Promise<Person> {
    try {
      const { data } = await api.patch(`/auth/persons/${id}/`, patch)
      persons.value.set(data.id, data)
      // Updated contact details may flow into /auth/tenants/ projection too.
      tenantsLoadedAt.value = null
      return data
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save person')
      throw err
    }
  }

  function invalidate(): void {
    tenantsLoadedAt.value = null
  }

  return {
    // state
    persons,
    tenants,
    tenantsLoadedAt,
    loading,
    error,
    // getters
    tenantsList,
    personById,
    // actions
    fetchTenants,
    fetchPerson,
    createPerson,
    updatePerson,
    invalidate,
  }
})
