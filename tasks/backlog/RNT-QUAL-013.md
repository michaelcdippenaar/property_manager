---
id: RNT-QUAL-013
stream: rentals
title: "Clean up stale DOCUSEAL_WEBHOOK_SECRET references in esigning docs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214237566166063"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace all `DOCUSEAL_WEBHOOK_SECRET` references in esigning documentation with the current `WEBHOOK_SECRET_ESIGNING` name so operators and developers configure the correct env var.

## Acceptance criteria
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/test_hub/context/modules/esigning.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/esigning/system_documentation/ESIGNING.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] Any remaining DocuSeal branding in esigning system docs is removed or updated to reflect the native signing backend
- [ ] `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` returns zero matches

## Files likely touched
- `backend/apps/test_hub/context/modules/esigning.md`
- `backend/apps/esigning/system_documentation/ESIGNING.md`

## Test plan
**Manual:**
- `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` — zero results
- `grep -r "docuseal" backend/apps/esigning/system_documentation/` — review any remaining references for accuracy

**Automated:**
- N/A (documentation-only change)

## Handoff notes
Promoted from discovery: `2026-04-22-esigning-docs-docuseal-secret-stale.md` (RNT-SEC-005). Low risk but could cause silent webhook auth bypass for any operator following the docs.
