# DocuSeal e-signing — Vue admin integration

This document describes how the **Tremly / Klikk admin SPA** (Vue 3) integrates with the e-signing backend and DocuSeal: **staff flows** inside authenticated lease UI and **passwordless signing** for external signers on a public route. For the full API contract, webhooks, models, and server behaviour, see [ESIGNING.md](ESIGNING.md). For the tenant mobile app, see [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md).

---

## 1. What the Vue app is responsible for

| Concern | Handled by backend | Handled by Vue |
|---------|-------------------|----------------|
| PDF generation from lease | Yes | No |
| DocuSeal template + submission | Yes | No |
| Webhook processing | Yes | No |
| Create/list submissions for a lease | Yes (API) | Yes (calls API) |
| Resend DocuSeal invitation email | Yes | Yes (button) |
| UUID “public” signing link | Yes (creates `ESigningPublicLink`) | Yes (Copy link / Email link) |
| Resolve UUID → `embed_src` (no login) | Yes (`GET /public-sign/<uuid>/`) | Yes (`PublicSignView`) |
| Embed DocuSeal UI | N/A | iframe (`PublicSignView`) |

The admin SPA is a **single Vue application** (`admin/`). Signers are **not** sent to a separate micro-frontend; they open the same deployed app on route **`/sign/:token`**, which is marked **public** so no JWT is required.

---

## 2. Codebase map (Vue)

All paths are under **`admin/src/`** unless noted.

| Concern | Location |
|---------|----------|
| Axios client (Bearer token, refresh) | `api.ts` |
| API base URL | `import.meta.env.VITE_API_URL` (fallback `http://localhost:8000/api/v1`) |
| Router + public `/sign/:token` | `router/index.ts` |
| Passwordless signing page (no auth) | `views/signing/PublicSignView.vue` |
| Lease signing UI (list, create, resend, public link) | `views/leases/ESigningPanel.vue` |
| Where the panel is mounted | `views/leases/EditLeaseDrawer.vue` (prop `leaseId`, optional `leaseTenants`) |

---

## 3. Router and authentication

### 3.1 Public signing route

```ts
{
  path: '/sign/:token',
  name: 'public-sign',
  component: () => import('../views/signing/PublicSignView.vue'),
  meta: { public: true, allowWhenAuthenticated: true },
}
```

- **`public: true`** — The global `beforeEach` guard does **not** redirect unauthenticated users to `/login`.
- **`allowWhenAuthenticated: true`** — If a user **is** logged in (e.g. staff testing the link), they are **not** redirected to their role home; they stay on `/sign/:token`. Other public routes like `/login` still bounce authenticated users away.

### 3.2 Staff e-signing

Lease signing management lives under the main **`AppLayout`** tree (`meta.requiresAuth: true`, roles `agent` / `admin`). The panel itself does not register a top-level route; it is embedded in the lease edit drawer.

---

## 4. `PublicSignView.vue` (signer-facing)

### 4.1 Purpose

A minimal full-screen page: load signing context by UUID, then show DocuSeal in an **iframe** via `embed_src`.

### 4.2 Data loading

On mount, the view reads **`route.params.token`** and calls:

```http
GET {VITE_API_URL}/esigning/public-sign/{token}/
```

**No `Authorization` header** — plain `axios` is used here (not the shared `api` instance), so localStorage tokens are not attached.

### 4.3 Successful response (JSON)

The backend returns (among other fields):

| Field | Use in UI |
|-------|-----------|
| `embed_src` | `iframe` `src` |
| `document_title` | Header subtitle (lease/property label) |
| `signer_name` | Header line |
| `signer_email` | Header line |

Other fields (`submission_status`, `signer_status`) are available for future UI but are not required for embedding.

### 4.4 Errors

- **404** — Invalid token, unknown link, or signing not ready (`embed_src` missing).
- **410** — Link expired, submission finished, or signer already completed/declined.

The view maps `response.data.detail` (string) to a user-visible message when present.

### 4.5 Configuration notes

- **`VITE_API_URL`** must match the Django API the browser can reach (CORS allowed). If unset, the fallback is `http://localhost:8000/api/v1`.
- Signers often open the link on **mobile**; the iframe uses a large min-height (`min-h-[70vh]`) and `allow="clipboard-write"` for DocuSeal field behaviour.

---

## 5. `ESigningPanel.vue` (staff-facing)

### 5.1 Where it appears

Embedded in **`EditLeaseDrawer.vue`**, with:

- **`leaseId`** — Filters and creates submissions for that lease.
- **`leaseTenants`** (optional) — Pre-populates the “Send for Signing” modal from tenant records.

### 5.2 List submissions

```http
GET /esigning/submissions/?lease_id={leaseId}
```

Uses the authenticated **`api`** client. Response may be paginated (`results`) or a plain array; the panel normalises with `data.results ?? data`.

### 5.3 Create submission

```http
POST /esigning/submissions/
```

Body:

```json
{
  "lease_id": <number>,
  "signers": [ { "name", "email", "phone", "role", "send_email", ... } ]
}
```

