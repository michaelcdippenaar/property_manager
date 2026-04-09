/**
 * Landlords (property owners) Pinia store.
 *
 * Single source of truth for /properties/landlords/. Every view that lists,
 * reads, mutates or references a landlord goes through this store — no direct
 * axios calls in components for this entity.
 *
 * See `system_documentation/state_management_2026-04-09.md` for the
 * conventions every entity store follows.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import type { BankAccount, Landlord } from '../types/landlord'
import { extractApiError } from '../utils/api-errors'
import { isFresh } from './_helpers'

export const useLandlordsStore = defineStore('landlords', () => {
  // ─── State ────────────────────────────────────────────────────────────────
  const items = ref<Map<number, Landlord>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loadedAt = ref<number | null>(null)
  // Module-scoped (not exposed) — dedupes concurrent fetchAll() callers.
  let inflightFetchAll: Promise<void> | null = null

  // ─── Getters ──────────────────────────────────────────────────────────────
  const list = computed(() => [...items.value.values()])

  function byId(id: number): Landlord | undefined {
    return items.value.get(id)
  }

  // ─── Internals ────────────────────────────────────────────────────────────
  function upsert(ll: Landlord): Landlord {
    const normalised: Landlord = {
      ...ll,
      address:
        ll.address && typeof ll.address === 'object'
          ? ll.address
          : ({} as Landlord['address']),
    }
    items.value.set(ll.id, normalised)
    return normalised
  }

  // ─── Actions ──────────────────────────────────────────────────────────────
  async function fetchAll(opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && isFresh(loadedAt.value) && items.value.size > 0) return
    if (inflightFetchAll) return inflightFetchAll

    loading.value = true
    error.value = null
    inflightFetchAll = (async () => {
      try {
        const { data } = await api.get('/properties/landlords/')
        const rows: Landlord[] = data.results ?? data
        const next = new Map<number, Landlord>()
        for (const ll of rows) {
          next.set(ll.id, {
            ...ll,
            address:
              ll.address && typeof ll.address === 'object'
                ? ll.address
                : ({} as Landlord['address']),
          })
        }
        items.value = next
        loadedAt.value = Date.now()
      } catch (err) {
        error.value = extractApiError(err, 'Failed to load owners')
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
  ): Promise<Landlord> {
    const cached = items.value.get(id)
    if (cached && !opts.force && isFresh(loadedAt.value)) return cached
    try {
      const { data } = await api.get(`/properties/landlords/${id}/`)
      return upsert(data)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to load owner')
      throw err
    }
  }

  async function create(payload: Partial<Landlord>): Promise<Landlord> {
    try {
      const { data } = await api.post('/properties/landlords/', payload)
      const created = upsert(data)
      // Invalidate the list — next fetchAll() forces a refetch.
      loadedAt.value = null
      return created
    } catch (err) {
      error.value = extractApiError(err, 'Failed to create owner')
      throw err
    }
  }

  async function update(
    id: number,
    patch: Partial<Landlord>,
  ): Promise<Landlord> {
    // Strip read-only / nested fields the API does not accept on PATCH.
    const {
      bank_accounts: _bankAccounts,
      properties: _properties,
      property_count: _propertyCount,
      created_at: _createdAt,
      updated_at: _updatedAt,
      ...clean
    } = patch as Landlord
    void _bankAccounts
    void _properties
    void _propertyCount
    void _createdAt
    void _updatedAt
    try {
      const { data } = await api.patch(`/properties/landlords/${id}/`, clean)
      return upsert(data)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save owner')
      throw err
    }
  }

  async function remove(id: number): Promise<void> {
    try {
      await api.delete(`/properties/landlords/${id}/`)
      items.value.delete(id)
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete owner')
      throw err
    }
  }

  // ─── Bank account sub-resource ───────────────────────────────────────────
  // Bank accounts have their own top-level endpoint (`/properties/bank-accounts/`)
  // but are returned nested on the landlord. After every mutation we re-fetch
  // the parent landlord so its `bank_accounts` array stays in sync.

  async function saveBankAccount(
    landlordId: number,
    account: Partial<BankAccount> & { id?: number },
  ): Promise<Landlord> {
    try {
      if (account.id) {
        await api.patch(`/properties/bank-accounts/${account.id}/`, account)
      } else {
        await api.post('/properties/bank-accounts/', {
          ...account,
          landlord: landlordId,
        })
      }
      return fetchOne(landlordId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to save bank account')
      throw err
    }
  }

  async function deleteBankAccount(
    landlordId: number,
    accountId: number,
  ): Promise<Landlord> {
    try {
      await api.delete(`/properties/bank-accounts/${accountId}/`)
      return fetchOne(landlordId, { force: true })
    } catch (err) {
      error.value = extractApiError(err, 'Failed to delete bank account')
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
    // getters
    list,
    byId,
    // actions
    fetchAll,
    fetchOne,
    create,
    update,
    remove,
    saveBankAccount,
    deleteBankAccount,
    invalidate,
  }
})
