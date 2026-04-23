---
discovered_by: rentals-reviewer
discovered_during: RNT-005
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
In `backend/apps/payments/reconciliation.py`, `ingest_bank_payment` calls `matching_leases.count()` twice in consecutive lines (lines 412 and 419) without caching the result. This issues two DB `COUNT(*)` queries for the same filter within a single atomic transaction.

## Why it matters
Minor inefficiency: every bank payment ingest that fails to match hits the DB twice for the count check. At scale (high-volume bank feed ingestion) this doubles the count queries on the no-match/ambiguous-match hot path. No correctness risk — the `@transaction.atomic` wrapper prevents the result changing between the two calls.

## Where I saw it
- `backend/apps/payments/reconciliation.py:412` — `if matching_leases.count() != 1:`
- `backend/apps/payments/reconciliation.py:419` — `reason = "no_match" if matching_leases.count() == 0 else "ambiguous_match"`

## Suggested acceptance criteria (rough)
- [ ] Cache count result: `lease_count = matching_leases.count()` then use `lease_count` for both the guard and the reason string.

## Why I didn't fix it in the current task
Out of scope for RNT-005 review. Correctness is not affected; this is a minor query efficiency issue only.
