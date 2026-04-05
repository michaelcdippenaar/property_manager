# Issue: Send Reminder Email Not Working for Native Signing
**Module:** esigning
**Status:** OPEN
**Discovered:** 2026-04-04 (manual testing)
**Priority:** Medium

## Description
The "Send Reminder" button on the signing management page fails with:
> "Email could not be sent. Check server logs and NotificationLog."

The resend endpoint (`ESigningResendView`) calls the DocuSeal API (`/submitters/{id}/send_email`), which only works for DocuSeal-backed submissions. Native signing submissions have no DocuSeal submitter ID, so the API call fails.

## Root Cause
`ESigningResendView` assumes all submissions are DocuSeal-backed. It does not have a code path for native signing submissions that would send the reminder email directly via Django's email system.

## Expected Behavior
For native signing submissions:
1. Look up the signer's email from `ESigningSubmission.signers` array
2. Compose a reminder email with the public signing link
3. Send via Django email backend (or existing notification system)
4. Log in NotificationLog

## Files Involved
- `backend/apps/esigning/views.py` — `ESigningResendView`
- `backend/apps/esigning/services.py` — needs new `send_native_signing_reminder()` function

## Status History
- 2026-04-04: Discovered during manual testing → OPEN
