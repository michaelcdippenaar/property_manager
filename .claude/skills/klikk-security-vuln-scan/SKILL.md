---
name: klikk-security-vuln-scan
description: >
  Scan the Django codebase for specific vulnerability patterns: SQL injection, XSS, CSRF bypass,
  insecure deserialization, IDOR, mass assignment, broken access control, sensitive data in logs.
  Trigger for: "vulnerability scan", "vuln scan", "find vulnerabilities", "code scan", "SAST",
  "static analysis", "injection check", "XSS check", "IDOR scan", "mass assignment check".
---

# Vulnerability Pattern Scanner — Tremly

You are a static application security testing (SAST) engine. Systematically scan the Tremly Django/DRF codebase for vulnerability patterns. Use Grep and Read to search for each pattern.

## Scan Procedure

Execute each scan category below. For each finding, record the file path, line number, code snippet, severity, and remediation.

### Category 1: SQL Injection (OWASP A03:2021)
Search `backend/` for these patterns:
- `raw(` — Raw SQL queries
- `.extra(` — Deprecated extra() with potential injection
- `RawSQL` — Raw SQL expressions
- `cursor.execute` — Direct cursor execution
- String formatting in queries: `%s.*%`, `.format(.*query`, `f".*SELECT`, `f".*INSERT`, `f".*UPDATE`, `f".*DELETE`

Also check:
- `core/contract_rag.py` for injection via ChromaDB queries
- Any management commands that accept user input

### Category 2: Cross-Site Scripting (OWASP A03:2021)
Search for:
- `mark_safe` — Marking strings as safe HTML
- `__html__` — Custom HTML rendering
- `|safe` — Template safe filter
- `SafeData` — Safe data marking
- `format_html` with user input
- `content_html` — Check lease template HTML rendering

Check if `content_html` from LeaseTemplate is rendered without sanitization in `backend/apps/leases/template_views.py` and `backend/apps/esigning/services.py`.

### Category 3: CSRF Bypass
Search for:
- `csrf_exempt` or `@csrf_exempt`
- Identify all CSRF-exempt views
- Verify CSRF-exempt views have alternative authentication (HMAC, token)
- Webhooks are expected to be CSRF-exempt but verify they have signature verification

### Category 4: Insecure Deserialization
Search for:
- `pickle.` — Pickle deserialization
- `yaml.load(` without SafeLoader
- `yaml.unsafe_load`
- `eval(` — Code evaluation
- `exec(` — Code execution
- `__import__` — Dynamic imports
- `marshal.loads` — Marshal deserialization

Check file upload handlers — Excel import uses `openpyxl`, verify it's safe against XXE/zip bombs.

### Category 5: IDOR / Broken Access Control (OWASP A01:2021)
For EVERY ViewSet and APIView in `backend/apps/*/views.py`:
1. Read each `get_queryset()` method
2. Check if it filters by `request.user` or user's role
3. Check `get_object()` overrides for ownership validation
4. Flag any that return unfiltered querysets

Key views to check:
- `PropertyViewSet` — fallback `Property.objects.all()` for non-agent/admin users
- `UnitViewSet` — no user filtering
- `UnitInfoViewSet` — no user filtering
- `PropertyAgentConfigViewSet` — no user filtering
- `PersonViewSet` — `Person.objects.all()` (any user can list all people)
- `PersonDetailView` — any user can read/update any person
- `TenantsListView` — any authenticated user can list all tenants
- Owner/supplier views — verify role checks

### Category 6: Mass Assignment
For EVERY serializer in `backend/apps/*/serializers.py`:
1. Check if `fields = '__all__'` is used
2. Check if sensitive fields are in `read_only_fields`
3. Check `UserSerializer` — is `role` writable? Is `is_staff`/`is_superuser` exposed?
4. Check `PersonSerializer` — is `linked_user` writable by anyone?

### Category 7: Sensitive Data in Logs/Responses
Search for:
- `logger.*(info|debug|warning|error).*password`
- `logger.*token`
- `logger.*secret`
- `logger.*api_key`
- `print(.*password`
- `print(.*token`

Also check:
- Chat log files (JSONL) for PII content
- API error responses for stack traces
- Serializers returning sensitive fields that should be hidden

### Category 8: Broken Authentication Patterns
Search for:
- `AllowAny` — List every endpoint and verify each has a legitimate reason
- `permission_classes = []` — Empty permission classes
- `authentication_classes = []` — Disabled authentication

Expected AllowAny endpoints: Login, Register, OTP, Webhooks, Public signing links, Supplier quote views.
Flag any unexpected AllowAny endpoints.

### Category 9: Hardcoded Secrets & Credentials
Search for:
- `password\s*=\s*["']` — Hardcoded passwords
- `secret\s*=\s*["']` — Hardcoded secrets
- `api_key\s*=\s*["']` — Hardcoded API keys
- `default.*secret` — Default secret values
- `dev-secret` — Development secrets that could leak to production

Check `.env.example` for any actual secret values.

### Category 10: File Upload Vulnerabilities
Search for:
- `upload_to` — File upload destinations
- `FileField` / `ImageField` — File field definitions
- `request.FILES` — File handling in views
- `MultiPartParser` — Multipart upload handling

Check:
- File type validation (extension-only vs content-type)
- Path traversal in upload filenames
- File size limits configured
- Uploaded files served with proper Content-Disposition headers
- Excel import in maintenance views — malicious XLSX protection

### Category 11: MCP Server Security
Read `backend/mcp_server/server.py` completely. Check:
- Authentication on any tool or resource (likely none)
- Write access tools (lease template create/update, chat posting)
- PII exposure (email, phone, name, role, chat content)
- Rate limiting
- Input validation on parameters

Severity: CRITICAL if MCP server is network-accessible without authentication.

## Output Format

```
# Vulnerability Scan Report
Date: [date]
Scan scope: backend/**/*.py

## Findings Summary
| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| SQL Injection | 0 | 0 | 0 | 0 |
| XSS | ... | ... | ... | ... |
| CSRF Bypass | ... | ... | ... | ... |
| Insecure Deserialization | ... | ... | ... | ... |
| IDOR | ... | ... | ... | ... |
| Mass Assignment | ... | ... | ... | ... |
| Sensitive Data Leak | ... | ... | ... | ... |
| Broken Auth | ... | ... | ... | ... |
| Hardcoded Secrets | ... | ... | ... | ... |
| File Upload | ... | ... | ... | ... |
| MCP Server | ... | ... | ... | ... |

## Detailed Findings

### [VULN-001] Title
- **Severity**: CRITICAL/HIGH/MEDIUM/LOW
- **Category**: OWASP A0X — Name
- **File**: path/to/file.py:line
- **Code**:
  ```python
  [vulnerable code snippet]
  ```
- **Impact**: [what an attacker can do]
- **Remediation**: [specific fix with code]
- **CVSS Estimate**: X.X

## False Positives Reviewed
[List items you checked but determined are not vulnerabilities]
```

## References
- OWASP Top 10 (2021): https://owasp.org/Top10/
- CWE Database: https://cwe.mitre.org/
- Django Security: https://docs.djangoproject.com/en/5.0/topics/security/
