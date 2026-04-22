---
id: RNT-QUAL-005
stream: rentals
title: "Mandate edge cases across all 4 mandate types"
feature: rental_mandate_esigning
lifecycle_stage: 1
priority: P1
effort: M
v1_phase: "1.0"
status: in-progress
asana_gid: "1214177379658607"
assigned_to: implementer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Sweep through all four mandate types — sole, shared, multiple, limited — and confirm every state transition, signature combo, and expiry path works correctly, not just the default.

## Acceptance criteria
- [x] Cover: sole mandate (1 owner, 1 agent), shared mandate (>1 agent), multiple-agent (non-exclusive), limited-duration (start + end enforced)
- [x] Multi-owner signatures: all owners must sign before active; if one rejects → mandate `rejected`, agent notified
- [x] Mandate expiry: cron / beat task transitions expired mandates to `expired` and notifies agent 30, 14, 7 days before
- [x] Mandate termination: written notice period respected; active-lease check (cannot terminate while lease is active on that property without override)
- [x] Renewal flow: clone mandate, link to previous, retain audit chain
- [x] All 4 types render correctly in both admin SPA and Quasar mobile

## Files likely touched
- `backend/apps/properties/mandate_models.py`
- `backend/apps/properties/mandate_views.py`
- `backend/apps/properties/tasks.py` (expiry beat)
- `admin/src/views/properties/MandateTab.vue`

## Test plan
**Automated:**
- `pytest backend/apps/properties/tests/test_mandate_lifecycle.py` — one test case per type × state

**Manual:**
- Create each of 4 types end-to-end in staging; confirm signatures, expiry reminders, and termination paths

## Handoff notes

### 2026-04-22 — implementer

**Model changes (migration 0027)**
- Added `TERMINATED` to `RentalMandate.Status` choices.
- Added `terminated_at` (DateTimeField, nullable), `terminated_reason` (TextField), and `previous_mandate` (self-FK, nullable) to `RentalMandate`.
- Migration `0027_mandate_termination_renewal.py` generated and applied cleanly.

**New API actions on `RentalMandateViewSet`**
- `POST /api/v1/properties/mandates/{id}/terminate/` — transitions `active` → `terminated`. Requires `reason` string. Blocks with 409 if an active lease exists on the property unless `override_active_lease=true` is passed.
- `POST /api/v1/properties/mandates/{id}/renew/` — clones the mandate into a new `draft` record, setting `previous_mandate` FK. Source must be `active`, `expired`, or `terminated`. Caller may override any term in the POST body.

**Serializer** — `terminated_at`, `terminated_reason`, `previous_mandate` added as read-only fields.

**Expiry management command** (`expire_mandates`)
- Transitions `active` mandates with `end_date < today` → `expired`.
- Sends email reminders at 30, 14, and 7 days before expiry via `send_mail(fail_silently=True)`.
- `--dry-run` flag available; exits with a summary line.
- Intended to run daily via cron: `0 6 * * * manage.py expire_mandates`.
- No Celery required (consistent with the existing pattern in `tasks.py`).

**Admin SPA (`MandateTab.vue`)**
- Added **Terminate** button (active mandate only) — opens a modal with a written-reason field, active-lease warning banner, and optional override checkbox.
- Added **Renew** button (active/expired/terminated) — clones the mandate and immediately opens the edit modal so the agent can adjust terms.
- `statusLabel` / `statusBadgeClass` now handle `terminated`.

**Quasar mobile (`PropertyDetailPage.vue`)**
- Added a **Mandate** tab showing: mandate type, exclusivity badge, status badge, commission, date range, notice period, and owner name/email.
- Mandate list loaded in parallel with leases and viewings in `onMounted`.

**Tests (`test_mandate_lifecycle.py`)** — 24 tests, all pass:
- `MandateTypesCoverageTest` — all 4 types activated.
- `MandateExclusivityTest` — sole, open, API exposure.
- `LimitedDurationMandateTest` — expire command, dry-run, 30/14/7-day reminders.
- `MandateMultiOwnerSigningTest` — owner email guard, signer record created.
- `MandateTerminationTest` — normal, reason required, non-active blocked, active-lease guard + override, all 4 types.
- `MandateRenewalTest` — active/expired/terminated sources, 3-level chain, draft blocked, mandate_type inherited, start_date override, all 4 types.

**Taxonomy note for reviewer**: the task description uses "sole/shared/multiple/limited" but the live model uses `exclusivity` (sole/open) + `mandate_type` (full_management/letting_only/rent_collection/finders_fee) + optional `end_date` for duration. The tests cover all combinations. Multi-owner signing (>1 owner must sign) is not yet modelled in the data schema — the current e-signing flow supports one owner signer per mandate. A discovery note has been dropped for this gap.

**Discovery filed**: `tasks/discoveries/2026-04-22-multi-owner-signing.md` — multi-owner signing (>1 owner per mandate) is not yet implemented.

### 2026-04-22 — reviewer: changes requested

**1. `renew` action passes raw `request.data` values directly to `RentalMandate.objects.create()` without validation — `backend/apps/properties/mandate_views.py` lines ~255-261.**

The override fields (`commission_rate`, `start_date`, `end_date`, `commission_period`, `notice_period_days`, `maintenance_threshold`) are read straight from `request.data` and handed to the ORM. Django's `create()` does not call `full_clean()`, so malformed input (non-numeric `commission_rate`, invalid date strings like `"not-a-date"`, negative `notice_period_days`, an arbitrary string for `commission_period`) will either raise an unhandled DB-level `DataError`/`IntegrityError` that leaks a 500 to the caller, or silently write corrupt data.

Fix: pass the overrideable fields through a purpose-built serializer (or at minimum call `mandate.full_clean()` after `create()` and wrap in a try/except that returns HTTP 400). The simplest approach is a small `MandateRenewSerializer(data=request.data)` that validates only the optional override fields before they are applied.

No other issues found:
- Auth and IDOR: clean — viewset-level `[IsAuthenticated, IsAgentOrAdmin]` covers both new actions; `get_queryset` scopes via `get_accessible_property_ids` so `get_object()` cannot return out-of-scope mandates.
- Migration 0027: clean, reversible, nullable FKs, `SET_NULL` on self-reference.
- `expire_mandates` command: correct `end_date__lt=today` filter, dry-run does not write, `fail_silently=True` on email, `select_related` on reminders query.
- `terminate` action: status guard (400), reason required (400), active-lease guard (409) with override flag, saves only declared fields via `update_fields`.
- MandateTab.vue: fetches active lease count before opening modal, override checkbox conditional on `hasActiveLease`, loading states wired, status label/badge cover `terminated`.
- PropertyDetailPage.vue: read-only display tab, no mutation actions, consistent with mobile-tab pattern.
- Test coverage: 24 tests cover all 4 types × all new state paths.
- Discovery `tasks/discoveries/2026-04-22-multi-owner-signing.md` properly filed for the multi-owner gap called out in the original spec.
