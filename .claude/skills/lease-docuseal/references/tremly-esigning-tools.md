# Tremly E-Signing Tools Reference

This document provides tool-level instructions for agents working on the Tremly e-signing integration.

## Tool: Create Signing Submission

**When to use:** Staff wants to send a lease for signing.

**API:** `POST /api/v1/esigning/submissions/`

**Required permissions:** ADMIN or AGENT role

**Request body:**
```json
{
  "lease_id": 42,
  "signing_mode": "sequential",
  "signers": [
    {
      "name": "Jane Landlord",
      "email": "jane@example.com",
      "phone": "+27821234567",
      "role": "Landlord",
      "send_email": true,
      "order": 0
    },
    {
      "name": "John Tenant",
      "email": "john@example.com",
      "phone": "+27829876543",
      "role": "Tenant",
      "send_email": true,
      "order": 1
    }
  ]
}
```

**Validation rules:**
- `lease_id` required, must be accessible to the user
- At least 1 signer required
- Each signer needs `name` and `email`
- `signing_mode` must be "sequential" or "parallel"
- `order` is auto-assigned from list position if omitted (sequential mode)

**Side effects:**
- Generates PDF from lease template
- Uploads PDF to DocuSeal as template
- Creates DocuSeal submission
- Creates local `ESigningSubmission` record
- DocuSeal sends email to first signer (sequential) or all signers (parallel)

---

## Tool: Create Public Signing Link

**When to use:** Staff wants to share a signing link via SMS, WhatsApp, or manual email.

**API:** `POST /api/v1/esigning/submissions/<id>/public-link/`

**Request body:**
```json
{
  "submitter_id": 456,
  "send_email": false,
  "public_app_origin": "https://admin.tremly.com",
  "expires_in_days": 14
}
```

**Response:**
```json
{
  "uuid": "a1b2c3d4-...",
  "expires_at": "2024-02-14T00:00:00Z",
  "sign_path": "/sign/a1b2c3d4-.../",
  "signing_url": "https://admin.tremly.com/sign/a1b2c3d4-.../",
  "email_sent": false
}
```

**Notes:**
- If `send_email: true`, an email with the signing URL is sent to the signer
- `public_app_origin` is used as fallback if `SIGNING_PUBLIC_APP_BASE_URL` not set
- Link expires after `expires_in_days` (default 14, range 1-90)

---

## Tool: Resend Signing Invitation

**When to use:** Signer didn't receive the original email.

**API:** `POST /api/v1/esigning/submissions/<id>/resend/`

**Request body:**
```json
{
  "submitter_id": 456
}
```

**Notes:** Calls DocuSeal's `send_email` API directly. Only works if signer hasn't completed yet.

---

## Tool: Check Signer Status

**When to use:** Check who has signed and who is pending.

**API:** `GET /api/v1/esigning/submissions/<id>/signer-status/`

**Response:**
```json
{
  "submission_id": 1,
  "status": "in_progress",
  "signing_mode": "sequential",
  "signed_pdf_url": null,
  "current_signer": {"id": 457, "name": "John", "email": "john@...", "status": "sent", "order": 1},
  "completed_signers": [{"id": 456, "name": "Jane", ...}],
  "pending_signers": [],
  "declined_signers": [],
  "progress": {"total": 2, "completed": 1, "declined": 0, "pending": 1}
}
```

---

## Tool: Resolve Public Signing Link (Legacy — embed_src)

**When to use:** Legacy endpoint; returns DocuSeal embed URL. The custom signing UI uses the headless endpoints below instead.

**API:** `GET /api/v1/esigning/public-sign/<uuid>/` (no auth)

**Response:**
```json
{
  "embed_src": "https://docuseal.com/s/abc123",
  "document_title": "Property Name — Unit 1",
  "signer_name": "John Tenant",
  "signer_email": "john@example.com",
  "submission_status": "in_progress",
  "signer_status": "sent"
}
```

**Error states:**
- 404: Invalid UUID or unknown signer
- 410: Link expired, submission completed/declined, or signer already finished

---

## Tool: Get Signing Document (Headless)

**When to use:** Frontend needs the PDF to render with PDF.js.

**API:** `GET /api/v1/esigning/public-sign/<uuid>/document/` (no auth)

**Response:** Binary PDF (`application/pdf`). Proxied from DocuSeal to avoid CORS issues.

