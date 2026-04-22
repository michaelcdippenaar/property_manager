---
id: RNT-QUAL-001
stream: rentals
title: "Complete Tenant Onboarding UI — models exist, views are thin"
feature: tenant_onboarding
lifecycle_stage: 8
priority: P0
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177379561081"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
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
