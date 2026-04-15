# Vulnerability Scan Categories

---

## Category 1: SQL Injection (OWASP A03)
Search `backend/` for:
- `raw(` — Raw SQL queries
- `.extra(` — Deprecated extra() with potential injection
- `RawSQL` — Raw SQL expressions
- `cursor.execute` — Direct cursor execution
- String formatting in queries: `%s.*%`, `.format(.*query`, `f".*SELECT`, `f".*INSERT`, `f".*UPDATE`, `f".*DELETE`

Also check: `core/contract_rag.py` for ChromaDB injection; management commands that accept user input.

---

## Category 2: Cross-Site Scripting (OWASP A03)
Search for: `mark_safe`, `__html__`, `|safe`, `SafeData`, `format_html` with user input, `content_html`

Check if `content_html` from LeaseTemplate is rendered without sanitization in:
- `backend/apps/leases/template_views.py`
- `backend/apps/esigning/services.py`

---

## Category 3: CSRF Bypass
Search for: `csrf_exempt`, `@csrf_exempt`

Identify all CSRF-exempt views. Verify each has alternative auth (HMAC, token). Webhooks expected to be CSRF-exempt but must have signature verification.

---

## Category 4: Insecure Deserialization
Search for: `pickle.`, `yaml.load(` without SafeLoader, `yaml.unsafe_load`, `eval(`, `exec(`, `__import__`, `marshal.loads`

Check file upload handlers — Excel import uses `openpyxl`, verify safe against XXE/zip bombs.

---

## Category 5: IDOR / Broken Access Control (OWASP A01)
For EVERY ViewSet and APIView in `backend/apps/*/views.py`:
1. Read each `get_queryset()` method
2. Check if it filters by `request.user` or user's role
3. Check `get_object()` overrides for ownership validation
4. Flag any that return unfiltered querysets

Key views to check:
- `PropertyViewSet` — fallback `Property.objects.all()` for non-agent/admin users
- `UnitViewSet` — no user filtering
- `PersonViewSet` — `Person.objects.all()` (any user can list all people)
- `PersonDetailView` — any user can read/update any person
- `TenantsListView` — any authenticated user can list all tenants

---

## Category 6: Mass Assignment
For EVERY serializer in `backend/apps/*/serializers.py`:
1. Check if `fields = '__all__'` is used
2. Check if sensitive fields are in `read_only_fields`
3. Check `UserSerializer` — is `role` writable? Is `is_staff`/`is_superuser` exposed?
4. Check `PersonSerializer` — is `linked_user` writable by anyone?

---

## Category 7: Sensitive Data in Logs/Responses
Search for: `logger.*(info|debug|warning|error).*password`, `logger.*token`, `logger.*secret`, `logger.*api_key`, `print(.*password`, `print(.*token`

Also check: chat log JSONL files for PII; API error responses for stack traces; serializers returning sensitive fields.

---

## Category 8: Broken Authentication Patterns
Search for: `AllowAny`, `permission_classes = []`, `authentication_classes = []`

Expected AllowAny: Login, Register, OTP, Webhooks, Public signing links, Supplier quote views.
Flag any unexpected AllowAny endpoints.

---

## Category 9: Hardcoded Secrets & Credentials
Search for: `password\s*=\s*["']`, `secret\s*=\s*["']`, `api_key\s*=\s*["']`, `default.*secret`, `dev-secret`

Check `.env.example` for any actual secret values.

---

## Category 10: File Upload Vulnerabilities
Search for: `upload_to`, `FileField`, `ImageField`, `request.FILES`, `MultiPartParser`

Check:
- File type validation (extension-only vs content-type)
- Path traversal in upload filenames
- File size limits configured
- `Content-Disposition` headers for file downloads
- Excel import in maintenance views — malicious XLSX protection

---

## Category 11: MCP Server Security
Read `backend/mcp_server/server.py` completely. Check:
- Authentication on any tool or resource (likely none)
- Write access tools (lease template create/update, chat posting)
- PII exposure (email, phone, name, role, chat content)
- Rate limiting; input validation on parameters

Severity: CRITICAL if MCP server is network-accessible without authentication.
