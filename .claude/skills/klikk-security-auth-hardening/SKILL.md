---
name: klikk-security-auth-hardening
description: >
  Harden authentication and authorization for the Django/DRF backend. Trigger for: "harden auth",
  "rate limiting", "brute force protection", "2FA", "MFA", "session security", "JWT hardening",
  "role escalation", "permission classes", "lock down auth", "add throttling", "prevent brute force",
  "password policy", "account lockout", "strengthen authentication".
---

# Authentication & Authorization Hardening — Tremly

Review current auth implementation and apply fixes. Read [hardening-fixes.md](references/hardening-fixes.md) for all 9 fixes with exact code.

## Step 1: Assess Current State

Read these files first:
- `backend/apps/accounts/models.py` — User model, OTPCode, roles
- `backend/apps/accounts/views.py` — Login, Register, OTP, MeView
- `backend/apps/accounts/serializers.py` — Writable fields
- `backend/config/settings/base.py` — JWT config, password validators

## Step 2: Apply Fixes by Priority

| Fix | Issue | Priority |
|-----|-------|----------|
| 2.1 | Rate limiting — `LoginView`/`RegisterView`/OTP views have no `throttle_classes` | **P0** |
| 2.2 | Role escalation — `role` writable via `PATCH /me/` | **P0** |
| 2.3 | Insecure OTP — `random.randint` not cryptographically secure | **P0** |
| 2.4 | Verify `RegisterSerializer` excludes `role` field | Verify |
| 2.5 | JWT hardening — add blacklisting, reduce token lifetime | P1 |
| 2.6 | Password policy — min 10 chars, complexity rules | P1 |
| 2.7 | Account lockout — 5 failures → 15 min lock | P1 |
| 2.8 | Permission classes — `IsAdmin`, `IsAgentOrAdmin`, role-based classes | P1 |
| 2.9 | 2FA for admin/agent roles via `django-otp` | P2 |

## Output Format

```
# Auth Hardening Report

## P0 — Fix Immediately
1. [Issue] — [File] — [Fix summary]

## P1 — This Sprint
## P2 — Next Sprint

## Implementation Checklist
- [ ] Add throttle_classes to all AllowAny views
- [ ] Add role to read_only_fields in UserSerializer
- [ ] Replace random.randint with secrets in OTP generation
- [ ] Add JWT token blacklisting
- [ ] Add role-based permission classes
- [ ] Add account lockout mechanism
- [ ] Strengthen password validators
- [ ] Add 2FA for admin/agent roles
```
