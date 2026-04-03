---
name: lease-docuseal
description: >
  Manage DocuSeal e-signing workflows for the Tremly property management platform. Use this skill
  when the user asks about e-signing, DocuSeal API, signing submissions, public signing links,
  sequential/parallel signing, webhook handling, PDF generation for leases, template uploads,
  signer management, or troubleshooting the signing pipeline. Also trigger for: "send for signing",
  "signing link", "DocuSeal webhook", "embed signing", "public sign", "resend invitation",
  "sequential signing", "parallel signing", "signing status", "signed PDF", or any question about
  how the e-signing flow works end-to-end in this project.
---

# DocuSeal E-Signing — Tremly Integration Skill

You are an expert at the DocuSeal API and the Tremly e-signing integration. Use this skill to manage, debug, extend, or explain the e-signing pipeline.

## Architecture Overview

### Stack
- **Backend**: Django + DRF (`backend/apps/esigning/`)
- **Frontend Admin**: Vue 3 SPA (`admin/src/views/leases/ESigningPanel.vue`, `admin/src/views/signing/PublicSignView.vue`)
- **Mobile**: Flutter (`mobile/lib/screens/esigning/`, `mobile/lib/services/esigning_service.dart`)
- **DocuSeal**: Self-hosted via Docker (`docker-compose.docuseal.yml`) or cloud API
- **Real-time**: Django Channels WebSocket (`backend/apps/esigning/consumers.py`)

### Key Files
| Layer | File | Purpose |
|-------|------|---------|
| Models | `backend/apps/esigning/models.py` | `ESigningSubmission`, `ESigningPublicLink` |
| Services | `backend/apps/esigning/services.py` | PDF generation, DocuSeal API calls, submission orchestration |
| Views | `backend/apps/esigning/views.py` | REST endpoints: create, list, resend, public-link, public-sign |
| Webhooks | `backend/apps/esigning/webhooks.py` | DocuSeal event processing, next-signer notification, WS broadcast |
| Serializers | `backend/apps/esigning/serializers.py` | DRF serializers |
| URLs | `backend/apps/esigning/urls.py` | URL routing |
| WebSocket | `backend/apps/esigning/consumers.py` | Real-time signer status updates |
| WS Routing | `backend/apps/esigning/routing.py` | `ws/esigning/<id>/` |
| Vue Panel | `admin/src/views/leases/ESigningPanel.vue` | Staff signing UI (embedded in lease drawer) |
| Vue Public | `admin/src/views/signing/PublicSignView.vue` | Passwordless signing page with PDF.js viewer + signature_pad (headless, no iframe) |
| Flutter Service | `mobile/lib/services/esigning_service.dart` | Models + API calls |
| Flutter Screens | `mobile/lib/screens/esigning/` | Tenant signing UI + WebView |
| Documentation | `backend/apps/esigning/system_documentation/` | ESIGNING.md, VUE_INTEGRATION.md, FLUTTER_INTEGRATION.md |

## Configuration (.env)

```env
# Required
DOCUSEAL_API_URL=https://api.docuseal.com     # or http://127.0.0.1:3000/api for self-hosted
DOCUSEAL_API_KEY=your-token                    # from DocuSeal Settings → API

# Webhook verification (pick one mode)
DOCUSEAL_WEBHOOK_SECRET=your-hmac-secret       # HMAC SHA256 (recommended)
DOCUSEAL_WEBHOOK_HEADER_NAME=                  # leave empty for HMAC, set for static header mode

# Public signing URLs
SIGNING_PUBLIC_APP_BASE_URL=https://admin.example.com  # base URL for email signing links
ESIGNING_PUBLIC_LINK_EXPIRY_DAYS=14                    # 1-90 days

# Optional
ESIGNING_WEBHOOK_PUBLIC_URL=https://api.example.com    # override webhook URL in info endpoint
DOCUSEAL_HOOK_URL=https://signing.example.com/hooks    # bookmark for DocuSeal console
```

## Core Workflow: Creating a Signing Submission

### Step-by-step (sequential mode)

1. **Staff** opens lease → clicks "Send for Signing"
2. **Frontend** `POST /api/v1/esigning/submissions/` with `lease_id`, `signers[]`, `signing_mode`
3. **Backend** `services.create_lease_submission()`:
   a. `generate_lease_pdf(lease)` — renders HTML template with merge fields → xhtml2pdf → PDF bytes
   b. `upload_pdf_template(pdf_bytes, name, num_signers)` — base64 encode → `POST /templates/pdf` to DocuSeal with signature+date fields positioned on last page
   c. `create_submission(template_id, submitters)` — `POST /submissions` to DocuSeal with submitter order
