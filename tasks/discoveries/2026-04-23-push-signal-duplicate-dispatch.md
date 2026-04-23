---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-007
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
The `post_save` push receivers in `backend/apps/notifications/push_signals.py` fire whenever the model's current status matches the trigger value (e.g. `status == "active"` for leases, `status in ("paid", "overpaid")` for rent invoices) — they do not detect the transition into that state. When `update_fields` is `None` (full `.save()`), any subsequent save of an already-paid / already-active record will re-dispatch the push notification.

## Why it matters
Tenants and agents will receive duplicate "Lease signed", "Rent received", "Mandate signed" pushes any time an unrelated field on the same model is saved without an explicit `update_fields` list. For landlord-facing rent receipts this is a trust-erosion bug.

## Where I saw it
- `backend/apps/notifications/push_signals.py:65` — `on_lease_status_change`
- `backend/apps/notifications/push_signals.py:122` — `on_mandate_status_change`
- `backend/apps/notifications/push_signals.py:159` — `on_rent_invoice_paid`

## Suggested acceptance criteria (rough)
- [ ] Track previous status via `pre_save` signal or `__init__` snapshot so dispatch only fires on genuine transition
- [ ] Add a `pytest` case that saves an already-paid invoice and asserts no second push is dispatched
- [ ] Apply the same pattern to lease and mandate signals

## Why I didn't fix it in the current task
The current implementation satisfies RNT-QUAL-007's acceptance criteria (events fire on the state change). This is a hardening follow-up that requires pre_save wiring plus tests, and should not block the v1 push rollout.
