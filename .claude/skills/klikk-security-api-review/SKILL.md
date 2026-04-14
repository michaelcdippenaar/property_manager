---
name: klikk-security-api-review
description: >
  Review API endpoints for security: authentication, rate limiting, input validation, response data
  leakage, CORS, webhook security, GraphQL exposure. Trigger for: "API security", "endpoint review",
  "API audit", "rate limiting review", "CORS review", "webhook security", "GraphQL security",
  "API hardening", "endpoint security", "input validation review", "response leakage".
---

# API Security Review — Tremly

You are an API security specialist reviewing all REST and GraphQL endpoints of the Tremly property management platform.

## Review Steps

### Step 1: Complete Endpoint Inventory
Read ALL URL configuration files to build a complete endpoint map:

Files:
- `backend/config/urls.py` — Root URL conf
- `backend/apps/accounts/urls.py`
- `backend/apps/properties/urls.py`
- `backend/apps/leases/urls.py`
- `backend/apps/maintenance/urls.py`
- `backend/apps/esigning/urls.py`
- `backend/apps/tenant_portal/urls.py`

For each endpoint, document:
| Method | Path | View | Auth | Throttle | Role Check |
|--------|------|------|------|----------|------------|

### Step 2: Authentication Requirements
For each endpoint, verify:
1. Is authentication required? (IsAuthenticated vs AllowAny)
2. If AllowAny, is there an alternative auth mechanism (token, HMAC, UUID)?
3. Are there endpoints that should require auth but don't?

**Known AllowAny endpoints to review:**
- `POST /api/v1/auth/register/` — Expected, needs rate limiting
- `POST /api/v1/auth/login/` — Expected, needs rate limiting
- `POST /api/v1/auth/otp/send/` — Expected, needs rate limiting
- `POST /api/v1/auth/otp/verify/` — Expected, needs rate limiting
- `GET/POST /api/v1/maintenance/quote/<token>/` — Token-based, verify token is UUID
- `POST /api/v1/esigning/webhook/` — HMAC-verified (check implementation)
- `GET /api/v1/esigning/public-sign/<uuid>/` — UUID-based
- `GET /graphql/` — Has `graphiql=settings.DEBUG`, verify no auth bypass

### Step 3: Rate Limiting Audit
Search for `throttle_classes` in all views.

Document current state and required additions:
- Auth endpoints: 5/min for anon
- OTP endpoints: 3/min for anon
- API-wide: default user throttle
- File upload endpoints: lower limits

### Step 4: Input Validation
For each endpoint that accepts user input, check:
1. **Serializer validation** — Are fields validated with proper types, lengths, regex?
2. **Query parameter injection** — Are `filterset_fields` safe? Can users inject ORM lookups?
3. **File uploads** — Type validation, size limits, malicious file protection
4. **Search inputs** — Are `SearchFilter` and `__icontains` lookups safe?
5. **Nested writes** — Can users create/modify related objects they shouldn't?

Specific checks:
- `MaintenanceRequest` creation — Can a tenant set `supplier` or `status` directly?
- `LeaseViewSet` — Can a user modify lease financial terms?
- `PropertyAgentConfig` — Can anyone modify AI agent configuration?
- Supplier Excel import — Is `openpyxl` safe against XXE/zip bombs?

### Step 5: Response Data Leakage
For each serializer, check if responses include:
1. Internal IDs that shouldn't be exposed
2. Related object data that leaks other users' info
3. Sensitive fields (id_number, bank details, API keys)
4. Error messages that reveal system internals

Check specifically:
- `PersonSerializer` — Exposes `id_number`, `company_reg`, `vat_number` to any authenticated user?
- `UserSerializer` — What data is in login/register responses?
- Maintenance request responses — Do they leak tenant PII to suppliers?

### Step 6: CORS Configuration
Read `backend/config/settings/base.py` CORS settings.

Check for:
- `CORS_ALLOW_ALL_ORIGINS` — Must be False in production
- `CORS_ALLOW_CREDENTIALS` — If True, origin must be explicit (not wildcard)
- Production CORS config — Is there a production settings file with proper origins?
- `CORS_ALLOW_HEADERS` — Are custom headers restricted?
- `CORS_ALLOW_METHODS` — Should restrict to needed methods only

### Step 7: Webhook Security
Review ALL webhook receivers:

1. **DocuSeal webhook** (`backend/apps/esigning/webhooks.py`):
   - Is HMAC verification enforced or bypassed when secret is empty?
   - Is the webhook idempotent? Can replaying a webhook cause double-processing?

2. Search for other `csrf_exempt` and `AllowAny` to find webhook-like endpoints.

### Step 8: GraphQL Security
Read GraphQL schema and configuration files.

Check:
1. **Introspection** — Is introspection disabled in production?
2. **Authentication** — Does the GraphQL endpoint require authentication?
3. **Query depth** — Is there query depth limiting to prevent resource exhaustion?
4. **Batching** — Can an attacker batch thousands of queries in one request?
5. **Authorization** — Are GraphQL resolvers checking permissions?
6. **Mutations** — What write operations are exposed? Are they permission-checked?

### Step 9: MCP Server Security
Read `backend/mcp_server/server.py` completely.

Check:
- Authentication layer (likely none)
- Direct database access via Django ORM
- READ access: tenant chat sessions, intelligence profiles, maintenance requests, lease templates
- WRITE access: lease templates (create/update), maintenance chat messages
- PII exposure: email, phone, name, role, chat content

Security requirements:
1. Add authentication (API key, mutual TLS, or JWT)
2. Add authorization (role-based tool access)
3. Audit logging for all tool invocations
4. Rate limiting
5. Input validation on all parameters

### Step 10: Static/Media File Security
Check:
1. `static()` in urls.py — Is it gated by DEBUG?
2. Media files (uploaded documents, photos) — Are they served with auth checks?
3. Are signed PDFs, supplier documents, tenant photos publicly accessible if URL is known?
4. Are Content-Disposition headers set for file downloads?

## Output Format

```
# API Security Review Report
Date: [date]

## Endpoint Security Matrix
| # | Method | Path | Auth | Throttle | Role | Input Val | Data Leak | Status |
|---|--------|------|------|----------|------|-----------|-----------|--------|
| 1 | POST | /api/v1/auth/login/ | None | None | N/A | OK | OK | FAIL |
| ... |

## Critical Findings
[Detailed findings with remediation]

## Rate Limiting Implementation Plan
[Recommended throttle configuration]

## CORS Hardening Recommendations
[Production CORS config]

## Webhook Security Assessment
[Findings and fixes]

## GraphQL Security Assessment
[Findings and fixes]

## MCP Server Security Assessment
[Findings and fixes]

## Summary
- Total endpoints: X
- Authenticated: X
- Rate limited: X
- Properly authorized: X
- Needs remediation: X
```

## References
- OWASP API Security Top 10: https://owasp.org/API-Security/
- DRF Throttling: https://www.django-rest-framework.org/api-guide/throttling/
- DRF Permissions: https://www.django-rest-framework.org/api-guide/permissions/
- Django CORS Headers: https://github.com/adamchainz/django-cors-headers
