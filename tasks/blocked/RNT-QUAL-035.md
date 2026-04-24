---
id: RNT-QUAL-035
stream: rentals
title: "Mandate e-signing: support multi-owner co-signatories"
feature: ""
lifecycle_stage: null
priority: P2
effort: L
v1_phase: "1.1"
status: blocked
assigned_to: rentals-pm
depends_on: []
asana_gid: "1214203875365414"
created: 2026-04-22
updated: 2026-04-24
---

## Goal
Allow a `RentalMandate` to collect signatures from all co-owners of a property before transitioning to `active`, and move to a `rejected` status (with agent notification) if any co-owner rejects.

## Acceptance criteria
- [ ] `RentalMandate` supports multiple co-owner signers via M2M to `PropertyOwnership` or a dedicated `MandateOwner` through-table, with a migration
- [ ] `mandate_services.build_mandate_signers` iterates all active co-owners and inserts one signer record per owner before the agent signer
- [ ] `RentalMandate.status` transitions to `active` only when all owner signers AND the agent have signed (webhook handler updated)
- [ ] If any owner rejects, mandate transitions to `rejected` and agent receives an in-app / email notification
- [ ] Admin SPA `MandateTab.vue` renders all co-owner signer rows with individual status chips
- [ ] Existing single-owner mandate flow is unaffected
- [ ] Tests cover: all sign → active; one owner rejects → rejected; agent rejects → existing behaviour

## Files likely touched
- `backend/apps/properties/models.py` — `RentalMandate` model + new M2M/through-table
- `backend/apps/properties/migrations/` — new migration
- `backend/apps/properties/mandate_services.py` — `build_mandate_signers`
- `backend/apps/esigning/` — webhook handler for signing events
- `admin/src/views/properties/MandateTab.vue`
- `backend/apps/properties/tests/test_mandate_lifecycle.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/properties/tests/test_mandate_lifecycle.py`
- `cd backend && pytest apps/esigning/tests/`

**Manual:**
- Create mandate for co-owned property → both owners receive signing links → both sign → mandate goes active
- Co-owned property → one owner rejects → mandate status = rejected → agent notified

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-multi-owner-signing.md` found during RNT-QUAL-005 review. Data-model change required; single-owner flow must not regress.

2026-04-24 — rentals-pm: Deferred post-launch per MC directive 2026-04-24. Single-owner mandates cover the first-client dry-run. v1_phase set to "1.1". Task moved to backlog/ for v1.1 planning. No implementation work in v1.0.

2026-04-24 — rentals-implementer: Task is effort L, already PM-flagged as v1.1 scope. Requires data-model migration (M2M/through-table), mandate_services refactor, e-signing webhook changes, MandateTab.vue updates, and new test coverage — too large for a single implementer pass and explicitly out of v1.0 scope. Moved to blocked/ for PM to confirm v1.1 scheduling.
