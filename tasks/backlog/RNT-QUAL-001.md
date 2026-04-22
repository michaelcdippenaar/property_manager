---
id: RNT-QUAL-001
stream: rentals
title: "Complete Tenant Onboarding UI — models exist, views are thin"
feature: tenant_onboarding
lifecycle_stage: 8
priority: P0
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177379561081"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Finish the UI surface for the Tenant Onboarding flow — the backend models and signals are built, but the admin + tenant screens are stubs. Without this, a lease that is signed today does not visibly transition the tenant into "onboarded" with the checklist they need.

## Acceptance criteria
- [ ] Admin SPA — `TenantOnboardingChecklist.vue` showing: welcome pack sent, deposit received + banked (trust flag deferred v2), first rent scheduled, keys handed over, incoming inspection booked (v2 — mark as "deferred"), emergency contacts captured
- [ ] Each checklist item has a CTA that drives the relevant action (send welcome pack, mark deposit received, schedule first rent)
- [ ] Tenant mobile + web: "Welcome to your new home" screen shown on first login post-lease-signing, walking through the same checklist from tenant side
- [ ] Onboarding progress % visible on agent dashboard and owner dashboard
- [ ] When all items complete → Lease transitions to `active`; unit transitions to `occupied` (already wired via signals)

## Files likely touched
- `admin/src/views/tenants/TenantOnboarding.vue` (new or flesh out)
- `admin/src/components/TenantOnboardingChecklist.vue` (new)
- `web_app/src/views/Welcome.vue` (new)
- `mobile/src/features/onboarding/*`
- `backend/apps/tenants/views.py` (onboarding state endpoints)

## Test plan
**Manual:**
- Sign a lease in staging → agent sees checklist → tenant logs in → sees welcome flow

**Automated:**
- `pytest backend/apps/tenants/tests/test_onboarding.py`

## Handoff notes
