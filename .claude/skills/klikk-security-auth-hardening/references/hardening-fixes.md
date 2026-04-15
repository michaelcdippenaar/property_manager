# Auth Hardening — Fixes & Code

---

## Files to Assess First

- `backend/apps/accounts/models.py` — User model, OTPCode, roles
- `backend/apps/accounts/views.py` — Login, Register, OTP, MeView
- `backend/apps/accounts/serializers.py` — Writable fields, role field
- `backend/apps/accounts/urls.py` — Public endpoints
- `backend/config/settings/base.py` — JWT config, REST_FRAMEWORK defaults, password validators

---

## Fix 2.1 — Rate Limiting on Auth Endpoints (P0)

**Problem:** `LoginView`, `RegisterView`, `OTPSendView`, `OTPVerifyView` all have `AllowAny` with NO `throttle_classes`.

```python
from rest_framework.throttling import AnonRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    rate = '5/min'

class OTPRateThrottle(AnonRateThrottle):
    rate = '3/min'
```

Apply `AuthRateThrottle` to `LoginView` and `RegisterView`.
Apply `OTPRateThrottle` to `OTPSendView` and `OTPVerifyView`.

Add to `REST_FRAMEWORK` in settings:
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '30/hour',
    'user': '100/hour',
}
```

---

## Fix 2.2 — Role Escalation via PATCH /me/ (P0)

**Problem:** `UserSerializer` has `role` in `fields` but NOT in `read_only_fields`. Any authenticated user can PATCH `{"role": "admin"}`.

```python
# In UserSerializer
read_only_fields = ["id", "date_joined", "role", "email", "is_staff", "is_superuser"]
```

---

## Fix 2.3 — Insecure OTP Random (P0)

**Problem:** OTP uses `random.randint(100000, 999999)` — NOT cryptographically secure.

```python
import secrets
code = f"{secrets.randbelow(900000) + 100000}"
```

Also add:
- OTP attempt limiting (max 5 failed per phone per 15 minutes)
- Delete used OTPs after verification
- 60-second cooldown between OTP sends

---

## Fix 2.4 — Registration Role Assignment (Verify)

**Check:** `RegisterSerializer` should have `fields = ["email", "first_name", "last_name", "phone", "password"]` — `role` NOT in fields. Confirm this is safe.

---

## Fix 2.5 — JWT Hardening (P1)

**Current config:**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}
```

**Add:**
```python
"BLACKLIST_AFTER_ROTATION": True,
"UPDATE_LAST_LOGIN": True,
"TOKEN_TYPE_CLAIM": "token_type",
"JTI_CLAIM": "jti",
```

Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS`.
Consider reducing `ACCESS_TOKEN_LIFETIME` to 15–30 minutes.

---

## Fix 2.6 — Password Policy (P1)

**Current:** 4 default validators, minimum 8 chars.

Strengthen: minimum 10 characters, at least 1 uppercase, 1 lowercase, 1 digit, 1 special character.

---

## Fix 2.7 — Account Lockout (P1)

Track failed login attempts per email. Lock account after 5 failed attempts for 15 minutes. Log all failed attempts.

---

## Fix 2.8 — Permission Classes Review (P1)

Search ALL views for authorization gaps. Role-based permission classes:

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

Apply to all ViewSets based on the role access matrix.

---

## Fix 2.9 — 2FA for Admin/Agent Roles (P2)

Use `django-otp` or `django-two-factor-auth`:
- Required for admin and agent roles
- Optional for tenant and owner roles
- Integrate with existing OTP infrastructure

---

## Implementation Plan Format

For each fix provide:
1. Exact file and line to modify
2. Code changes (before/after)
3. Migration requirements (if model changes)
4. Test cases to add
5. Priority (P0 = immediate, P1 = this sprint, P2 = next sprint)

---

## Test Cases to Add

- [ ] Test role escalation via `PATCH /me/` is blocked
- [ ] Test rate limiting on login endpoint
- [ ] Test OTP brute force protection
- [ ] Test account lockout after N failures
- [ ] Test JWT token blacklisting on refresh
- [ ] Test password policy enforcement
