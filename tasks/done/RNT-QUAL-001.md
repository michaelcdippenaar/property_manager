---
id: RNT-QUAL-001
stream: rentals
title: "Complete Tenant Onboarding UI — models exist, views are thin"
feature: tenant_onboarding
lifecycle_stage: 8
priority: P0
effort: M
v1_phase: "1.0"
status: testing
asana_gid: "1214177379561081"
assigned_to: tester
depends_on: []
created: 2026-04-22
updated: 2026-04-22-r6
---

## Goal
Finish the UI surface for the Tenant Onboarding flow — the backend models and signals are built, but the admin + tenant screens are stubs. Without this, a lease that is signed today does not visibly transition the tenant into "onboarded" with the checklist they need.

## Acceptance criteria
- [x] Admin SPA — `TenantOnboardingChecklist.vue` showing: welcome pack sent, deposit received + banked (trust flag deferred v2), first rent scheduled, keys handed over, incoming inspection booked (v2 — mark as "deferred"), emergency contacts captured
- [x] Each checklist item has a CTA that drives the relevant action (send welcome pack, mark deposit received, schedule first rent)
- [x] Tenant mobile + web: "Welcome to your new home" screen shown on first login post-lease-signing, walking through the same checklist from tenant side
- [x] Onboarding progress % visible on agent dashboard and owner dashboard
- [x] When all items complete → Lease transitions to `active`; unit transitions to `occupied` (already wired via signals)

## Files likely touched
- `admin/src/views/tenants/TenantOnboarding.vue` (new or flesh out)
- `admin/src/components/TenantOnboardingChecklist.vue` (new)
- `web_app/src/views/Welcome.vue` (new)
- `backend/apps/tenants/views.py` (onboarding state endpoints)

> v1.0 scope note: Flutter tenant mobile app deferred to v2. Tenant onboarding UI is web-only (web_app/) for v1.0.

## Test plan
**Manual:**
- Sign a lease in staging → agent sees checklist → tenant logs in → sees welcome flow

**Automated:**
- `pytest backend/apps/tenants/tests/test_onboarding.py`

## Handoff notes

### 2026-04-22 — implementer

**What was built (greenfield — no prior model existed):**

The task description says "backend models are built" but no `TenantOnboarding` model existed anywhere. This was a full greenfield implementation.

**Backend (`backend/apps/tenant/`):**
- Added `TenantOnboarding` model to `models.py` — tracks 5 v1 checklist items (welcome pack, deposit, first rent, keys, emergency contacts) plus 2 v2-deferred items (incoming inspection, trust deposit banking). Includes computed `progress` (0–100) and `is_complete` properties based on v1 items only.
- Migration `0002_tenant_onboarding.py` created (unapplied on local DB).
- Added `TenantOnboardingSerializer`, `TenantOnboardingCreateSerializer` to `serializers.py`. Serializer auto-stamps `*_at` timestamps on False→True transitions and sets `completed_at` when all v1 items are ticked.
- Added `TenantOnboardingViewSet` to `views.py` — agents/admins have full CRUD; tenants get read-only filtered to their own records.
- Registered `onboarding` router in `urls.py` → `/api/v1/tenant/onboarding/`.
- Added `create_onboarding_on_active` signal to `leases/signals.py` — auto-creates `TenantOnboarding` when a `Lease` transitions to `active`.
- Updated `admin.py` with `TenantOnboardingAdmin`.
- 8 unit tests in `backend/apps/test_hub/tenant/unit/test_onboarding.py` — all green.

**Admin SPA (`admin/src/`):**
- `components/OnboardingItem.vue` — single checklist row (tick/CTA/timestamp).
- `components/TenantOnboardingChecklist.vue` — full checklist card with progress bar, deposit modal (captures actual amount), v2-deferred section.
- `views/tenants/TenantOnboardingView.vue` — view wrapper that loads onboarding by lease, with manual creation fallback.
- `views/tenants/TenantDetailView.vue` — added "Onboarding" tab (4th tab, between Leases and Documents).
- `views/dashboard/DashboardView.vue` — added onboarding-in-progress widget (shows up to 5 incomplete onboardings with progress bars + links to tenant detail).
- `views/owner/OwnerDashboard.vue` — same onboarding widget for owner portal.

**Tenant web app (`tenant/src/`):**
- `views/home/WelcomeView.vue` — "Welcome to your new home" screen with per-item checklist, progress bar, and CTA to dashboard.
- `components/TenantOnboardingItem.vue` — mobile-friendly list row for each checklist step.
- `router/index.ts` — added `/welcome` route; added router guard on `home` to redirect to welcome once per session (uses `sessionStorage.klikk_welcome_checked` / `klikk_welcome_seen`).

