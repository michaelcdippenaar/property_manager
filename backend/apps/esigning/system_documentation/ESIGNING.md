# E-Signing App

Electronic signature management for lease agreements with **sequential and parallel signing** support, using the native in-app signing flow backed by Gotenberg PDF generation.

## Overview

The e-signing app handles the full lifecycle of lease document signing:

1. **PDF Generation** — The backend generates a filled PDF from the lease data using the active `LeaseTemplate` HTML (with merge fields replaced) or a fallback table layout. Gotenberg (Docker sidecar) converts HTML → PDF.
2. **Submission Creation** — A signing submission is created with one or more signers. Supports both **sequential signing** (one after the other) and **parallel signing** (all at once).
3. **Public Signing Links** — Each signer receives a UUID-based token link (`ESigningPublicLink`) allowing passwordless signing without an account.
4. **Status Tracking** — The backend updates submission and per-signer status as signers view, complete, or decline. Webhook events (machine-to-machine) may also drive status updates.
5. **Signed PDF** — Once all signers complete, Gotenberg assembles a signed PDF with signature overlays. The file is stored in `signed_pdf_file`.

**The frontend does NOT need to generate or provide a PDF** — the backend handles everything. The frontend only needs to collect signer details and the lease ID.

---

## Model: `ESigningSubmission`

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `lease` | ForeignKey → Lease | The lease being signed (CASCADE, nullable — mandate submissions omit this) |
| `mandate` | ForeignKey → RentalMandate | The mandate being signed (nullable) |
| `status` | CharField(20) | Overall submission status (see Status Flow below) |
| `signing_mode` | CharField(12) | `"native"` (default) or `"sequential"` / `"parallel"` |
| `signers` | JSONField | Ordered array of signer objects (see Signer Object below) |
| `signed_pdf_file` | FileField | Local storage path to the completed signed PDF (blank until completed) |
| `created_by` | ForeignKey → User | User who initiated the signing (SET_NULL) |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |
| `webhook_payload` | JSONField | Raw payload from last received webhook |

### Status Flow

```
pending ──→ in_progress ──→ completed
   │             │
   │             └──→ declined
   │
   └──→ declined
```

| Status | Description |
|--------|-------------|
| `pending` | Created, awaiting first signer action |
| `in_progress` | At least one signer has viewed/started the form |
| `completed` | **All** signers have completed signing |
| `declined` | A signer declined to sign |
| `expired` | Signing request expired |

### Signing Mode

| Mode | Value | Behaviour |
|------|-------|-----------|
| Sequential | `"sequential"` | **Default.** Signers are invited in order. Signer #2 receives their email only after Signer #1 completes. Each signer has an `order` field (0-based). |
| Parallel | `"parallel"` | All signers are invited simultaneously. Everyone can sign at the same time. |

### Signer Object Shape (stored in `signers` JSONField)

Each entry in the `signers` array looks like this:

```json
{
  "id": 1,
  "name": "John Tenant",
  "email": "john@example.com",
  "role": "tenant_1",
  "status": "completed",
  "completed_at": "2026-03-20T14:30:00Z",
  "order": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Internal signer identifier (used for webhook matching) |
| `name` | string | Signer's full name |
| `email` | string | Signer's email address |
| `role` | string | Signer role key (e.g. `"tenant_1"`, `"landlord"`, `"guarantor"`) |
| `status` | string | Per-signer status: `"sent"`, `"opened"`, `"completed"`, `"declined"` |
| `completed_at` | string/null | ISO 8601 timestamp when this signer completed, or `null` |
| `order` | integer | Signing order position (0-based). Only meaningful in sequential mode. |

**Per-signer status transitions:**

```
sent ──→ opened ──→ completed
  │         │
  │         └──→ declined
  │
  └──→ declined
