# Properties / Landlords / Tenants — Audit & Remediation

**Date:** 2026-04-09
**Scope:** Backend `apps/properties` + admin Vue views (`properties/`, `tenants/`)
**Excluded:** Multi-tenancy / agent-scoping security (single-tenant deploy for now), lease/e-sign/maintenance/dashboard, tenant-facing apps.

This document captures the findings from a full audit of the properties, landlords, and tenants surfaces in the Klikk admin app, plus the remediation log for what was changed in this pass.

---

## A. Functional Bugs (Confirmed)

### A1. Property creation can orphan from a landlord

**File:** `admin/src/views/properties/PropertiesView.vue:314-341`

`createProperty()` issues two POSTs sequentially:

1. `POST /api/v1/properties/properties/` to create the Property
2. `POST /api/v1/properties/ownerships/` to attach a Landlord via PropertyOwnership

There is no rollback on the second call. If the ownership POST fails (validation error, network drop, missing required `owner_name`), the Property is left in the database with no landlord and the user only sees a generic `toast.error('Failed to create property')`. The dangling property is invisible to the create flow but lives forever in the list.

The bare `catch { … }` block also swallows the actual backend `detail` so the user has no idea *why* it failed.

### A2. `owner_name` is required on `PropertyOwnership` but the frontend may send empty

**Files:**
- `backend/apps/properties/models.py:208` — `owner_name = models.CharField(max_length=200)` — no `blank=True`, no `default`, so the serializer treats it as required.
- `admin/src/views/properties/PropertiesView.vue:324` — `owner_name: ll?.name ?? ''` — sends empty string when the landlord lookup fails.
- `admin/src/views/properties/LandlordDetailView.vue` link-property action does the same fallback.

Result: a 400 from DRF that is hidden by the swallowed catch block in A1. Symptom is "create property doesn't work" with no error feedback.

### A3. `loadLandlords()` swallows errors silently

**File:** `admin/src/views/properties/PropertiesView.vue:299-302`

```ts
async function loadLandlords() {
  const { data } = await api.get('/properties/landlords/')
  landlords.value = (data.results ?? data) || []
}
```

No try/catch. If the call fails (auth, network, 500), the dropdown is empty and there is no toast — the user can't link a landlord and has no idea why.

### A4. `createProperty()` catch hides backend validation detail

**File:** `admin/src/views/properties/PropertiesView.vue:336-338`

```ts
} catch {
  toast.error('Failed to create property')
}
```

DRF returns helpful field errors (e.g. `{address: ['This field is required.']}`). They are silently dropped. The user sees a generic toast and doesn't know what to fix.

### A5. LandlordDetailView silently swallows FICA / registration document loads

**File:** `admin/src/views/properties/LandlordDetailView.vue:1137-1142, 1170-1175`

`loadFicaDocs()` and `loadRegDocs()` both have `catch {}` blocks. If either endpoint fails, the user sees an empty document list with no indication something went wrong.

### A6. FICA and "registration" documents hit the same backend endpoint

**Files:**
- `backend/apps/properties/views.py:245-267` — `LandlordViewSet.fica_documents` returns `landlord.documents.all()` (no filter at all).
- `admin/src/views/properties/LandlordDetailView.vue:1137-1175` — `loadFicaDocs()` AND `loadRegDocs()` both call `GET /properties/landlords/{id}/fica-documents/` and put the response in different refs.

There is **no separation between FICA and registration documents on the backend**. The two refs duplicate each other and the UI shows the same list under two tabs. The right fix is to drop the second loader (frontend-only) until the model grows a `doc_type` field.

### A7. `alert()` and `JSON.stringify()` used for errors

**File:** `admin/src/views/properties/LandlordDetailView.vue` lines `1092, 1124, 1157, 1190, 1250`

When an API call fails, the user gets a JSON dump in a native browser alert dialog. Looks broken, leaks internal field names, breaks the design system, no localisation. There is no `useToast` import in this file at all.

### A8. `window.confirm()` for destructive actions

