# Admin State Management — Pinia Stores

**Status:** Migration complete (2026-04-09). Phases 0–5 landed; only `viewings` was deferred (no admin consumers exist). Subsequent entity work should follow the conventions below.

## Why this exists

Before this refactor, every view fetched its own data with `api.get(...)`. The same entity (e.g. landlords) was loaded by 5+ views with no shared cache. Mutations in one view never updated others. We patched the symptom with `onActivated(loadX)` workarounds in `<KeepAlive>`-cached views, but the underlying problem was that the data layer was scattered across components.

This Pinia migration centralises all entity data into one store per entity, so every view reads from the same source of truth and mutations are reactive across the app. The plan, decisions, and per-phase verification steps live in `~/.claude/plans/polished-munching-stroustrup.md`.

## When to use a store

Use a store when:
- The entity has its own DRF endpoint (`/properties/`, `/properties/landlords/`, `/leases/`).
- More than one view reads or writes it.
- Mutations in one view need to be visible in another without manual refresh.

Do NOT put in a store:
- View-local sub-resources only ever read in one place (e.g. `/properties/{id}/photos/`, `/leases/{id}/inventory/`).
- One-shot dashboard fetches with no consistency requirement.
- TipTap editor state (already in `template.ts`).
- GraphQL data (already in `contract.ts`).
- PDF blobs and one-off generate calls.

## Conventions every entity store follows

### Style

Composition-API setup function with `defineStore(...)`. Imports the axios client (`admin/src/api.ts`) directly — **no service layer**. Mirrors `admin/src/stores/auth.ts`.

### File layout

```
admin/src/
  types/                 ← TS types mirroring the backend serializers
    landlord.ts
    property.ts
    lease.ts
    ...
    index.ts             ← barrel
  stores/
    _helpers.ts          ← isFresh(), STALENESS_TTL_MS
    auth.ts              ← unchanged reference pattern
    landlords.ts         ← entity stores
    properties.ts
    leases.ts
    ...
```

### State shape

Entities with detail views (landlords, properties, leases) use a normalised `Map<number, T>`. Entities consumed only as flat lists (tenants, viewings) may use a plain array.

```ts
const items = ref<Map<number, T>>(new Map())
const loading = ref(false)
const error = ref<string | null>(null)
const loadedAt = ref<number | null>(null)
let inflightFetchAll: Promise<void> | null = null   // module-scoped, not exposed
```

### Standard actions

Every entity store exposes:

| Action | Purpose |
|---|---|
| `fetchAll(opts?: { force?: boolean })` | List endpoint. Skips if `isFresh(loadedAt)` and not forced. Dedupes concurrent calls via `inflightFetchAll`. |
| `fetchOne(id, opts?: { force?: boolean })` | Detail endpoint. Upserts into the map. |
| `create(payload)` | POST. Upserts response into the map and clears `loadedAt` to invalidate the list. |
| `update(id, patch)` | PATCH. Upserts response. |
| `remove(id)` | DELETE. Removes from the map. |
| `invalidate(id?)` | Clears `loadedAt` (all) or removes one entry. |

### Error handling

Stores set `error.value = extractApiError(err, 'fallback')` AND **re-throw** so components can `toast.error(err)`. Stores **never** import `useToast` — that mixes presentation into the data layer.

### Component consumption pattern

```ts
import { storeToRefs } from 'pinia'
import { useLandlordsStore } from '../../stores/landlords'
import { useToast } from '../../composables/useToast'

const landlordsStore = useLandlordsStore()
const { list: landlords, loading } = storeToRefs(landlordsStore)
const toast = useToast()

onMounted(() => {
  landlordsStore.fetchAll().catch((err) => toast.error(extractApiError(err, '...')))
})
// NO onActivated — store reactivity handles cross-view updates.
```

### Cross-store invalidation

Call `useOtherStore()` **inside** the action body, never at module top-level:

```ts
async function create(payload) {
  const { data } = await api.post('/leases/', payload)
  leases.value.set(data.id, data)
  loadedAt.value = null
  if (data.auto_created_unit) {
    const propertiesStore = usePropertiesStore()
    await propertiesStore.fetchOne(data.property_id, { force: true })
  }
  return data
}
```

## Migrated entities

