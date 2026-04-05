# Module: esigning

**App path:** `apps/esigning/`
**Domain:** E-signing workflows (DocuSeal), PDF generation (Gotenberg), audit trail, native in-app signing, public signing links.

---

## Models

| Model | Key Fields |
|-------|-----------|
| `ESigningSubmission` | `lease` (FK→Lease), `docuseal_submission_id` (int, nullable), `status` (pending/completed/declined/expired), `signers` (JSON list of signer configs), `signed_pdf_url`, `completed_at`, `created_by` (FK→User), `signing_mode` (docuseal/native) |
| `ESigningAuditEvent` | Immutable audit log. Fields: `submission` (FK→ESigningSubmission), `event_type` (created/viewed/signed/declined/completed/webhook_received), `actor_email`, `ip_address`, `metadata` (JSON), `created_at` |
| `ESigningPublicLink` | `submission` (FK→ESigningSubmission), `signer_role` (tenant/guarantor/landlord), `token` (UUID), `expires_at`, `is_used` |

---

## DocuSeal Integration

**File:** `apps/esigning/services.py`

DocuSeal is a self-hosted or cloud e-signing service. Tremly uses HTML-based templates
with `data-*` attribute field markers.

### Key service functions

| Function | Purpose |
|----------|---------|
| `create_submission(lease, signers)` | POST to DocuSeal API to create a signing submission |
| `generate_lease_html(lease, template)` | Render TipTap template with merge fields resolved → HTML string |
| `extract_editable_merge_fields(html)` | Parse HTML and return list of `{{field}}` tokens |
| `complete_native_signer(submission, signer_role, captured_data)` | Mark a signer complete in native mode without DocuSeal |
| `generate_signed_pdf(submission)` | Call Gotenberg to assemble signed PDF with signature overlays |

### DocuSeal API calls (mock these in tests)

```python
# In tests, patch the HTTP layer:
@patch("apps.esigning.services.requests.post")
@patch("apps.esigning.services.requests.get")
```

### Webhook

`apps/esigning/webhooks.py` — `POST /api/v1/esigning/webhook/`

DocuSeal sends webhook events when:
- A submission is created, viewed, signed, or completed
- A signer declines

**Validation:** HMAC-SHA256 signature check using `DOCUSEAL_WEBHOOK_SECRET`.
In tests, set `DOCUSEAL_WEBHOOK_SECRET = ""` to disable signature validation,
or mock the HMAC check.

Webhook handler writes an `ESigningAuditEvent` for every event received.

---

## Gotenberg PDF Service

**File:** `apps/esigning/gotenberg.py`

Gotenberg is a Docker sidecar that converts HTML → PDF.

- **URL:** `http://localhost:3000` (configurable via `GOTENBERG_URL` env var)
- **Endpoint used:** `POST /forms/chromium/convert/html`
- Returns raw PDF bytes on success

In tests, mock `apps.esigning.gotenberg.requests.post` to return fake PDF bytes:

```python
@patch("apps.esigning.gotenberg.requests.post")
def test_pdf_generated(self, mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        content=b"%PDF-1.4 fake",
    )
```

---

## Native Signing Flow

When `signing_mode = "native"`, signing happens inside the Tremly app without
redirecting to DocuSeal:

1. `ESigningSubmission` created with `signing_mode="native"`
2. Each signer receives an `ESigningPublicLink` (token-based, no login required)
3. Signer opens public link, views lease HTML, draws/types signature
4. `POST /api/v1/esigning/submissions/{id}/sign/` with `captured_data` (signature image/text)
5. `complete_native_signer()` called → signer marked complete
6. When all signers complete → `generate_signed_pdf()` → submission status `completed`

---

## Public Links

`ESigningPublicLink` allows tenants and guarantors to sign without logging in.
Each link has:
- A unique `token` (UUID)
- An `expires_at` timestamp
- `is_used` flag (prevents reuse)

Endpoint: `GET /api/v1/esigning/public/{token}/` — returns submission info and lease HTML
Endpoint: `POST /api/v1/esigning/public/{token}/sign/` — submit signature

Expired or used tokens must return 400/410.

---

## Audit Trail

Every esigning event is logged to `ESigningAuditEvent` (append-only).
Audit events are written:
- On submission creation
- On each webhook received
- On each native signing step
- On public link access and use

Never delete audit events. Tests should verify an event is created for each action.

---

## Key Invariants

- `ESigningSubmission` must reference a valid `Lease`
- Each `signer_role` must be unique within a submission
- `signing_mode` cannot be changed after submission is created
- `ESigningPublicLink.token` is UUID4, generated once, never regenerated
- Expired public links must be rejected (check `expires_at < now`)
- Already-used public links must be rejected (`is_used=True`)
- HMAC webhook validation is enforced in production; skipped when `DOCUSEAL_WEBHOOK_SECRET=""`

---

## Integration Dependencies

- **DocuSeal API** — external e-signing service (mock in tests)
- **Gotenberg** — PDF generation Docker service (mock in tests)
- **Leases app** — `ESigningSubmission.lease` FK

---

## Known Test Areas

- Submission creation: valid lease → 201; invalid lease → 400
- Webhook: valid HMAC → 200 + audit event created; invalid HMAC → 403
- Webhook: completed event → submission status updated
- Native signing: public link created → sign → submission completed
- Public link: valid token → 200; expired token → 400; used token → 400
- PDF generation: mock Gotenberg → signed PDF URL stored on submission
- Sequential signing: landlord cannot sign before all tenants complete
- Audit events: verify event created for create/view/sign/complete

---

## Coverage Gaps

- `gotenberg.py` unit tests (HTML to PDF conversion, page size, header/footer)
- `ESigningAuditEvent` completeness: verify every action writes an event
- Public link expiry edge cases (exactly at expiry boundary)
- DocuSeal status polling (background job to check submission status)
- Submission cancellation / expiry flow