**Files:**
- `admin/src/views/properties/LandlordDetailView.vue:1057` (delete owner)
- `admin/src/views/properties/LandlordDetailView.vue:1099` (unlink property)
- `admin/src/views/properties/PropertyDetailView.vue:1826` (delete photo)
- `admin/src/views/properties/LandlordDrawer.vue` (delete landlord)

Native confirm dialogs are inconsistent with the rest of the app, can be auto-blocked by the browser, don't theme, and offer no description. The reference implementation in `PropertiesView.vue` already uses a `BaseModal`-driven delete dialog that should be promoted to a shared `ConfirmDialog` component.

### A9. `convert-to-lease` auto-creates a unit silently

**File:** `backend/apps/properties/viewing_views.py:121-139`

```python
if not viewing.property.units.exists():
    default_unit = Unit.objects.create(
        property=viewing.property,
        unit_number="1",
        rent_amount=request.data.get("monthly_rent") or 0,
    )
    unit_id = default_unit.pk
```

Intentional ("mirrors `import_view.py`") so single-family homes can convert without setup. But the response only returns the `Lease`, not the new `Unit`. The frontend has no way to know a unit was just spawned and won't refresh its unit list — the user sees a phantom unit appear next time they reload the property page. Add an `auto_created_unit` flag (or include the new unit) in the response.

### A10. Inconsistent property delete UX

`PropertiesView.vue` uses `BaseModal` (good). `LandlordDetailView.vue` and `PropertyDetailView.vue` use `window.confirm`. Pick one, ship one — see remediation.

### A11. TenantsView is read-only with no path to create a tenant

**File:** `admin/src/views/tenants/TenantsView.vue`

The view only lists. Tenants are `Person` records linked through `Lease.primary_tenant`, so the canonical way to add one is "create a lease". The empty state currently says only "Tenants will appear here once they are added to a property." with no CTA. Users will look for "+ Add Tenant", not find it, and bounce. The empty state needs a "Create a lease" action button that links to the lease builder.

### A12. `propertyTypes` array hardcoded and at risk of drift

**File:** `admin/src/views/properties/PropertiesView.vue:246`

```ts
const propertyTypes = ['apartment', 'house', 'townhouse', 'commercial']
```

Hardcoded in multiple places with no central source. Backend `Property.PROPERTY_TYPE_CHOICES` is the authority. Extract to `src/constants/property.ts` and import everywhere.

---

## B. UX / Accessibility / Design-Standard Drift

### B1. TenantsView table missing `scope="col"`
`admin/src/views/tenants/TenantsView.vue:30-34`. WCAG fix; other tables already have it.

### B2. Status badge colour-only signals
`admin/src/views/properties/PropertyDetailView.vue:33` — colour dot for unit status with no aria-label or text. Add label.

### B3. Hardcoded "Loading…" instead of skeletons
`admin/src/components/PropertyDrawer.vue:73, 176`. Replace with skeleton blocks.

### B4. Inconsistent error display patterns
toast vs alert vs JSON dump vs silent. Standardise on `toast.error(extractApiError(err))`.

### B5. Required-field `*` indicators missing on landlord edit forms
`LandlordDetailView.vue` edit form has no asterisks. Create modal already has them.

### B6. No field-level inline validation
Backend 400s show as toasts only. The CSS classes (`.input-error`, `.input-error-msg`) exist but are unused. Deferred to Phase 4.

### B7. Duplicated utility functions
- `initials()` — TenantsView, PropertyDetailView, PropertyDrawer
- `formatDate() / fmtDate()` — TenantsView, PropertyDetailView, LandlordDetailView

Pull into `src/utils/formatters.ts`.

### B8. Drawer vs full-page detail navigation inconsistency
Landlords use a drawer; properties use a full page. Both are valid but document the rationale (landlord forms are short, property detail has many tabs). No fix needed beyond standardising back-button behaviour where applicable.

### B9. Deprecated `Property.owner` Person FK still in models
Confusing for anyone reading the schema. Out of scope (data migration needed) but flagged for follow-up.

---

## C. False Positives (verified by direct read)