| Entity | Store | Phase | Status |
|---|---|---|---|
| Auth | `auth.ts` | (existing) | Stable |
| Lease templates | `template.ts` | (existing) | TipTap workflow, out of scope |
| Lease contract | `contract.ts` | (existing) | GraphQL, out of scope |
| Landlords | `landlords.ts` | 1 | **Migrated** |
| Properties | `properties.ts` | 2 | **Migrated** |
| Leases | `leases.ts` | 3 | **Migrated** |
| Ownerships | `ownerships.ts` | 4a | **Migrated** |
| Persons / Tenants | `persons.ts` | 4b | **Migrated** |
| Viewings | — | 4c | **Skipped** — no admin consumers; agent-app territory |
| Rental mandates | `mandates.ts` | 4d | **Migrated** |

### Per-entity notes

- **Landlords** (`landlords.ts`) — Standard `Map<number, Landlord>`. Bank-account subresource lives inline on the landlord; updates re-fetch the parent via `fetchOne({ force: true })` rather than maintaining a separate keyed map.
- **Properties** (`properties.ts`) — Inline units array stays in the store; photos and documents stay view-local in `PropertyDetailView`. Exposes `updateUnit` / `createUnit` / `deleteUnit` which mutate the unit subresource and force-refresh the parent so derived getters stay correct.
- **Leases** (`leases.ts`) — Adds `fetchActiveFor({ property?, unit? })` for the property/unit detail panels and `fetchForUnit(unitId)` for the previous-leases list. Both upsert into the same `items` map without bumping `loadedAt`. The builder/import endpoint (`POST /leases/import/`) gets its own `importLease()` action with the same upsert + parent-refresh semantics as `create`.
- **Ownerships** (`ownerships.ts`) — Keyed by **property** instead of by id (`byProperty: Map<number, PropertyOwnership[]>`) since ownerships are always queried per property. The dedicated `fetchCurrent(pid)` endpoint and history list both populate the same map. After every mutation, the store force-refreshes both the affected landlord (denormalised `property_count`) and property (denormalised owner info).
- **Persons / Tenants** (`persons.ts`) — Two collections in one store: a keyed `Map<number, Person>` for the rich `/auth/persons/` records (used by lease tenant editing and the e-signing panel), and a plain `tenants[]` array for the lighter `/auth/tenants/` projection consumed by `TenantsView`. `createPerson` / `updatePerson` invalidate `tenantsLoadedAt` so the tenants list refetches on the next visit.
- **Mandates** (`mandates.ts`) — Same `byProperty: Map<number, Mandate[]>` shape as ownerships. The signing-trigger subresource (`POST /mandates/{id}/send-for-signing/`) is exposed as `sendForSigning(id, propertyId)` because it mutates state and needs the parent's mandate list re-fetched.

### Cross-store wiring summary

| Mutation | Triggers refresh of |
|---|---|
| `leases.create` / `leases.importLease` / `leases.update` / `leases.remove` | parent property (units, active-lease info) |
| `ownerships.create` / `ownerships.update` / `ownerships.remove` | linked landlord + parent property |
| `persons.createPerson` / `persons.updatePerson` | tenants projection (`tenantsLoadedAt = null`) |
| `mandates.create` / `mandates.update` / `mandates.remove` / `mandates.sendForSigning` | parent property's mandate list |
| `properties.updateUnit` / `properties.createUnit` / `properties.deleteUnit` | parent property (force `fetchOne`) |

## Known limitations

- **No pagination** — every `fetchAll` queries with a high `page_size` (500). Documented assumption: `< 500` of any entity per agency.
- **No optimistic updates** — every mutation awaits the server.
- **No offline cache** — `loadedAt` is in-memory only.
- **No Pinia unit tests yet** — `admin/vitest.config.ts` is browser-only; a pure-Node setup is its own infra task. Verification is manual via the preview server until that lands.

## Reused infrastructure (do not reinvent)

| What | Where |
|---|---|
| Axios client (auth, refresh, interceptors) | `admin/src/api.ts` |
| Composition-API store template | `admin/src/stores/auth.ts` |
| API error normalisation | `admin/src/utils/api-errors.ts` (`extractApiError`) |
| Toast notifications (component-only) | `admin/src/composables/useToast.ts` |
| Shared formatters (`initials`, `formatDate`) | `admin/src/utils/formatters.ts` |
