---
name: klikk-security-vuln-scan
description: >
  Scan the Django codebase for specific vulnerability patterns: SQL injection, XSS, CSRF bypass,
  insecure deserialization, IDOR, mass assignment, broken access control, sensitive data in logs.
  Trigger for: "vulnerability scan", "vuln scan", "find vulnerabilities", "code scan", "SAST",
  "static analysis", "injection check", "XSS check", "IDOR scan", "mass assignment check".
---

# Vulnerability Pattern Scanner — Tremly

SAST engine for the Tremly Django/DRF codebase. Use Grep and Read to check each category. Record file, line, code snippet, severity, and remediation for every finding.

## 11 Scan Categories

Read [scan-categories.md](references/scan-categories.md) for all grep patterns, specific files to audit, and known-vulnerable views for each category.

| # | Category | OWASP | Key Patterns |
|---|----------|-------|--------------|
| 1 | SQL Injection | A03 | `raw(`, `cursor.execute`, `RawSQL`, `f".*SELECT` |
| 2 | XSS | A03 | `mark_safe`, `\|safe`, `SafeData`, `content_html` |
| 3 | CSRF Bypass | A01 | `csrf_exempt` — verify HMAC on each |
| 4 | Insecure Deserialization | A08 | `pickle.`, `yaml.load(`, `eval(`, `exec(` |
| 5 | IDOR / Access Control | A01 | Every `get_queryset()` — filter by user? |
| 6 | Mass Assignment | A04 | `fields = '__all__'`, `role` writable in UserSerializer |
| 7 | Sensitive Data in Logs | A09 | `logger.*password`, `logger.*token`, JSONL chat files |
| 8 | Broken Auth Patterns | A07 | `AllowAny`, `permission_classes = []` |
| 9 | Hardcoded Secrets | A02 | `password\s*=\s*["']`, `dev-secret` |
| 10 | File Upload | A01 | `upload_to`, `request.FILES` — type + size checks |
| 11 | MCP Server Security | A07 | `backend/mcp_server/server.py` — no auth = CRITICAL |

## Output Format

```
# Vulnerability Scan Report
Date: [date]
Scan scope: backend/**/*.py

## Findings Summary
| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| SQL Injection | 0 | 0 | 0 | 0 |
...

## Detailed Findings

### [VULN-001] Title
- **Severity**: CRITICAL/HIGH/MEDIUM/LOW
- **Category**: OWASP A0X — Name
- **File**: path/to/file.py:line
- **Code**: [snippet]
- **Impact**: [what an attacker can do]
- **Remediation**: [specific fix with code]
- **CVSS Estimate**: X.X

## False Positives Reviewed
[Items checked but not vulnerable]
```