The modal requires every signer to have **name** and **email**. Optional checkboxes:

- **Send invitation email** — `send_email` per signer (DocuSeal-side invitation when the backend forwards it).
- **Save contact to tenant record** — For rows tied to `personId`, the panel may `PATCH /auth/persons/{id}/` before creating the submission.

On success, the new submission is prepended to the list and the drawer can emit **`signed`** (parent refreshes lease state as needed).

### 5.4 Resend (DocuSeal email)

```http
POST /esigning/submissions/{id}/resend/
{ "submitter_id": <DocuSeal submitter id> }
```

`submitter_id` is the numeric **`signers[].id`** from the submission payload (same id used for public links).

### 5.5 Public link — Copy

```http
POST /esigning/submissions/{id}/public-link/
{ "submitter_id": <id> }
```

Response **`201`** includes:

| Field | Meaning |
|-------|---------|
| `uuid` | Same as URL token |
| `sign_path` | e.g. `/sign/{uuid}/` |
| `signing_url` | Absolute URL if `SIGNING_PUBLIC_APP_BASE_URL` is set or `public_app_origin` was sent |
| `email_sent` | `false` when not emailing |

The panel builds the clipboard string as:

`data.signing_url || (window.location.origin + (data.sign_path || '/sign/' + data.uuid + '/'))`

Then **`navigator.clipboard.writeText`**. A short green hint explains paste-to-SMS/email.

### 5.6 Public link — Email (notifications app)

```http
POST /esigning/submissions/{id}/public-link/
{
  "submitter_id": <id>,
  "send_email": true,
  "public_app_origin": "<window.location.origin>"
}
```

- **`public_app_origin`** — Ensures the email contains an **absolute** URL when `SIGNING_PUBLIC_APP_BASE_URL` is empty. Must be the real origin signers will open (scheme + host + port), no trailing slash.
- **UI** — “Email link” is only shown when **`signer.email`** is present and submission is not **`completed`**.
- **Success** — `data.email_sent === true` → green hint.
- **Partial failure** — `201` with `email_sent: false` and `email_error` → error banner; staff can use **Copy link**.
- **Hard failure** — **`400`** if the server cannot build an absolute URL (no base URL and no usable origin) or signer has no email.

Email is sent via **`apps.notifications.services.send_email`** (Django SMTP, etc.); operational detail is in [NOTIFICATIONS_APP.md](../../notifications/system_documentation/NOTIFICATIONS_APP.md).

### 5.7 Permissions

Creating public links, resending, and creating submissions require an authenticated user who passes **`can_manage_esigning`** on the server (admin/agent with appropriate lease scope). Tenants cannot call these endpoints; see [ESIGNING.md](ESIGNING.md).

---

## 6. How the URL in the email relates to Vue

1. Staff generates a link (copy or email).
2. The path is always **`/sign/<uuid>/`** on the **admin SPA host**.
3. Production/staging should set **`SIGNING_PUBLIC_APP_BASE_URL`** in Django settings (e.g. `https://admin.example.com`) so emails and API responses use a stable absolute URL even if staff use a different origin when clicking “Email link”.
4. Default link lifetime is **`ESIGNING_PUBLIC_LINK_EXPIRY_DAYS`** (server); optional **`expires_in_days`** (1–90) on the POST body is supported by the API (the Vue panel currently omits it and uses the default).

---

## 7. Comparison with Flutter tenant flow

| Aspect | Vue `PublicSignView` | Flutter tenant signing |
|--------|----------------------|-------------------------|
| Auth | None (UUID link) | JWT (tenant) |
| Embed | iframe | `WebView` |
| Resolve URL | `GET /public-sign/<uuid>/` | N/A (uses `embed_src` from authenticated list/detail) |
| Polling | Not implemented on public page | Polls submission detail until terminal state |

Staff may still open **`embed_src`** inside the authenticated app in future; today the dedicated passwordless path is **`/sign/:token`**.

---

## 8. Operational checklist

1. **Backend** — DocuSeal API key, webhook URL, migrations (including `esigning` and `notifications` if logging email).
2. **Email** — SMTP / `send_test_email` working before relying on “Email link”.
3. **Admin env** — `VITE_API_URL` points at the API the browser can call.
4. **Signing links** — Either `SIGNING_PUBLIC_APP_BASE_URL` or consistent use of `window.location.origin` when emailing.
5. **CORS** — Django must allow the admin origin for `GET`/`POST` esigning endpoints as used by the SPA.

---

## 9. Related tests

Backend regression tests for public links and email flags live in **`apps/esigning/tests/test_esigning.py`** (e.g. `ESigningPublicLinkTests`). Run:

```bash
python manage.py test apps.esigning.tests.test_esigning.ESigningPublicLinkTests -v 2
```

---

## 10. See also

- [ESIGNING.md](ESIGNING.md) — Endpoints, request/response shapes, webhooks, status model.
- [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md) — Tenant app WebView + polling.
- [NOTIFICATIONS_APP.md](../../notifications/system_documentation/NOTIFICATIONS_APP.md) — Email delivery and `NotificationLog`.