**Caveats for reviewer:**
- The redirect guard uses `sessionStorage` (per-tab, not per-user). If a tenant dismisses the welcome screen in one tab and opens a new tab, they'll be redirected again. A more durable approach would be a `seen_welcome` flag on the backend user model, but that's out-of-scope for this task. Consider a discovery if this needs hardening.
- The task says "Lease transitions to `active`" as a criteria for completing onboarding — this is already wired via the existing lease signals (`sync_unit_status`). The `TenantOnboarding.is_complete` flag is computed but does NOT itself trigger a lease status transition (the lease is already active by the time onboarding is created). This is the correct behavior per the task description.
- The `backend/apps/tenants/tests/test_onboarding.py` path in the task has a typo — the app is `tenant` (no `s`). Tests are at `backend/apps/test_hub/tenant/unit/test_onboarding.py`.

### 2026-04-22 — reviewer (changes requested)

Two fixes required before this can be approved. Fix 1 is a security issue (blocking). Fix 2 is a minor cleanup.

**1. SECURITY — Owner role gets unscoped access to all onboarding records (IDOR)**

`backend/apps/tenant/views.py` — `TenantOnboardingViewSet.get_queryset()` (lines 107–126).

The `get_queryset` branch reads:

```python
if user.role == "tenant":
    qs = qs.filter(lease__primary_tenant__linked_user=user)
else:
    # Agents/admins can filter by lease or property
    ...
```

The `else` branch catches every non-tenant role — including `owner`. An owner-portal user who calls `GET /api/v1/tenant/onboarding/` with no query params receives every onboarding record in the database. They can also `GET /api/v1/tenant/onboarding/<id>/` for any lease they don't own.

Owner-portal `OwnerDashboard.vue` (`admin/src/views/owner/OwnerDashboard.vue`) calls exactly this endpoint without a property filter:

```js
api.get('/tenant/onboarding/?page_size=10')
```

Fix: add an owner scope branch in `get_queryset` using the same `PropertyOwnership` chain used in `HasPropertyAccess` and `IsOwnerOfProperty`. Something like:

```python
if user.role == User.Role.OWNER:
    from apps.properties.models import PropertyOwnership, Landlord
    person = getattr(user, 'person_profile', None)
    if not person:
        return qs.none()
    landlord_ids = Landlord.objects.filter(person=person).values_list('pk', flat=True)
    owned_property_ids = PropertyOwnership.objects.filter(
        landlord_id__in=landlord_ids, is_current=True
    ).values_list('property_id', flat=True)
    qs = qs.filter(lease__unit__property_id__in=owned_property_ids)
```

The same fix makes the `OwnerDashboard.vue` API call safe without changing the frontend, because the backend will now naturally return only that owner's records.

**2. MINOR — Unused import `IsTenant` in `backend/apps/tenant/views.py` line 6**

`IsTenant` is imported but never referenced — `get_permissions()` uses `IsAuthenticated()` directly for the read branch. Remove the import to keep the file clean and avoid misleading future readers about the intended permission design.

**Discovery filed:** `tasks/discoveries/2026-04-22-tenant-onboarding-welcome-redirect-durability.md` — covers the `sessionStorage` welcome-redirect issue flagged by the implementer. No action needed in this task; PM to promote if desired.

**Everything else is solid:** model design, serializer auto-timestamping, signal with lazy import and `get_or_create` guard, checklist component + deposit modal, tenant `WelcomeView`, dashboard widgets, and 8 unit tests all look good and match project conventions.

### 2026-04-22 — implementer (reviewer fixes)

**Fix 1 — SECURITY (Owner IDOR in `TenantOnboardingViewSet.get_queryset`):**
Added an `elif user.role == User.Role.OWNER:` branch before the `else` agent/admin branch. The new branch scopes the queryset through the `PropertyOwnership` chain (same pattern as `HasPropertyAccess` in `apps/accounts/permissions.py`): walks `user.person_profile` → `Landlord` → `PropertyOwnership` (is_current=True) → filters onboarding records to `lease__unit__property_id__in=owned_property_ids`. If `person_profile` is absent, returns `qs.none()`. Also changed the tenant role check from the bare string `"tenant"` to the `User.Role.TENANT` constant for consistency.

**Fix 2 — Unused import `IsTenant`:**
Removed `IsTenant` from the import line on line 6. Replaced with `from apps.accounts.models import User` (needed for `User.Role` constants in the queryset fix above).

Smoke-check: `from apps.tenant.views import TenantOnboardingViewSet` imports cleanly with `DJANGO_SETTINGS_MODULE=config.settings.local`.

### 2026-04-22 — reviewer (r2 — review passed)

**Approved. Both requested fixes are correctly implemented.**

1. **SECURITY fix verified** — `backend/apps/tenant/views.py` lines 119–130: the `elif user.role == User.Role.OWNER:` branch is present, correctly positioned before the `else` agent/admin branch, and the `PropertyOwnership` chain matches the established pattern in `apps/accounts/permissions.py` (`HasPropertyAccess` lines 140–143, `IsOwnerOfProperty` lines 196–202) exactly: `person_profile` → `Landlord.objects.filter(person=person)` → `PropertyOwnership.objects.filter(landlord_id__in=..., is_current=True)` → `qs.filter(lease__unit__property_id__in=...)`. The `person_profile` absent guard (`return qs.none()`) is present.

