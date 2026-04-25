---
id: RNT-QUAL-066
stream: rentals-quality
title: "Log (don't swallow) storage errors when deleting lease document files"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214274171423379"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Replace bare `except Exception: pass` blocks in the lease document delete paths with `logger.exception(...)` so S3/MinIO errors surface in logs/Sentry instead of silently orphaning files.

## Acceptance criteria

- [x] `backend/apps/leases/views.py:35-41` (`perform_destroy`): `except Exception: pass` replaced with `logger.exception("Failed to delete lease document file %s", doc.pk)`.
- [x] `backend/apps/leases/views.py:90-99` (`delete_document` action): same replacement.
- [x] The DB delete still proceeds even when the storage delete fails (swallow is retained, logging is added).
- [x] A module-level `logger = logging.getLogger(__name__)` is present (add if missing).
- [x] No POPIA/right-to-erasure regression: the fix does not suppress the DB-row deletion.

## Files likely touched

- `backend/apps/leases/views.py` (lines 35-41, 90-99)

## Test plan

**Manual:**
- Mock storage backend to raise on delete; confirm a log line appears and the DB row is still removed.

**Automated:**
- `cd backend && pytest apps/leases/tests/ -k delete`

## Handoff notes

Promoted from discovery `2026-04-24-lease-document-delete-silent-failure.md` (2026-04-24). P2 — silent POPIA/erasure leak and orphaned storage risk; 2-line fix.

2026-04-24 (implementer): Added `import logging` and `logger = logging.getLogger(__name__)` to `backend/apps/leases/views.py`. Replaced both bare `except Exception: pass` blocks (perform_destroy and delete_document) with `logger.exception(...)` calls — swallow behaviour retained so DB deletion always proceeds. Added 4 unit tests in `backend/apps/test_hub/leases/unit/test_document_delete_logging.py` using caplog to assert log emission and DB deletion; all 4 pass.
