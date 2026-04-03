---
name: auth-hardening
description: >
  Harden authentication and authorization for the Django/DRF backend. Trigger for: "harden auth",
  "rate limiting", "brute force protection", "2FA", "MFA", "session security", "JWT hardening",
  "role escalation", "permission classes", "lock down auth", "add throttling", "prevent brute force",
  "password policy", "account lockout", "strengthen authentication".
---

# Authentication & Authorization Hardening — Tremly

You are a security engineer specializing in Django authentication hardening. Review the current auth implementation and provide actionable fixes with code.

## Step 1: Assess Current State

Read these files:
- `backend/apps/accounts/models.py` — User model, OTPCode, roles
- `backend/apps/accounts/views.py` — Login, Register, OTP, MeView
- `backend/apps/accounts/serializers.py` — Writable fields, role field
- `backend/apps/accounts/urls.py` — Public endpoints
- `backend/config/settings/base.py` — JWT config, REST_FRAMEWORK defaults, password validators

## Step 2: Identify and Fix Each Issue

### 2.1 Rate Limiting on Auth Endpoints
**Problem:** `LoginView`, `RegisterView`, `OTPSendView`, `OTPVerifyView` all have `permission_classes = [AllowAny]` with NO throttle_classes.

**Fix:** Add DRF throttle classes:
```python
from rest_framework.throttling import AnonRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    rate = '5/min'

class OTPRateThrottle(AnonRateThrottle):
    rate = '3/min'
```
Apply `AuthRateThrottle` to LoginView and RegisterView.
Apply `OTPRateThrottle` to OTPSendView and OTPVerifyView.

Also add default throttle rates to settings:
```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/hour',
        'user': '100/hour',
    }
}
```

### 2.2 Role Escalation via PATCH /me/
**Problem:** `UserSerializer` has `role` in `fields` but NOT in `read_only_fields`. Any authenticated user can PATCH `{"role": "admin"}` to escalate privileges.

**Fix:** Add `role` to `read_only_fields` in `UserSerializer`:
```python
read_only_fields = ["id", "date_joined", "role", "email", "is_staff", "is_superuser"]
```

### 2.3 OTP Uses Insecure Random
**Problem:** OTP generation uses `random.randint(100000, 999999)` which is NOT cryptographically secure.

**Fix:**
```python
import secrets
code = f"{secrets.randbelow(900000) + 100000}"
```

Also add:
- OTP attempt limiting (max 5 failed attempts per phone per 15 minutes)
- Delete used OTPs after verification
- Add cooldown between OTP sends (e.g., 60 seconds)

### 2.4 Registration Role Assignment
**Verify:** `RegisterSerializer` has `fields = ["email", "first_name", "last_name", "phone", "password"]` — role is NOT in fields. Confirm this remains safe.

### 2.5 JWT Hardening
**Current config:**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}
```

**Recommendations:**
- Add `"BLACKLIST_AFTER_ROTATION": True` and add `rest_framework_simplejwt.token_blacklist` to INSTALLED_APPS
- Add `"UPDATE_LAST_LOGIN": True`
- Consider reducing ACCESS_TOKEN_LIFETIME to 15-30 minutes
- Add `"TOKEN_TYPE_CLAIM": "token_type"` for explicit type checking
- Add `"JTI_CLAIM": "jti"` for token revocation support

### 2.6 Password Policy
**Current:** Django's 4 default validators with default MinimumLengthValidator (8 chars).

**Fix:** Strengthen with custom validator:
- Minimum 10 characters
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character

### 2.7 Account Lockout
**Implement:** Track failed login attempts per email. Lock account after 5 failed attempts for 15 minutes. Log all failed attempts.

### 2.8 Permission Classes Review
Search ALL views for authorization gaps. Create role-based permission classes:

```python
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'

class IsAgentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ('agent', 'admin')

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'owner'

class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'tenant'

class IsSupplier(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'supplier'
```

Apply appropriate permission classes to ALL ViewSets based on the role access matrix.

### 2.9 2FA Recommendations
For admin and agent roles, recommend adding TOTP-based 2FA:
- Use `django-otp` or `django-two-factor-auth`
- Required for admin and agent roles
- Optional for tenant and owner roles
- Integrate with the existing OTP infrastructure

## Step 3: Provide Implementation Plan

For each fix, provide:
1. Exact file and line to modify
2. Code changes with before/after
3. Migration requirements (if model changes)
4. Test cases to add
5. Priority (P0 = immediate, P1 = this sprint, P2 = next sprint)

## Output Format

```
# Auth Hardening Report

## P0 — Fix Immediately
1. [Issue] — [File] — [Fix summary]

## P1 — This Sprint
1. ...

## P2 — Next Sprint
1. ...

## Implementation Checklist
- [ ] Add throttle_classes to all AllowAny views
- [ ] Add role to read_only_fields in UserSerializer
- [ ] Replace random.randint with secrets in OTP generation
- [ ] Add JWT token blacklisting
- [ ] Add role-based permission classes
- [ ] Add account lockout mechanism
- [ ] Strengthen password validators
- [ ] Add 2FA for admin/agent roles

## Test Cases to Add
- [ ] Test role escalation via PATCH /me/ is blocked
- [ ] Test rate limiting on login endpoint
- [ ] Test OTP brute force protection
- [ ] Test account lockout after N failures
```