- `PropertyDetailView.vue:1686-1689` **does** guard the route watcher with `if (route.name !== 'property-detail') return`. No fix needed.
- `LandlordDetailView.vue` route watcher is also already guarded. No fix needed.

---

## D. Out of Scope — Security Findings (Deferred, single-tenant for now)

These were found during the audit but the user explicitly excluded multi-tenancy fixes from this pass. Logged here so they aren't lost:

1. **`LandlordViewSet.get_queryset()`** — `backend/apps/properties/views.py:212`
   `Q(ownerships__isnull=True)` makes orphan landlords visible to every agent. Cross-tenant leak the moment a second tenant is provisioned.

2. **`PropertySerializer.agent`** — writable field via `__all__`. An agent could reassign a property to another user.

3. **`viewings/{id}/convert-to-lease`** — `backend/apps/properties/viewing_views.py:155-163`
   `request.data.get("unit")` is not validated against `get_accessible_property_ids`. An attacker who knows a unit_id from another tenant could attach a lease to it.

4. **`PropertyAgentConfigViewSet.by_property`** — `backend/apps/properties/views.py:176-184`
   `get_or_create(property_id=property_id)` runs without scope check. Any authenticated agent can read or write any property's AI config.

5. **`PropertyOwnershipSerializer`** — exposes all denormalised owner fields as writable, including bypassing the Landlord link.

**Recommended sweep:** add scope checks to every `@action`, lock down writable fields with explicit serializer field lists, and remove the `isnull=True` clause once the Landlord ownership backfill is complete.

---

## E. Remediation Log (this pass)

### Phase 0 — Documentation
- [x] Created this audit document.

### Phase 1 — Critical functional bugs
- [ ] `PropertiesView.vue` — atomic create + rollback + extracted error detail (A1, A2, A4)
- [ ] `PropertiesView.vue` — `loadLandlords()` try/catch (A3)
- [ ] `LandlordDetailView.vue` — kill `catch {}`, kill `alert()`, kill `window.confirm()`, drop duplicate doc loader, add `useToast` import (A5, A6, A7, A8)
- [ ] `PropertyDetailView.vue` — replace photo `window.confirm` with `ConfirmDialog`, add status text label (A8, B2)
- [ ] `LandlordDrawer.vue` — replace `window.confirm` with `ConfirmDialog`, add toast error handling (A8)
- [ ] `viewing_views.py` — return `auto_created_unit` flag from `convert-to-lease` (A9)
- [ ] `TenantsView.vue` — empty-state CTA linking to lease creation (A11)

### Phase 2 — UX & accessibility
- [ ] `TenantsView.vue` — `scope="col"` on `<th>` (B1)
- [ ] `PropertyDrawer.vue` — replace "Loading…" with skeleton blocks (B3)
- [ ] `LandlordDetailView.vue` — required-field `*` markers on edit form (B5)
- [ ] Extract `propertyTypes` to `src/constants/property.ts` (A12)

### Phase 3 — Shared utilities
- [ ] `src/utils/api-errors.ts` — `extractApiError(err)` helper
- [ ] `src/utils/formatters.ts` — `initials`, `formatDate`, `fmtMoney`
- [ ] `src/components/ConfirmDialog.vue` — shared destructive-action dialog

---

## F. Verification Checklist (post-implementation)

1. **Landlords flow** — create owner → drawer → edit → save; trigger validation error → toast (no JSON dump); delete owner → styled confirm → cancel/confirm both work.
2. **Properties flow** — create modal → owner dropdown loads or shows error toast; submit with broken landlord → property is rolled back AND error detail is visible; delete property → confirm dialog.
3. **Property detail** — switch units; upload photo; delete photo via styled confirm.
4. **Tenants flow** — empty state shows "Create lease" CTA; tabs all/active/inactive work; search by phone/ID number.
5. **Landlord FICA tab** — upload doc → list refreshes → delete via styled confirm. Zero `alert()` dialogs.
6. **Convert viewing to lease** — schedule on a property with no units → convert → lease created and the auto-created unit either appears in the response or triggers a toast.

Automated:
- `cd backend && pytest apps/test_hub/properties -q`
- `cd admin && npm run build`
