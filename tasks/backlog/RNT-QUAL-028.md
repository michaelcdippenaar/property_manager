---
id: RNT-QUAL-028
stream: rentals
title: "Fix stale DOCUSEAL_WEBHOOK_SECRET references in esigning docs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214218083690104"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace all `DOCUSEAL_WEBHOOK_SECRET` references in esigning documentation with `WEBHOOK_SECRET_ESIGNING` so operators following the docs do not silently misconfigure webhook verification.

## Acceptance criteria
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/test_hub/context/modules/esigning.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/esigning/system_documentation/ESIGNING.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] Remaining DocuSeal branding removed or updated in esigning system docs where DocuSeal was fully removed
- [ ] `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` returns zero matches

## Files likely touched
- `backend/apps/test_hub/context/modules/esigning.md`
- `backend/apps/esigning/system_documentation/ESIGNING.md`

## Test plan
**Manual:**
- `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` — expect zero output

## Handoff notes
Promoted from discovery `2026-04-22-esigning-docs-docuseal-secret-stale.md` (found during RNT-SEC-005).