**Error states:**
- 404: Invalid link, document not available yet
- 410: Link expired, submission completed/declined, signer already finished
- 502: Could not fetch document from DocuSeal

---

## Tool: Get Signing Fields (Headless)

**When to use:** Frontend needs to know which fields the signer must fill (signature, date).

**API:** `GET /api/v1/esigning/public-sign/<uuid>/fields/` (no auth)

**Response:**
```json
{
  "signer_name": "John Tenant",
  "signer_email": "john@example.com",
  "signer_role": "First Party",
  "document_title": "Property Name — Unit 1",
  "total_pages": 14,
  "fields": [
    {
      "name": "Signature (First Party)",
      "type": "signature",
      "required": true,
      "areas": [{"x": 0.05, "y": 0.22, "w": 0.35, "h": 0.06, "page": 14}]
    },
    {
      "name": "Date (First Party)",
      "type": "date",
      "required": true,
      "areas": [{"x": 0.05, "y": 0.30, "w": 0.20, "h": 0.04, "page": 14}]
    }
  ]
}
```

---

## Tool: Submit Signature (Headless)

**When to use:** Signer has drawn their signature and picked a date; submit to DocuSeal.

**API:** `POST /api/v1/esigning/public-sign/<uuid>/submit/` (no auth)

**Request body:**
```json
{
  "fields": [
    {"name": "Signature (First Party)", "value": "data:image/png;base64,..."},
    {"name": "Date (First Party)", "value": "2026-03-26"}
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "submitter_status": "completed",
  "message": "Your signature has been submitted successfully."
}
```

**Notes:**
- Signature value must be a base64 PNG data URL
- Date value should be YYYY-MM-DD format
- Field names must match the template field names exactly
- After success, DocuSeal webhook fires (`form.completed`) for downstream processing

---

## Tool: Get Webhook Info

**When to use:** Setting up or debugging DocuSeal webhook configuration.

**API:** `GET /api/v1/esigning/webhook/info/`

**Response:**
```json
{
  "webhook_url": "https://api.tremly.com/api/v1/esigning/webhook/",
  "verify_mode": "hmac_sha256_body",
  "webhook_header_name": null,
  "docuseal_console_hooks_url": "https://signing.tremly.com/hooks"
}
```

---

## Tool: List Submissions

**When to use:** View all signing submissions for a lease.

**API:** `GET /api/v1/esigning/submissions/?lease_id=42`

**Response:** Paginated list of `ESigningSubmission` objects with full signer details.

---

## WebSocket: Real-time Signing Updates

**Endpoint:** `ws://<host>/ws/esigning/<submission_id>/`

**Auth:** JWT token required

**Events received:**
```json
{"type": "signer_completed", "submission_id": 1, "completed_signer": {...}, "next_signer": {...}, "completed_count": 1, "total_signers": 2}
{"type": "submission_completed", "submission_id": 1, "signed_pdf_url": "https://..."}
{"type": "signer_declined", "submission_id": 1, "declined_signer": {...}}
{"type": "signer_viewed", "submission_id": 1, "signer": {...}}
```

---

## Database Models Quick Reference

### ESigningSubmission
| Field | Type | Description |
|-------|------|-------------|
| `lease` | FK(Lease) | The lease being signed |
| `docuseal_submission_id` | CharField | DocuSeal's submission ID |
| `docuseal_template_id` | CharField | DocuSeal's template ID |
| `status` | CharField | pending/in_progress/completed/declined/expired |
| `signing_mode` | CharField | sequential/parallel |
| `signers` | JSONField | Array of signer objects with id, name, email, role, status, embed_src, order |
| `signed_pdf_url` | URLField | Final signed PDF download URL |
| `created_by` | FK(User) | Staff who initiated |
| `webhook_payload` | JSONField | Last webhook payload (for debugging) |

### ESigningPublicLink
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField (PK) | Unguessable link token |
| `submission` | FK(ESigningSubmission) | Parent submission |
| `submitter_id` | PositiveIntegerField | DocuSeal submitter ID |
| `expires_at` | DateTimeField | Link expiration |

### Signer JSON Object Shape
```json
{
  "id": 456,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "Tenant",
  "status": "sent",
  "slug": "abc123",
  "embed_src": "https://docuseal.com/s/abc123",
  "completed_at": null,
  "order": 0
}
```

Signer statuses: `sent` → `opened` → `completed` / `declined`