2. **Unused import removed** — `IsTenant` is gone; replaced with `from apps.accounts.models import User` (required for `User.Role` constants). `IsAgentOrAdmin` retained. Import block is clean.

3. **Tenant role check** — upgraded from bare string `"tenant"` to `User.Role.TENANT` constant, consistent with the owner constant added in the same fix.

No regressions identified. `OwnerDashboard.vue` API call (`/tenant/onboarding/?page_size=10`) is now safe without any frontend change — the backend scopes the response naturally.

### 2026-04-22 — tester (test run)

**Automated tests** (`backend/apps/test_hub/tenant/unit/test_onboarding.py`):
Note: the test plan path `backend/apps/tenants/tests/test_onboarding.py` is a typo (app name is `tenant` not `tenants`); ran the actual file per the implementer's caveat.
- PASS: `TestTenantOnboardingProgress::test_zero_progress_when_all_false`
- PASS: `TestTenantOnboardingProgress::test_full_progress_when_all_v1_true`
- PASS: `TestTenantOnboardingProgress::test_partial_progress`
- PASS: `TestTenantOnboardingProgress::test_v2_items_do_not_affect_progress`
- PASS: `TestTenantOnboardingProgress::test_is_complete_false_when_partial`
- PASS: `TestTenantOnboardingProgress::test_is_complete_true_when_all_v1_ticked`
- PASS: `TestTenantOnboardingProgress::test_is_complete_false_when_v2_only`
- PASS: `TestTenantOnboardingStr::test_str_contains_lease_repr`
All 8 passed.

Pre-condition: also ran `manage.py migrate` — `tenant.0002_tenant_onboarding` and all silk migrations were unapplied; applied them before API testing.

**Manual UI (API layer — FAIL):**
`GET /api/v1/tenant/onboarding/` with an empty queryset returns `{"count":0,"results":[]}` (OK). As soon as any record exists and the serializer tries to serialize an instance, the server 500s with:

```
AssertionError: It is redundant to specify `source='lease_id'` on field 'IntegerField' in
serializer 'TenantOnboardingSerializer', because it is the same as the field name.
Remove the `source` keyword argument.
```

Root cause: `backend/apps/tenant/serializers.py` line 91:
```python
lease_id = serializers.IntegerField(source="lease_id", read_only=True)
```
DRF raises an `AssertionError` when `fields` is accessed on any instance of `TenantOnboardingSerializer`. This crashes every GET that returns records, and also any POST that goes through this serializer. The 8 unit tests did not catch it because they only test model-level properties, not the serializer.

**Impact:** The admin SPA's `TenantOnboardingView.vue`, `TenantOnboardingChecklist.vue`, dashboard widgets, and owner dashboard widget are all non-functional as soon as any onboarding record is created. The entire manual UI flow (agent sees checklist) is blocked.

**Fix required:** In `backend/apps/tenant/serializers.py` line 91, change:
```python
lease_id = serializers.IntegerField(source="lease_id", read_only=True)
```
to:
```python
lease_id = serializers.IntegerField(read_only=True)
```

**Verdict: BLOCKED — serializer bug causes 500 on all onboarding API reads with data.**

### 2026-04-22 — implementer (unblock fix)

One-line fix in `backend/apps/tenant/serializers.py` line 91: removed redundant `source="lease_id"` from `lease_id = serializers.IntegerField(...)`. DRF raises `AssertionError` at field access time when `source` matches the field name; dropping it resolves the 500. All 8 unit tests still pass (`pytest backend/apps/test_hub/tenant/unit/test_onboarding.py`).

### 2026-04-22 — reviewer (r3 — review passed)

**Approved. Unblock fix is correct and complete.**

Reviewed commit `02fb4cb` (blocked → review).

Single-line change in `backend/apps/tenant/serializers.py` line 91: `source="lease_id"` removed from `TenantOnboardingSerializer.lease_id`. DRF raises `AssertionError` at field-access time when `source` equals the field name; removing it resolves the 500 on every serializer read with data — exactly the bug the tester identified.

No regressions introduced: the field is still declared `read_only=True` and is listed in both `fields` and `read_only_fields` in `Meta`. All other serializer logic (timestamp stamping in `update()`, `_TIMESTAMP_MAP`, `get_*` methods) is unchanged.

All prior review work stands: Owner IDOR fix (r2) is present at `views.py` lines 119–130; unused `IsTenant` import removed; `User.Role.TENANT` constant in use. Import block is clean.

Scope confirmed against `content/product/features.yaml` `tenant_onboarding` feature — implementation matches v1.0 scope.
