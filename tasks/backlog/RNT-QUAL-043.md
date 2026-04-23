---
id: RNT-QUAL-043
stream: rentals
title: "Double count() query in ingest_bank_payment reconciliation hot path"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214230978588997"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Cache the `matching_leases.count()` result in `ingest_bank_payment` to eliminate a redundant DB `COUNT(*)` query on every no-match / ambiguous-match bank payment.

## Acceptance criteria
- [ ] `ingest_bank_payment` assigns `lease_count = matching_leases.count()` once
- [ ] Both the guard condition (`if lease_count != 1`) and the reason string (`"no_match" if lease_count == 0 else "ambiguous_match"`) reference `lease_count`, not fresh `.count()` calls
- [ ] All existing reconciliation unit tests pass unchanged
- [ ] No behaviour change — correctness is unaffected; this is a query-reduction only

## Files likely touched
- `backend/apps/payments/reconciliation.py` — lines ~412 and ~419

## Test plan
**Manual:**
- N/A (no observable behaviour change)

**Automated:**
- `cd backend && pytest apps/payments/tests/ -v`
- Optionally add a Django test that asserts `django.test.utils.CaptureQueriesContext` shows exactly 1 COUNT query on the no-match path

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-reconciliation-double-count-query.md`. Discovered by rentals-reviewer during RNT-005 review. Trivial one-line fix; bundle with the next reconciliation maintenance pass if preferred.
