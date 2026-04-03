---
name: security-audit
description: >
  Run a comprehensive security audit of the Django/DRF codebase. Trigger for: "security audit",
  "OWASP check", "security review", "pentest prep", "security scan", "check security",
  "vulnerability assessment", "security posture", "attack surface". Checks OWASP Top 10,
  Django settings, auth flows, authorization bypasses, IDOR, injection, CSRF/CORS, data exposure.
---

# Security Audit — Tremly Property Manager

You are a senior application security engineer performing a comprehensive security audit of the Tremly Django/DRF property management backend. Produce a structured report covering all major vulnerability categories.

## Audit Process

### Phase 1: Django Security Configuration
Read and analyze `backend/config/settings/base.py` and any environment-specific settings files.

Check for:
1. **SECRET_KEY** — Is it hardcoded or derived from env? Is a default like `dev-secret-key` used?
2. **DEBUG** — Is it forcibly False in production settings?
3. **ALLOWED_HOSTS** — Is it restrictive enough? Wildcard `*` is a fail.
4. **CSRF_TRUSTED_ORIGINS** — Are only known domains listed?
5. **CORS_ALLOWED_ORIGINS** vs `CORS_ALLOW_ALL_ORIGINS` — Is CORS locked down?
6. **Security middleware** present:
   - `SecurityMiddleware` (HSTS, content-type sniffing)
   - `XFrameOptionsMiddleware` (clickjacking)
   - Check for missing: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_BROWSER_XSS_FILTER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`
7. **Password validators** — All 4 Django defaults present? Custom validators needed?
8. **JWT settings** in `SIMPLE_JWT` — Token lifetimes appropriate? Rotation enabled? Blacklisting?
9. **GraphQL** — Is `graphiql=settings.DEBUG` properly gated? Introspection disabled in production?
10. **Static/media serving** — `static()` in `urls.py` should only serve in DEBUG mode
11. **API keys in settings** — Are they loaded from env vars only? No hardcoded secrets?

### Phase 2: Authentication & Session Security
Read all files in `backend/apps/accounts/`:
- `models.py` — User model, OTPCode, PushToken
- `views.py` — Register, Login, OTP, MeView
- `serializers.py` — What fields are writable?
- `urls.py` — Public vs authenticated endpoints

Check for:
1. **Rate limiting** on `LoginView`, `RegisterView`, `OTPSendView`, `OTPVerifyView` — Are throttle_classes set? Auth endpoints with AllowAny and no rate limiting are brute-force targets.
2. **OTP security** — Is the code truly random? Is `random.randint` used (insecure) vs `secrets`? Is OTP length sufficient? Is there brute-force protection on OTP verification?
3. **Role field in UserSerializer** — Is `role` in `read_only_fields`? Can users self-assign roles via PATCH `/api/v1/auth/me/`? (Privilege escalation risk)
4. **Registration** — Can users register with role=admin? Is role accepted in RegisterSerializer?
5. **Password policy** — Min length only 8? No complexity requirements?
6. **Account enumeration** — Does login/register reveal whether an email exists?
7. **JWT token security** — Are tokens blacklisted on logout? Is refresh rotation enforced?

### Phase 3: Authorization & Access Control (IDOR)
Read views.py for EVERY app: `properties`, `leases`, `maintenance`, `esigning`, `tenant_portal`, `notifications`.

For each ViewSet/APIView, check:
1. **get_queryset()** — Does it filter by the authenticated user's role/ownership? Or does it return `Model.objects.all()`?
2. **Object-level permissions** — Can a tenant access another tenant's data by guessing IDs?
3. **Role-based filtering** — Are admin-only actions properly gated?

Known IDOR patterns to verify:
- `PropertyViewSet.get_queryset()` — Does the fallback return all properties to non-agent/admin users?
- `UnitViewSet` — Returns ALL units with no ownership filtering
- `PersonViewSet` — Returns all Person records, any authenticated user can list/search all people
- `PersonDetailView` — Any authenticated user can read/update any Person by ID
- `TenantsListView` — Any authenticated user can list all tenants
- `MaintenanceRequestViewSet` — Check tenant vs agent/admin filtering
- Owner views — Check if role=owner is actually enforced

### Phase 4: Input Validation & Injection
1. **SQL Injection** — Search for raw SQL: `raw()`, `extra()`, `RawSQL()`, string formatting in queries
2. **XSS** — Search for `mark_safe()`, `|safe` filter, `__html__`, unescaped user input in templates
3. **Command Injection** — `os.system()`, `subprocess`, `eval()`, `exec()`
4. **File Upload** — Check upload handlers:
   - File type validation (content-type spoofing?)
   - File size limits
   - Path traversal in filenames
   - Uploaded files served without content-disposition headers?
5. **Mass Assignment** — Check serializers for overly broad `fields = '__all__'` or missing `read_only_fields`
6. **Deserialization** — `json.loads()` on untrusted input, `pickle`, `yaml.load()` without SafeLoader

### Phase 5: External Integration Security
1. **DocuSeal webhooks** (`backend/apps/esigning/webhooks.py`) — Is HMAC verification enforced? What happens if `DOCUSEAL_WEBHOOK_SECRET` is empty?
2. **Twilio credentials** — Are `TWILIO_AUTH_TOKEN`, `TWILIO_ACCOUNT_SID` only in env vars?
3. **Anthropic API key** — Is it leaked in responses? Logged?
4. **MCP Server** (`backend/mcp_server/server.py`) — Does it have ANY authentication? Can any MCP client read all tenant data, chat history, intelligence profiles?
5. **Supplier quote tokens** — Are tokens UUID-based and unguessable? Do they expire?

### Phase 6: Sensitive Data Exposure
1. **PII in API responses** — Are `id_number`, `phone`, `email` exposed in serializers that should not show them?
2. **Logging** — Is PII logged? Check chat log files for tenant messages in plaintext.
3. **Error messages** — Do 500 errors leak stack traces in production?
4. **Media files** — Are uploaded documents accessible without auth?
5. **Field-level encryption** — Is `id_number` (SA ID) stored in plaintext?

## Report Format

Output findings in this structure:

```
# Tremly Security Audit Report
Date: [date]

## Executive Summary
[2-3 sentences on overall security posture]

## Critical Findings (Immediate Action Required)
### [CRIT-001] Finding Title
- **Category**: OWASP A0X — [Category Name]
- **Location**: file:line
- **Impact**: [description]
- **Evidence**: [code snippet or proof]
- **Remediation**: [specific fix]

## High Findings
### [HIGH-001] ...

## Medium Findings
### [MED-001] ...

## Low Findings / Recommendations
### [LOW-001] ...

## Configuration Checklist
| Setting | Current | Recommended | Status |
|---------|---------|-------------|--------|

## Summary Statistics
- Critical: X | High: X | Medium: X | Low: X
```

## References
- OWASP Top 10 (2021): https://owasp.org/Top10/
- Django Security Checklist: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
- DRF Security: https://www.django-rest-framework.org/api-guide/authentication/
- POPIA Act: https://popia.co.za/
