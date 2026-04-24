---
id: RNT-QUAL-061
stream: rentals
title: "Guard push signals against duplicate dispatch on non-transitional saves"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Prevent duplicate push notifications being sent when an already-active/paid model instance is saved without a status transition (e.g. unrelated field update with `update_fields=None`).

## Acceptance criteria
- [x] `on_lease_status_change`, `on_mandate_status_change`, and `on_rent_invoice_paid` in `push_signals.py` only dispatch when the status genuinely transitions into the trigger value (not on every save of an already-triggered record)
- [x] Use `pre_save` signal or `__init__` snapshot to capture previous status before save
- [x] Pytest case: save an already-paid rent invoice (no status change) → assert FCM dispatch is NOT called a second time
- [x] Same transition-guard applied to lease and mandate signals

## Files likely touched
- `backend/apps/notifications/push_signals.py` (lines ~65, ~122, ~159)
- `backend/apps/notifications/tests/test_push_signals.py` (new or existing)

## Test plan
**Automated:**
- `cd backend && pytest apps/notifications/tests/test_push_signals.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-push-signal-duplicate-dispatch.md`. Current implementation fires on status match, not transition. Deferred to v1.1 — not blocking launch, but a trust-erosion bug for landlords receiving duplicate rent receipt pushes.

2026-04-24 (implementer) -- Added `_snapshot_status()` helper and four `pre_save` receivers (Lease, RentalMandate, RentInvoice, MaintenanceRequest) that stash `_old_status` on each instance before save. Each `post_save` handler now returns early when `instance.status == _old_status` (no genuine transition). New records (`created=True`) are also skipped. 8 pytest cases in `backend/apps/notifications/tests/test_push_signals.py` -- all 8 pass. Caveat: `QuerySet.update()` bypasses signals so `_old_status` is not set; those paths will still fire once (acceptable -- bulk updates are always intentional transitions in this codebase).
