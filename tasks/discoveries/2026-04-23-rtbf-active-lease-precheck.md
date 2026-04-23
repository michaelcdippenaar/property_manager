---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-006
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found

`DSARReviewView` approve path for RTBF does not surface any active-lease or
legal-hold warnings to the operator before executing the tombstone.  An
operator can approve an RTBF and erase a user who still has an `active` lease
or outstanding payment obligations — the deletion service runs atomically but
the operator has no in-band prompt about retention obligations.

## Why it matters

Under RHA and FICA, certain records must be retained even after erasure.  The
deletion service does anonymise correctly (does not hard-delete leases/payments),
but the operator reviewing the DSAR queue has no visibility of whether the
user has active obligations.  A well-meaning operator could approve an RTBF
for a current tenant without realising the tenant's lease hasn't ended.  This
is a UX/process risk rather than a data-loss risk, but it could lead to
disputes or regulatory scrutiny.

## Where I saw it

- `backend/apps/popia/views.py` — `DSARReviewView.post` approve branch
- `admin/src/views/compliance/DSARQueueView.vue` — review modal (no active-lease warning)

## Suggested acceptance criteria (rough)

- [ ] `DSARReviewView` response for RTBF requests includes a `retention_flags` object:
      `{ "has_active_lease": bool, "has_outstanding_payments": bool }`
- [ ] Admin queue review modal surfaces these flags with a confirmation prompt
      ("This user has an active lease — are you sure?") before the operator
      can click Approve RTBF.
- [ ] No change to the tombstone logic itself — operator judgment is preserved.

## Why I didn't fix it in the current task

Reviewer item 5 (should-fix, not must-fix).  Requires touching the admin Vue
component which is out of scope for the current blocker pass.  The deletion
service itself is correct; this is a UX improvement.
