---
id: RNT-SEC-041
stream: rentals
title: "RTBF operator safeguard: surface active-lease and outstanding-payment flags before approve"
feature: "popia_dsar"
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Prevent operators from accidentally approving a Right-to-be-Forgotten DSAR for a user who still has an active lease or outstanding payment obligations, by surfacing retention flags in the review UI before the tombstone can be executed.

## Acceptance criteria
- [ ] `DSARReviewView` response for RTBF requests includes a `retention_flags` object: `{ "has_active_lease": bool, "has_outstanding_payments": bool }`
- [ ] Admin `DSARQueueView.vue` review modal displays a confirmation prompt when either flag is `true` (e.g., "This user has an active lease — are you sure you want to approve erasure?")
- [ ] Operator can still override and approve — judgment is preserved; this is a guardrail not a hard block
- [ ] No change to the tombstone/anonymisation logic itself

## Files likely touched
- `backend/apps/popia/views.py` (`DSARReviewView.post` approve branch)
- `admin/src/views/compliance/DSARQueueView.vue` (review modal)

## Test plan
**Manual:**
- Create a DSAR RTBF request for a user with an active lease → open review modal → confirm warning is shown
- Approve anyway → confirm tombstone runs correctly

**Automated:**
- `cd backend && pytest apps/popia/tests/ -k rtbf -v`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-rtbf-active-lease-precheck.md` (found during RNT-SEC-006). Tombstone/anonymisation logic is correct; this is a UX/process guardrail. RHA/FICA require retention of certain records even post-erasure — an operator approving RTBF for a current tenant without a warning risks disputes or regulatory scrutiny.
