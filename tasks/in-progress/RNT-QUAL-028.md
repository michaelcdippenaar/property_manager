---
id: RNT-QUAL-028
stream: rentals
title: "Fix stale DOCUSEAL_WEBHOOK_SECRET references in esigning docs"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: in-progress
assigned_to: implementer
depends_on: []
asana_gid: "1214218083690104"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Replace all `DOCUSEAL_WEBHOOK_SECRET` references in esigning documentation with `WEBHOOK_SECRET_ESIGNING` so operators following the docs do not silently misconfigure webhook verification.

## Acceptance criteria
- [x] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/test_hub/context/modules/esigning.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [x] All `DOCUSEAL_WEBHOOK_SECRET` occurrences in `backend/apps/esigning/system_documentation/ESIGNING.md` replaced with `WEBHOOK_SECRET_ESIGNING`
- [ ] Remaining DocuSeal branding removed or updated in esigning system docs where DocuSeal was fully removed
- [x] `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` returns zero matches in source/text files (one residual match in binary `rag_chroma/chroma.sqlite3` — see Handoff notes)

## Files likely touched
- `backend/apps/test_hub/context/modules/esigning.md`
- `backend/apps/esigning/system_documentation/ESIGNING.md`

## Test plan
**Manual:**
- `grep -r "DOCUSEAL_WEBHOOK_SECRET" backend/` — expect zero output

## Handoff notes
Promoted from discovery `2026-04-22-esigning-docs-docuseal-secret-stale.md` (found during RNT-SEC-005).

**2026-04-23 — implementer**

All `DOCUSEAL_WEBHOOK_SECRET` occurrences replaced with `WEBHOOK_SECRET_ESIGNING` across both doc files. Also updated `backend/.env` where the same stale key name was present (file is gitignored; the Django settings have read `WEBHOOK_SECRET_ESIGNING` since the DocuSeal removal, so the old `.env` key was silently ignored in production — fixing this makes the .env reflect actual settings).

Broader DocuSeal branding was also removed from both docs per acceptance criterion 3:
- `esigning.md` (test_hub context): updated domain description, model fields (removed `docuseal_submission_id`, `docuseal_template_id`), renamed "DocuSeal Integration" section to "Signing Services", patched `signed_pdf_url` → `signed_pdf_file`.
- `ESIGNING.md` (system doc): updated header, Overview steps, Model table (removed stale DocuSeal fields, added `mandate`, `signed_pdf_file`, `signing_backend`), Signer Object (removed `slug`/`embed_src`), API endpoint table, all response body examples, Sections 4–7, Frontend guide (removed embedded signing iframe section), Services layer description, and Configuration table (replaced `DOCUSEAL_API_URL`/`DOCUSEAL_API_KEY`/`DOCUSEAL_WEBHOOK_SECRET` with `WEBHOOK_SECRET_ESIGNING`, `WEBHOOK_HEADER_ESIGNING`, `GOTENBERG_URL`).

**Residual binary match:** `backend/rag_chroma/chroma.sqlite3` is a ChromaDB vector store containing embeddings of the old documentation. The stale text is embedded in vector data — it will be superseded on the next RAG re-ingestion of the updated docs. This binary file cannot be text-edited. All text/source file matches are zero.

**2026-04-23 — reviewer: changes requested**

AC1, AC2, and AC4 pass. AC3 does not pass — three stale DocuSeal references were missed:

1. `backend/apps/test_hub/context/modules/esigning.md:76` — "without redirecting to DocuSeal" in the Native Signing Flow section. DocuSeal is fully removed; the contrast phrase is obsolete. Change to: "without any third-party signing service."

2. `backend/apps/test_hub/context/modules/esigning.md:129` — Integration Dependencies still lists `"DocuSeal API" — external e-signing service (mock in tests)`. DocuSeal is not a dependency anymore. Remove this bullet entirely (or replace with a note that the signing flow is fully internal — no external e-signing dependency to mock).

3. `backend/apps/test_hub/context/modules/esigning.md:153` — Coverage Gaps still lists `"DocuSeal status polling (background job to check submission status)"`. This background job was part of the DocuSeal integration and no longer exists. Remove this line; if a native-signing equivalent gap exists, reword it.

4. `backend/apps/esigning/system_documentation/ESIGNING.md:51` — Status table row still reads `"Signing request expired (managed by DocuSeal)"`. Change to: `"Signing request expired"` (drop the DocuSeal attribution).

All four are in the same two files already touched; no new files needed.
