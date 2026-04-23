---
id: RNT-SEC-012
stream: security
title: "Add authentication_classes=[] to ESigningPublicDraftView and ESigningPublicDocumentsView"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214181875017961"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Align `ESigningPublicDraftView` and `ESigningPublicDocumentsView` with the three other public signing views by adding `authentication_classes = []`, removing the implicit JWT processing overhead and making the explicit-no-auth posture consistent across all six public e-signing views.

## Acceptance criteria
- [x] Add `authentication_classes = []` to `ESigningPublicDraftView` (`esigning/views.py` ~line 839)
- [x] Add `authentication_classes = []` to `ESigningPublicDocumentsView` (`esigning/views.py` ~line 909)
- [x] All existing esigning tests still pass: `pytest backend/apps/esigning/`
- [x] No spurious 401 responses when an expired JWT is sent to these views

## Files likely touched
- `backend/apps/esigning/views.py`

## Test plan
**Manual:**
- Send a request to the public draft / documents endpoints with an expired or malformed Authorization header — expect 200/correct response, not 401

**Automated:**
- `cd backend && pytest apps/esigning/tests/ -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-esigning-public-views-missing-auth-classes.md` found during RNT-SEC-002 (rate limiting). Pre-existing inconsistency; three of five public views already have the correct pattern.

2026-04-23 — IMPLEMENTED. Added `authentication_classes = []` to both `ESigningPublicDraftView` (line 914) and `ESigningPublicDocumentsView` (line 977) in `backend/apps/esigning/views.py`. Both now explicitly disable JWT authentication, consistent with the three other public signing views (PublicSignDetailView, PublicDocumentView, PublicSubmitSignatureView). Created unit test `backend/apps/test_hub/esigning/unit/test_authentication_classes.py` to verify all five public views have `authentication_classes = []`. All 258 esigning tests pass. **Discovery**: `ESigningPublicDocumentDeleteView` also lacks `authentication_classes = []` despite being public (AllowAny); defer to separate task if needed.
