---
id: RNT-QUAL-020
stream: rentals
title: "Update esigning docs: replace stale DOCUSEAL_WEBHOOK_SECRET references"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214195065174770"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace all `DOCUSEAL_WEBHOOK_SECRET` references in esigning documentation with `WEBHOOK_SECRET_ESIGNING` so operators following the docs configure the correct env var and webhooks remain protected.

## Acceptance criteria
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/test_hub/context/modules/esigning.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/esigning/system_documentation/ESIGNING.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] Remaining DocuSeal branding removed or updated from the esigning system docs where DocuSeal was fully removed
- [ ] `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` returns no results

## Files likely touched
- `backend/apps/test_hub/context/modules/esigning.md` (lines 51, 52, 132)
- `backend/apps/esigning/system_documentation/ESIGNING.md` (lines 622-624, 635)

## Test plan
**Manual:**
- `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` — confirm 0 results
- `grep -r "docuseal" backend/apps/esigning/system_documentation/` (case-insensitive) — review any remaining references

**Automated:**
- n/a (docs-only change)

## Handoff notes
2026-04-22: Promoted from discovery `2026-04-22-esigning-docs-docuseal-secret-stale.md` (found during RNT-SEC-005 review).
