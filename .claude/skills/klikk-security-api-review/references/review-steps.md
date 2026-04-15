# API Security Review — Steps

---

## Step 1: Complete Endpoint Inventory

Read ALL URL configuration files:
- `backend/config/urls.py` — Root URL conf
- `backend/apps/accounts/urls.py`
- `backend/apps/properties/urls.py`
- `backend/apps/leases/urls.py`
- `backend/apps/maintenance/urls.py`
- `backend/apps/esigning/urls.py`
- `backend/apps/tenant_portal/urls.py`

For each endpoint document:
| Method | Path | View | Auth | Throttle | Role Check |
|--------|------|------|------|----------|------------|

---

## Step 2: Authentication Requirements

For each endpoint verify:
1. Is authentication required? (`IsAuthenticated` vs `AllowAny`)
2. If `AllowAny`, is there an alternative mechanism (token, HMAC, UUID)?
3. Are there endpoints that should require auth but don't?

**Known AllowAny endpoints (expected):**
- `POST /api/v1/auth/register/` — needs rate limiting
- `POST /api/v1/auth/login/` — needs rate limiting
- `POST /api/v1/auth/otp/send/` — needs rate limiting
- `POST /api/v1/auth/otp/verify/` — needs rate limiting
- `GET/POST /api/v1/maintenance/quote/<token>/` — token-based, verify UUID
- `POST /api/v1/esigning/webhook/` — HMAC-verified (check implementation)
- `GET /api/v1/esigning/public-sign/<uuid>/` — UUID-based
- `GET /graphql/` — `graphiql=settings.DEBUG`, verify no auth bypass

Flag any `AllowAny` endpoints NOT in this list.

---

## Step 3: Rate Limiting Audit

Search for `throttle_classes` in all views. Document current state.

Required throttle configuration:
- Auth endpoints: `AuthRateThrottle` — 5/min anon
- OTP endpoints: `OTPRateThrottle` — 3/min anon
- Default user throttle: 100/hour
- File upload endpoints: lower limits
- API-wide default anon: 30/hour

---

## Step 4: Input Validation

For each endpoint accepting user input:
1. **Serializer validation** — proper types, lengths, regex?
2. **Query parameter injection** — `filterset_fields` safe? ORM lookup injection?
3. **File uploads** — type validation, size limits, malicious file protection
4. **Search inputs** — `SearchFilter` and `__icontains` safe?
5. **Nested writes** — can users create/modify related objects they shouldn't?

Specific checks:
- `MaintenanceRequest` creation — can a tenant set `supplier` or `status` directly?
- `LeaseViewSet` — can a user modify lease financial terms?
- `PropertyAgentConfig` — can anyone modify AI agent configuration?
- Supplier Excel import — `openpyxl` safe against XXE/zip bombs?

---

## Step 5: Response Data Leakage

For each serializer, check if responses include:
1. Internal IDs that shouldn't be exposed
2. Related object data that leaks other users' info
3. Sensitive fields (`id_number`, bank details, API keys)
4. Error messages that reveal system internals

Specific checks:
- `PersonSerializer` — exposes `id_number`, `company_reg`, `vat_number` to any authenticated user?
- `UserSerializer` — what data is in login/register responses?
- Maintenance request responses — do they leak tenant PII to suppliers?

---

## Step 6: CORS Configuration

Read `backend/config/settings/base.py` CORS settings. Check:
- `CORS_ALLOW_ALL_ORIGINS` — must be `False` in production
- `CORS_ALLOW_CREDENTIALS` — if `True`, origin must be explicit (never wildcard)
- Production CORS config — explicit allowed origins list
- `CORS_ALLOW_HEADERS` — are custom headers restricted?
- `CORS_ALLOW_METHODS` — restrict to needed methods only

---

## Step 7: Webhook Security

Review ALL webhook receivers:

1. **DocuSeal/native signing webhook** (`backend/apps/esigning/webhooks.py`):
   - Is HMAC verification enforced or bypassed when secret is empty?
   - Is the webhook idempotent? Can replaying cause double-processing?

2. Search for other `csrf_exempt` + `AllowAny` to find webhook-like endpoints.

---

## Step 8: GraphQL Security

Read GraphQL schema and configuration files. Check:
1. **Introspection** — disabled in production?
2. **Authentication** — GraphQL endpoint requires auth?
3. **Query depth** — depth limiting to prevent resource exhaustion?
4. **Batching** — can attacker batch thousands of queries in one request?
5. **Authorization** — resolvers check permissions?
6. **Mutations** — what write operations are exposed? Permission-checked?

---

## Step 9: MCP Server Security

Read `backend/mcp_server/server.py` completely. Check:
- Authentication layer (likely none)
- Direct database access via Django ORM
- READ access: tenant chat sessions, intelligence profiles, maintenance requests, lease templates
- WRITE access: lease templates (create/update), maintenance chat messages
- PII exposure: email, phone, name, role, chat content

Severity: **CRITICAL** if MCP server is network-accessible without authentication.

Required hardening:
1. Add authentication (API key, mutual TLS, or JWT)
2. Add authorization (role-based tool access)
3. Audit logging for all tool invocations
4. Rate limiting
5. Input validation on all parameters

---

## Step 10: Static/Media File Security

Check:
1. `static()` in urls.py — gated by `DEBUG`?
2. Media files (uploaded documents, photos) — served with auth checks?
3. Are signed PDFs, supplier documents, tenant photos publicly accessible by URL?
4. `Content-Disposition` headers set for file downloads?