4. **Backend** creates `ESigningSubmission` record with signer JSON (includes `embed_src`, `slug`, `id` from DocuSeal)
5. **DocuSeal** sends email to first signer (order=0)
6. **Signer 1** signs → DocuSeal `POST` webhook `form.completed`
7. **Webhook handler** updates signer status, creates `ESigningPublicLink` for next signer, emails them
8. **Signer 2** signs → DocuSeal `POST` webhook `submission.completed`
9. **Webhook handler** sets status=completed, stores `signed_pdf_url`, notifies staff

### Parallel mode
- All signers get emails simultaneously (no `order` field sent)
- Each `form.completed` webhook updates individual signer status
- `submission.completed` fires when ALL signers have signed

## DocuSeal API Calls Made

| Service Function | DocuSeal Endpoint | Purpose |
|-----------------|-------------------|---------|
| `upload_pdf_template()` | `POST /templates/pdf` | Upload base64 PDF with field positions |
| `create_submission()` | `POST /submissions` | Create signing workflow with submitters |
| `get_submitter()` | `GET /submitters/{id}` | Fetch submitter details (status, documents) |
| `get_template_fields()` | `GET /templates/{id}` | Fetch template field definitions + positions |
| `submit_signature()` | `PUT /submitters/{id}` | Headless: submit signature + mark completed |
| `get_document_pdf_url()` | `GET /submitters/{id}` | Extract PDF document URL from submitter data |
| `ESigningResendView` | `POST /api/submitters/{id}/send_email` | Resend invitation email |

### Template Upload Payload
```json
{
  "name": "Lease - Tenant Name - Property Unit X",
  "documents": [{
    "name": "lease.pdf",
    "file": "<base64>",
    "fields": [
      {"name": "Signature (First Party)", "type": "signature", "role": "First Party", "required": true,
       "areas": [{"x": 0.05, "y": 0.82, "w": 0.35, "h": 0.06, "page": 1}]},
      {"name": "Date (First Party)", "type": "date", "role": "First Party", "required": true,
       "areas": [{"x": 0.55, "y": 0.82, "w": 0.20, "h": 0.04, "page": 1}]},
      {"name": "Signature (Signer 2)", "type": "signature", "role": "Signer 2", "required": true,
       "areas": [{"x": 0.05, "y": 0.72, "w": 0.35, "h": 0.06, "page": 1}]},
      {"name": "Date (Signer 2)", "type": "date", "role": "Signer 2", "required": true,
       "areas": [{"x": 0.55, "y": 0.72, "w": 0.20, "h": 0.04, "page": 1}]}
    ]
  }]
}
```

### Submission Create Payload
```json
{
  "template_id": 123,
  "send_email": true,
  "submitters": [
    {"name": "Jane Landlord", "email": "jane@example.com", "role": "First Party", "send_email": true, "order": 0},
    {"name": "John Tenant", "email": "john@example.com", "role": "Signer 2", "send_email": true, "order": 1}
  ]
}
```

## Webhook Events Handled

| Event | What Happens | Status Change |
|-------|-------------|---------------|
| `form.viewed` | Signer opened the document | pending → in_progress, signer → opened |
| `form.started` | Signer started filling | pending → in_progress, signer → opened |
| `form.completed` | One signer finished | pending → in_progress, signer → completed. **Sequential: auto-notifies next signer** |
| `submission.completed` | All signers done | → completed. Stores `signed_pdf_url`. Notifies staff. |
| `submission.declined` | A signer declined | → declined. Signer → declined. Notifies staff. |

### Webhook Verification Modes
1. **HMAC SHA256** (default): `X-Docuseal-Signature` header = `hmac(secret, body)`
2. **Static header**: Custom header name + value compared with `hmac.compare_digest`
3. **None**: If `DOCUSEAL_WEBHOOK_SECRET` is empty (NOT recommended for production)

## Public Signing Links (Passwordless)

- Staff creates via `POST /api/v1/esigning/submissions/<id>/public-link/` with `submitter_id`
- Creates `ESigningPublicLink` (UUID primary key, expires in N days)
- URL format: `https://admin.example.com/sign/<uuid>/`
- Vue route `/sign/:token` loads `PublicSignView.vue` (no auth required)
- Validates: link exists, not expired, submission active, signer not already completed

## Headless Signing Flow (Custom UI — No DocuSeal iframe)

The signing page uses **PDF.js** to render the document and **signature_pad** to capture signatures.
DocuSeal is used purely as a headless API — no iframe or DocuSeal-hosted pages are shown.

### Frontend Flow (`PublicSignView.vue`)
1. Signer opens `/sign/<uuid>/`
2. Vue component calls 2 APIs in parallel:
   - `GET /api/v1/esigning/public-sign/<uuid>/fields/` → field definitions (name, type, areas/positions)
   - `GET /api/v1/esigning/public-sign/<uuid>/document/` → PDF bytes (proxied from DocuSeal)
