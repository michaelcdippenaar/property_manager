---
id: RNT-SEC-043
stream: rentals
title: "POPIA DSAR: emit audit event on GET DSARReviewView (read-path parity with POST)"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214237345319240"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Emit a `popia.dsar_review_opened` audit log entry when an operator GETs the DSAR review endpoint, bringing the read path into parity with the POST approve/deny paths which already log.

## Acceptance criteria
- [x] `DSARReviewView.get` (line ~393–406 in `backend/apps/popia/views.py`) calls `_log_audit("popia.dsar_review_opened", ...)` with payload `{dsar_id, request_type, retention_flags_computed: bool}`
- [x] No PII in the audit payload — retention flag values are not logged, only whether they were computed
- [x] Existing POST approve/deny audit entries are untouched
- [x] Unit test asserts that a GET to the review endpoint creates an audit log entry with event `popia.dsar_review_opened`

## Files likely touched
- `backend/apps/popia/views.py` (DSARReviewView.get, ~line 393)
- `backend/apps/popia/tests/test_dsar_views.py` (or equivalent)

## Test plan
**Manual:**
- Log in as `agency_admin`, GET `/api/v1/popia/dsar-queue/<id>/review/`, confirm a new audit entry appears in the audit log

**Automated:**
- `cd backend && pytest apps/popia/tests/ -k dsar_review -v`

## Handoff notes
2026-04-23 — Promoted from discovery `2026-04-23-dsar-review-get-no-audit.md` (found by rentals-reviewer during RNT-SEC-041). Read-path audit gap only; POST paths already log correctly.

2026-04-23 — **Implementer handoff:** added `_log_audit("popia.dsar_review_opened", ...)` call to `DSARReviewView.get()` method in `backend/apps/popia/views.py` (lines 406-414). Payload includes `dsar_id`, `request_type`, and `retention_flags_computed` (boolean flag indicating whether retention checks were computed, not the actual flag values themselves — no PII). Added two new test methods: `test_get_review_creates_audit_event()` and `test_get_review_sar_audit_event_no_retention_flags()` in `backend/apps/popia/tests/test_dsar.py` to verify audit event creation for both RTBF and SAR request types. All 51 existing DSAR tests pass. Existing POST approve/deny audit paths remain untouched.
