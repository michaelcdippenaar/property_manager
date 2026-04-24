---
id: RNT-QUAL-061
stream: rentals
title: "Guard push signals against duplicate dispatch on non-transitional saves"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Prevent duplicate push notifications being sent when an already-active/paid model instance is saved without a status transition (e.g. unrelated field update with `update_fields=None`).

## Acceptance criteria
- [ ] `on_lease_status_change`, `on_mandate_status_change`, and `on_rent_invoice_paid` in `push_signals.py` only dispatch when the status genuinely transitions into the trigger value (not on every save of an already-triggered record)
- [ ] Use `pre_save` signal or `__init__` snapshot to capture previous status before save
- [ ] Pytest case: save an already-paid rent invoice (no status change) → assert FCM dispatch is NOT called a second time
- [ ] Same transition-guard applied to lease and mandate signals

## Files likely touched
- `backend/apps/notifications/push_signals.py` (lines ~65, ~122, ~159)
- `backend/apps/notifications/tests/test_push_signals.py` (new or existing)

## Test plan
**Automated:**
- `cd backend && pytest apps/notifications/tests/test_push_signals.py -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-push-signal-duplicate-dispatch.md`. Current implementation fires on status match, not transition. Deferred to v1.1 — not blocking launch, but a trust-erosion bug for landlords receiving duplicate rent receipt pushes.