3. **Step 1 (Review)**: PDF.js renders all pages on canvases. Signer reads the document.
4. **Step 2 (Sign)**: Signer draws signature on a `signature_pad` canvas and picks a date.
5. On submit: `POST /api/v1/esigning/public-sign/<uuid>/submit/` with signature as base64 PNG data URL + date.
6. Backend calls `PUT /submitters/{id}` with `completed: true` and the field values.
7. Success screen shown. DocuSeal webhook fires for downstream processing.

### Backend Headless Endpoints

| Endpoint | View Class | Purpose |
|----------|-----------|---------|
| `GET /public-sign/<uuid>/document/` | `ESigningDocumentView` | Proxies the PDF from DocuSeal (avoids CORS) |
| `GET /public-sign/<uuid>/fields/` | `ESigningFieldsView` | Returns field definitions filtered by signer's role |
| `POST /public-sign/<uuid>/submit/` | `ESigningSubmitSignatureView` | Submits signature + date to DocuSeal headless API |

### Submit Signature Request Body
```json
{
  "fields": [
    {"name": "Signature (First Party)", "value": "data:image/png;base64,..."},
    {"name": "Date (First Party)", "value": "2026-03-26"}
  ]
}
```

### Key Service Functions for Headless Mode
```python
# Get submitter details (status, documents)
services.get_submitter(submitter_id) -> dict

# Get template field positions for rendering
services.get_template_fields(template_id) -> dict

# Submit signature and mark complete (headless)
services.submit_signature(submitter_id, fields) -> dict
# fields = [{"name": "Signature (First Party)", "default_value": "data:image/png;base64,..."}]

# Get the PDF URL for proxying to frontend
services.get_document_pdf_url(submitter_id) -> str | None
```

### NPM Dependencies for Signing Page
- `pdfjs-dist` — PDF rendering on canvas
- `signature_pad` — Touch/mouse signature capture

## Merge Fields (PDF Generation)

The following fields are available in `build_lease_context()`:

| Field | Source |
|-------|--------|
| `landlord_name` | `property.owner.full_name` |
| `property_address` | `property.address` |
| `property_name` | `property.name` |
| `unit_number` | `unit.unit_number` |
| `city` | `property.city` |
| `province` | `property.province` |
| `tenant_name` | `lease.primary_tenant.full_name` |
| `tenant_id` | `lease.primary_tenant.id_number` |
| `tenant_phone` | `lease.primary_tenant.phone` |
| `tenant_email` | `lease.primary_tenant.email` |
| `lease_start` | `lease.start_date` |
| `lease_end` | `lease.end_date` |
| `monthly_rent` | `R X,XXX.XX` format |
| `deposit` | `R X,XXX.XX` format |
| `notice_period_days` | lease field |
| `water_included` | "Included" or "Excluded" |
| `electricity_prepaid` | "Prepaid" or "Included in rent" |
| `max_occupants` | lease field |
| `payment_reference` | lease field |
| `co_tenants` | comma-separated names |

## Troubleshooting Guide

### "DOCUSEAL_API_KEY is empty"
- Set `DOCUSEAL_API_KEY` in `backend/.env` and restart Django

### Webhook not firing
1. Check `GET /api/v1/esigning/webhook/info/` for the correct URL
2. Paste that URL in DocuSeal console → Settings → Webhooks
3. Ensure the server is publicly reachable (use ngrok for local dev)
4. Check `DOCUSEAL_WEBHOOK_SECRET` matches what's in DocuSeal

### Signature fields overlapping
- `upload_pdf_template()` positions fields on the **last page** (dedicated signature page) at `y = 0.22 + (i * 0.18)`
- With >4 signers, fields may overlap or go off-page
- Fix: reduce spacing or generate extra signature pages

### Sequential signer not getting notified
- Check webhook handler `_notify_next_signer()` in `webhooks.py`
- Requires `SIGNING_PUBLIC_APP_BASE_URL` to build email URLs
- Check email service logs in `NotificationLog`

### embed_src empty for a signer
- In sequential mode, DocuSeal may not provide `embed_src` for later signers until prior ones complete
- The public-link flow handles this by re-fetching from the signer record

## Common Operations

### Add a new merge field
1. Add to `build_lease_context()` in `services.py`
2. Add `{{field_name}}` or `<span data-merge-field="field_name">` in template HTML
3. Update `ESIGNING.md` documentation

### Change signature field positioning
- Edit `upload_pdf_template()` in `services.py`
- `x`, `y` are fractions of page (0.0 = top-left)
- `w`, `h` are fractions of page dimensions

### Add a new webhook event handler
1. Add `elif event_type == 'new.event':` block in `webhooks.py`
2. Update signer status as needed
3. Create `ws_event` dict for WebSocket broadcast
4. Update `ESIGNING.md`

### Test webhook locally
```bash
curl -X POST http://localhost:8000/api/v1/esigning/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"event_type": "form.completed", "data": {"submission_id": "123", "submitter": {"id": "456", "name": "Test", "completed_at": "2024-01-01T00:00:00Z"}}}'
```
