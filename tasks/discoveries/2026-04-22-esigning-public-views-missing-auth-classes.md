---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-002
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found

`ESigningPublicDraftView` (`esigning/views.py:847`) and `ESigningPublicDocumentsView` (`esigning/views.py:909`) declare `permission_classes = [AllowAny]` but are missing `authentication_classes = []`. Three other public signing views in the same file (`ESigningPublicSignDetailView`, `ESigningPublicDocumentView`, `ESigningPublicSubmitSignatureView`) correctly set both. The inconsistency means DRF still attempts JWT authentication on the draft and file-upload views before falling through to AllowAny, which can cause spurious 401s on expired tokens sent by mistake.

## Why it matters

Inconsistent auth configuration on public views can produce confusing client errors and is a maintenance hazard. Aligning all six public views to `authentication_classes = []` removes the JWT processing overhead and makes the security posture explicit.

## Where I saw it

- `backend/apps/esigning/views.py:839` (`ESigningPublicDraftView`) — missing `authentication_classes = []`
- `backend/apps/esigning/views.py:909` (`ESigningPublicDocumentsView`) — missing `authentication_classes = []`

## Suggested acceptance criteria (rough)

- [ ] Add `authentication_classes = []` to `ESigningPublicDraftView` and `ESigningPublicDocumentsView`
- [ ] Verify no existing tests break

## Why I didn't fix it in the current task

Pre-existing inconsistency not introduced by RNT-SEC-002; fixing it in this diff would expand scope beyond rate-limiting.
