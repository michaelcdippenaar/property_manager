# Issue: Document Hash Integrity Check Failure After HTML Regeneration
**Module:** esigning
**Status:** FIXED
**Discovered:** 2026-04-04 (manual testing)

## Description
After regenerating `document_html` (e.g. fixing a landlord name), the `document_hash` field was not updated. When a signer attempted to submit their signature, `submit_native_signature()` computed a SHA-256 hash of the current HTML, compared it to the stored hash, and rejected the submission with:

> "Document integrity check failed — document may have been tampered with."

## Root Cause
The `document_hash` is computed at submission creation time via `hashlib.sha256(document_html.encode()).hexdigest()`. When the HTML was manually updated in the database (to fix landlord name), the hash was not recomputed.

**Code path:** `backend/apps/esigning/services.py` → `submit_native_signature()` lines 972-975:
```python
current_hash = hashlib.sha256(submission.document_html.encode()).hexdigest()
if current_hash != submission.document_hash:
    raise ValueError('Document integrity check failed...')
```

## Fix Applied
Recomputed the hash for the affected submission (ID 74) via Django shell:
```python
sub.document_hash = hashlib.sha256(sub.document_html.encode()).hexdigest()
sub.save(update_fields=['document_hash'])
```

## Prevention
Any code path that modifies `document_html` after submission creation MUST also update `document_hash`. Consider adding a model method `update_html(new_html)` that atomically updates both fields.

## Status History
- 2026-04-04: Discovered during manual signing test → hash mismatch error
- 2026-04-04: Fixed by recomputing hash → FIXED
