---
id: RNT-QUAL-020
stream: rentals
title: "Update esigning docs: replace stale DOCUSEAL_WEBHOOK_SECRET references"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214195065174770"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Replace all `DOCUSEAL_WEBHOOK_SECRET` references in esigning documentation with `WEBHOOK_SECRET_ESIGNING` so operators following the docs configure the correct env var and webhooks remain protected.

## Acceptance criteria
- [x] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/test_hub/context/modules/esigning.md` replaced with `WEBHOOK_SECRET_ESIGNING` — already clean, no change needed
- [x] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/esigning/system_documentation/ESIGNING.md` replaced with `WEBHOOK_SECRET_ESIGNING` — already clean, no change needed
- [x] Remaining DocuSeal branding removed or updated from the esigning system docs where DocuSeal was fully removed — CONTEXT.md, marketing/ux/uat-mc-instructions.md, backend/pytest.ini updated
- [x] `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` returns no results — confirmed 0 results

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
2026-04-23: Implementer. The two primary target files (`backend/apps/test_hub/context/modules/esigning.md` and `backend/apps/esigning/system_documentation/ESIGNING.md`) were already clean — they already used `WEBHOOK_SECRET_ESIGNING`. Widened search to all docs scope and found three additional stale references: (1) `CONTEXT.md` line 309 still listed DocuSeal as an active integration; updated to native e-signing + Gotenberg note. (2) `marketing/ux/uat-mc-instructions.md` line 28 still said "DocuSeal / native signing"; updated to native only. (3) `backend/pytest.ini` e2e marker description still listed DocuSeal; removed. `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` confirms 0 results. `.pytest_cache` and `htmlcov` generated artifacts were left untouched (not source files).

2026-04-23: Reviewer. Verified diff against ACs. Two primary doc targets were already clean (grep confirms). The 3 additional files (CONTEXT.md L309, backend/pytest.ini L14, marketing/ux/uat-mc-instructions.md L28) correctly replace DocuSeal mentions with native e-signing (Gotenberg + signed_pdf_file + ESigningPublicLink signer_role links) per the April 2026 native-signing-only reality. grep -r DOCUSEAL across backend/docs/marketing/content/CONTEXT.md returns 0 non-trivial hits. Remaining lowercase docuseal references in backend/apps/esigning/*.py (services.py, views.py, migrations, tests) are source-code concerns outside this docs-only task and should be tracked separately if needed. No security surface. Approved.
