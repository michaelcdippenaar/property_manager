---
name: klikk-security-api-review
description: >
  Review API endpoints for security: authentication, rate limiting, input validation, response data
  leakage, CORS, webhook security, GraphQL exposure. Trigger for: "API security", "endpoint review",
  "API audit", "rate limiting review", "CORS review", "webhook security", "GraphQL security",
  "API hardening", "endpoint security", "input validation review", "response leakage".
---

# API Security Review — Tremly

Review all REST and GraphQL endpoints for security issues. Read [review-steps.md](references/review-steps.md) for the full 10-step procedure.

## Review Steps Summary

| Step | Area | Key Files |
|------|------|-----------|
| 1 | Endpoint inventory | 7 `urls.py` files |
| 2 | Auth requirements | Known AllowAny list; flag unexpected ones |
| 3 | Rate limiting | `throttle_classes` — auth 5/min, OTP 3/min |
| 4 | Input validation | Serializer fields, filterset injection, file uploads |
| 5 | Response data leakage | `PersonSerializer`, `UserSerializer`, PII in errors |
| 6 | CORS config | `base.py` — `CORS_ALLOW_ALL_ORIGINS` must be False |
| 7 | Webhook security | `esigning/webhooks.py` — HMAC enforced? Idempotent? |
| 8 | GraphQL security | Introspection, depth limiting, auth on resolvers |
| 9 | MCP server | `backend/mcp_server/server.py` — no auth = CRITICAL |
| 10 | Static/media files | Auth-gated? Content-Disposition headers? |

## Output Format

```
# API Security Review Report
Date: [date]

## Endpoint Security Matrix
| # | Method | Path | Auth | Throttle | Role | Input Val | Data Leak | Status |
|---|--------|------|------|----------|------|-----------|-----------|--------|
| 1 | POST | /api/v1/auth/login/ | None | None | N/A | OK | OK | FAIL |

## Critical Findings
[Detailed findings with remediation]

## Rate Limiting Plan
[Recommended throttle config]

## CORS Hardening
[Production CORS config]

## Webhook Security Assessment
## GraphQL Security Assessment
## MCP Server Assessment

## Summary
- Total endpoints: X | Authenticated: X | Rate limited: X | Needs remediation: X
```
