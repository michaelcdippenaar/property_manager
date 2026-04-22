---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-005
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
Two documentation files still reference the old `DOCUSEAL_WEBHOOK_SECRET` setting name after the runtime rename to `WEBHOOK_SECRET_ESIGNING`: `backend/apps/test_hub/context/modules/esigning.md` (lines 51, 52, 132) and `backend/apps/esigning/system_documentation/ESIGNING.md` (lines 622–624, 635).

## Why it matters
An operator or developer following these docs would configure `DOCUSEAL_WEBHOOK_SECRET` and see no verification enforced (because the runtime code reads `WEBHOOK_SECRET_ESIGNING`), silently leaving webhook endpoints unprotected.

## Where I saw it
- `backend/apps/test_hub/context/modules/esigning.md:51-52,132`
- `backend/apps/esigning/system_documentation/ESIGNING.md:622-624,635`

## Suggested acceptance criteria (rough)
- [ ] Replace all `DOCUSEAL_WEBHOOK_SECRET` references in both files with `WEBHOOK_SECRET_ESIGNING`.
- [ ] Remove or update any remaining DocuSeal branding from the esigning system docs where DocuSeal was fully removed.

## Why I didn't fix it in the current task
Documentation files are outside the scope of RNT-SEC-005 which targeted runtime code and tests only. A dedicated cleanup task keeps the diff minimal and reviewable.