```

- `sent` — Invitation sent (or queued, in sequential mode for later signers)
- `opened` — Signer has viewed the form
- `completed` — Signer has finished signing
- `declined` — Signer declined to sign

---

## API Endpoints

All endpoints are prefixed with `/api/v1/esigning/`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/submissions/` | List submissions |
| `POST` | `/submissions/` | Create new submission (triggers PDF generation + native signing setup) |
| `GET` | `/submissions/<id>/` | Retrieve a single submission |
| `POST` | `/submissions/<id>/resend/` | Resend signing notification to a specific signer |
| `POST` | `/submissions/<id>/public-link/` | Create UUID link for passwordless signing (staff only) |
| `GET` | `/public-sign/<uuid>/` | Resolve link → signing payload for one signer (**no auth**) |
| `POST` | `/webhook/` | Webhook receiver for machine-to-machine events (no auth) |

---

### 1. List Submissions

```
GET /api/v1/esigning/submissions/
```

**Auth:** Required (Bearer token)

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `lease_id` | integer | No | Filter submissions by lease ID |

**Response:** `200 OK` — Paginated list

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "lease": 42,
      "lease_label": "Sunset Apartments — Unit 101",
      "status": "completed",
      "signing_mode": "sequential",
      "signers": [
        {
          "id": 1,
          "name": "Jane Landlord",
          "email": "jane@example.com",
          "role": "landlord",
          "status": "completed",
          "completed_at": "2026-03-18T09:00:00Z",
          "order": 0
        },
        {
          "id": 2,
          "name": "John Tenant",
          "email": "john@example.com",
          "role": "tenant_1",
          "status": "completed",
          "completed_at": "2026-03-20T14:30:00Z",
          "order": 1
        }
      ],
      "signed_pdf_file": "/media/esigning/signed_pdfs/submission_1.pdf",
      "created_at": "2026-03-10T10:00:00Z",
      "updated_at": "2026-03-20T14:30:00Z"
    }
  ]
}
```

**Error Responses:**

| Status | Reason |
|--------|--------|
| `401` | Not authenticated |

---

### 2. Create Submission (Send for Signing)

```
POST /api/v1/esigning/submissions/
```

**Auth:** Required (Bearer token)

**This is the main endpoint the frontend calls to kick off signing.** The backend handles everything else (PDF generation, public link creation, signer notifications).

**Request Body:**

```json
{
  "lease_id": 42,
  "signing_mode": "sequential",
  "signers": [
    {
      "name": "Jane Landlord",
      "email": "jane@example.com",
      "role": "First Party",
      "send_email": true,
      "order": 0
    },
    {
      "name": "John Tenant",
      "email": "john@example.com",
      "role": "Second Party",
      "send_email": true,
      "order": 1
    },
    {
      "name": "Alice Witness",
      "email": "alice@example.com",
      "role": "Witness",
      "send_email": true,
      "order": 2
    }
  ]
}
```

**Request Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `lease_id` | integer | **Yes** | — | ID of the lease to sign |
| `signing_mode` | string | No | `"sequential"` | `"sequential"` or `"parallel"` |
| `signers` | array | **Yes** | — | Must contain at least one signer |
| `signers[].name` | string | **Yes** | — | Signer's full name |
| `signers[].email` | string | **Yes** | — | Signer's email (signing notification sent here) |
| `signers[].role` | string | No | `"signer"` | Signer role key. Used for public link lookup. Examples: `"tenant_1"`, `"landlord"`, `"guarantor"`. |
| `signers[].send_email` | boolean | No | `true` | Whether to email the signer their signing link immediately on submission creation. |
| `signers[].order` | integer | No | Position in array (0, 1, 2...) | **Sequential mode only.** Controls signing order. Lower numbers go first. If omitted, the array position is used as the order. Ignored in parallel mode. |

**Signing Mode Behaviour:**

| Mode | What happens |
|------|-------------|
| `"sequential"` | Only the first signer (order 0) gets an email immediately. Each subsequent signer is emailed only after the previous one completes. The frontend can show which signer is "up next" by checking each signer's `status` in order. |
| `"parallel"` | All signers get their emails at the same time. Everyone can sign independently. |

**Response:** `201 Created`

```json
{
  "id": 1,
  "lease": 42,
  "lease_label": "Sunset Apartments — Unit 101",
  "status": "pending",
  "signing_mode": "sequential",
  "signers": [
    {
      "id": 10,
      "name": "Jane Landlord",
      "email": "jane@example.com",
      "role": "landlord",
      "status": "sent",
      "completed_at": null,
      "order": 0
    },
    {
      "id": 11,
      "name": "John Tenant",
      "email": "john@example.com",
      "role": "tenant_1",
      "status": "sent",
      "completed_at": null,
      "order": 1
    },
    {
      "id": 12,
      "name": "Alice Witness",
      "email": "alice@example.com",
      "role": "guarantor",
      "status": "sent",
      "completed_at": null,
      "order": 2
    }
  ],
  "signed_pdf_file": "",
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-20T10:00:00Z"
}
```

> **Note:** In sequential mode, only the first signer (order 0) receives an email at creation time. Each subsequent signer is notified only after the previous signer completes.

**Error Responses:**

| Status | Body | Reason |
|--------|------|--------|
| `400` | `{"error": "lease_id is required"}` | Missing `lease_id` |
| `400` | `{"error": "At least one signer is required"}` | Empty signers array |
| `400` | `{"error": "signing_mode must be \"sequential\" or \"parallel\""}` | Invalid signing mode |
| `401` | — | Not authenticated |
| `404` | — | Lease not found |
| `500` | `{"error": "<exception message>"}` | PDF generation or signing setup error |

---

### 3. Retrieve Submission

```
GET /api/v1/esigning/submissions/<id>/
```

**Auth:** Required (Bearer token)

**Response:** `200 OK` — Same shape as a single item in the list response.

Use this to poll the current status of a submission and its signers. The `signers` array will reflect real-time updates from webhooks.

**Frontend Tip:** To show a signing progress indicator, iterate through `signers` (which are sorted by `order`) and check each signer's `status`:
- `"sent"` → Waiting (grey/pending)
- `"opened"` → Currently viewing (blue/active)
- `"completed"` → Done (green/check)
- `"declined"` → Declined (red/X)

**Error Responses:**

| Status | Reason |
|--------|--------|
| `401` | Not authenticated |
| `404` | Submission not found |

---

### 4. Resend Signing Email

```
POST /api/v1/esigning/submissions/<id>/resend/
```

**Auth:** Required (Bearer token)

Resends the signing notification email/SMS to a specific signer. Useful when:
- A signer hasn't received the notification
- The email went to spam
- You want to remind a signer to complete their step

**Request Body:**

```json
{
  "submitter_id": 10
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `submitter_id` | integer | **Yes** | The signer `id` field from the signer object in the `signers` array |

**Response:** `200 OK`

```json
{
  "ok": true
}
```

**Error Responses:**

| Status | Body | Reason |
|--------|------|--------|
| `400` | `{"error": "submitter_id required"}` | Missing submitter_id |
| `401` | — | Not authenticated |
| `404` | — | Submission not found |

> **Sequential mode note:** In sequential mode, resending to a signer whose turn hasn't come yet will still send the notification, but the signing link will only become active when prior signers complete.

---

### 5. Create passwordless signing link (staff)

```
POST /api/v1/esigning/submissions/<id>/public-link/
```

**Auth:** Required — **admin** or **agent** only (same lease scope as other esigning actions).

**Request body:**

```json
{
  "submitter_id": 10,
  "expires_in_days": 14,
  "send_email": false,
  "public_app_origin": "https://admin.example.com"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `submitter_id` | Yes | Signer id (`signers[].id` on the submission) |
| `expires_in_days` | No | Default from `ESIGNING_PUBLIC_LINK_EXPIRY_DAYS` (1–90) |
| `send_email` | No | If `true`, sends the signing link to the signer’s email via `apps.notifications.send_email` (requires Django email / SMTP). |
| `public_app_origin` | When emailing without `SIGNING_PUBLIC_APP_BASE_URL` | Admin site origin (no trailing slash), e.g. `https://admin.example.com` — used to build the absolute URL in the email. The admin UI sends `window.location.origin`. |

**Response:** `201 Created`

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-04-08T12:00:00+00:00",
  "sign_path": "/sign/550e8400-e29b-41d4-a716-446655440000/",
  "signing_url": "https://your-admin-host/sign/550e8400-.../",
  "email_sent": false,
  "email_error": ""
}
```

`signing_url` is set when `SIGNING_PUBLIC_APP_BASE_URL` is configured, or when `public_app_origin` is sent (combined with `sign_path`). Otherwise the admin UI uses `window.location.origin + sign_path` for copy/paste.

If `send_email` is `true` and no absolute URL can be built, the API returns **`400`** (no link is kept). If the link is created but SMTP fails, response is still **`201`** with `email_sent: false` and `email_error` set.

The **admin SPA** exposes a public route **`/sign/:token`** (no login) that calls **`GET /public-sign/<uuid>/`** and renders the native in-app signing flow.

---

### 6. Public signing payload (no auth)

```
GET /api/v1/esigning/public-sign/<uuid>/
```

**Auth:** None.

Returns the signing payload (document HTML, signer details) for the signer tied to that link. Responds `410` if the link expired, the submission finished, or that signer already completed/declined.

---

### 7. Esigning Webhook

```
POST /api/v1/esigning/webhook/
```

**Auth:** None (publicly accessible, CSRF-exempt) — secured by `WEBHOOK_SECRET_ESIGNING` HMAC-SHA256 signature verification.

This endpoint is called by machine-to-machine callbacks — the frontend does not call it directly. However, the frontend should understand what it does because **it changes the data the frontend reads**.

**Webhook Events and Their Effects:**

| Event | Overall Status Change | Per-Signer Update | Description |
|-------|----------------------|-------------------|-------------|
| `submission.completed` | → `completed` | All signers updated from payload | **All** signers done. Signed PDF is generated and stored. |
| `form.completed` | → `in_progress` (if was `pending`) | The specific signer → `completed` + `completed_at` set | **One** signer finished. In sequential mode, the next signer is notified. |
| `submission.declined` | → `declined` | The declining signer → `declined` | A signer refused to sign. The whole submission is marked declined. |
| `form.viewed` | → `in_progress` (if was `pending`) | The specific signer → `opened` | A signer opened the signing page. |
| `form.started` | → `in_progress` (if was `pending`) | The specific signer → `opened` | A signer started filling in fields. |

**Sequential Signing Webhook Flow (example: 3 signers):**

```
1. POST webhook: form.viewed    (signer #0 opens)     → status: in_progress, signer[0]: opened
2. POST webhook: form.completed (signer #0 signs)     → status: in_progress, signer[0]: completed
   ── backend notifies signer #1 ──
3. POST webhook: form.viewed    (signer #1 opens)     → status: in_progress, signer[1]: opened
4. POST webhook: form.completed (signer #1 signs)     → status: in_progress, signer[1]: completed
   ── backend notifies signer #2 ──
5. POST webhook: form.viewed    (signer #2 opens)     → status: in_progress, signer[2]: opened
6. POST webhook: form.completed (signer #2 signs)     → status: in_progress, signer[2]: completed
7. POST webhook: submission.completed (all done)       → status: completed, signed_pdf_file set
```

---

## Frontend Integration Guide

### Creating a Signing Submission

The minimal frontend flow:

1. **Collect signer details** — name, email, and optionally role and order
2. **POST to `/api/v1/esigning/submissions/`** with `lease_id`, `signing_mode`, and `signers`
3. **Display the returned signers** with their statuses

```javascript
// Example: Create a sequential signing submission
const response = await api.post('/api/v1/esigning/submissions/', {
  lease_id: 42,
  signing_mode: 'sequential',  // or 'parallel'
  signers: [
    { name: 'Jane Landlord', email: 'jane@example.com', role: 'First Party' },    // signs first
    { name: 'John Tenant',   email: 'john@example.com',  role: 'Second Party' },   // signs second
    { name: 'Alice Witness', email: 'alice@example.com',  role: 'Witness' },        // signs last
  ],
});
// response.data.signers is sorted by order: [0, 1, 2]
```

### Displaying Signing Progress

```javascript
// Fetch current status
const submission = await api.get(`/api/v1/esigning/submissions/${id}/`);

// Determine the "current" signer (sequential mode)
const currentSigner = submission.signers.find(s => s.status !== 'completed');

// Build a progress display
submission.signers.forEach((signer, idx) => {
  console.log(`${idx + 1}. ${signer.name} (${signer.role}) — ${signer.status}`);
  // e.g. "1. Jane Landlord (First Party) — completed"
  // e.g. "2. John Tenant (Second Party) — opened"    ← currently signing
  // e.g. "3. Alice Witness (Witness) — sent"          ← waiting for turn
});
```

### Signing Mode UI Suggestions

| Element | Sequential | Parallel |
|---------|-----------|----------|
| Signer list | Show numbered steps (1→2→3) with status indicators | Show all signers equally, no numbering |
| Progress | Stepper/timeline component showing which signer is active | Progress bar or count (2/3 signed) |
| Reorder | Allow drag-to-reorder before sending (send `order` field) | No ordering needed |
| Current step | Highlight the active signer | N/A — all are active |
| Resend button | Show only for the current (active) signer | Show for any signer who hasn't completed |

### Resending Notifications

```javascript
// Resend to a specific signer using their signer id
await api.post(`/api/v1/esigning/submissions/${submissionId}/resend/`, {
  submitter_id: signer.id,  // from the signer object in the signers array
});
```

### Polling for Updates

Since webhook events update the backend asynchronously, the frontend should poll the detail endpoint to reflect changes:

```javascript
// Poll every 10 seconds while status is 'pending' or 'in_progress'
const poll = setInterval(async () => {
  const { data } = await api.get(`/api/v1/esigning/submissions/${id}/`);
  updateUI(data);
  if (data.status === 'completed' || data.status === 'declined') {
    clearInterval(poll);
  }
}, 10000);
```

---

## Services Layer (`services.py`)

> This section is for backend reference — the frontend does not interact with these directly.

### `create_lease_submission(lease, signers, signing_mode='sequential') → dict`

Orchestrates the full signing flow:

1. **`generate_lease_html(lease, template)`** — Renders the active `LeaseTemplate` HTML with merge fields resolved. The HTML snapshot is stored on the submission for tamper detection.

2. **`create_submission(lease, signers, signing_mode)`** — Creates an `ESigningSubmission`, generates `ESigningPublicLink` entries for each signer, and sends signing notifications (email/SMS) to the first signer(s).

3. **`generate_signed_pdf(submission)`** — Calls Gotenberg to assemble a signed PDF with signature overlays once all signers complete. Stores the result in `signed_pdf_file`.

### PDF Merge Fields

The PDF generator replaces these merge fields in the template HTML:

| Field | Source |
|-------|--------|
| `landlord_name` | Property owner's full name |
| `property_address` | Property address |
| `property_name` | Property name |
| `unit_number` | Unit number |
| `city` / `province` | Property location |
| `tenant_name` | Primary tenant's full name |
| `tenant_id` / `tenant_phone` / `tenant_email` | Primary tenant details |
| `lease_start` / `lease_end` | Lease dates (ISO format) |
| `monthly_rent` / `deposit` | Formatted as `R 5,000.00` |
| `notice_period_days` | Notice period |
| `water_included` / `electricity_prepaid` | Utility inclusion flags |
| `max_occupants` | Maximum occupants |
| `payment_reference` | Payment reference |
| `co_tenants` | Comma-separated co-tenant names |

Supports both `<span data-merge-field="field_name">...</span>` and `{{ field_name }}` syntax.

---

## Configuration

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `WEBHOOK_SECRET_ESIGNING` | No | `""` | HMAC secret for webhook signature verification |
| `WEBHOOK_HEADER_ESIGNING` | No | `""` | When set, switches verification to static-token mode instead of HMAC-SHA256 |
| `ESIGNING_PUBLIC_LINK_EXPIRY_DAYS` | No | `14` | Default lifetime for UUID signing links |
| `SIGNING_PUBLIC_APP_BASE_URL` | No | `""` | Full admin origin for absolute URLs in API (e.g. `https://admin.example.com`) |
| `GOTENBERG_URL` | No | `http://localhost:3000` | Gotenberg Docker service URL for PDF generation |

---

## Security Notes

| ID | Severity | Issue |
|----|----------|-------|
| VULN-9 | (reduced) | **Was critical IDOR.** Create, resend, and public-link creation are **staff-only** and **lease-scoped** (aligned with leases API). Tenants may only list/detail submissions for their leases. |
| VULN-10 | High | **Optional webhook verification** — If `WEBHOOK_SECRET_ESIGNING` is unset, anyone can POST fake webhook events to change submission status. |
