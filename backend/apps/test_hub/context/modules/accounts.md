# Module: accounts

**App path:** `apps/accounts/`
**Domain:** User management, authentication, authorization, roles, audit logging.

---

## Models

| Model | Purpose |
|-------|---------|
| `User` | Custom auth user (`AbstractBaseUser`). Fields: `email` (unique), `first_name`, `last_name`, `phone`, `id_number`, `role`, `is_active`, `is_staff`. `USERNAME_FIELD = "email"`. |
| `Person` | Natural person or company linked to property transactions. May or may not have a `linked_user`. Fields: `linked_user` (OneToOne, nullable), `person_type` (individual/company), `full_name`, `id_number`, `phone`, `email`, `address`, `employer`, `occupation`, `date_of_birth`, `emergency_contact_*`, `company_reg`, `vat_number`. |
| `OTPCode` | One-time password. Fields: `user` (FK), `code` (6-char), `created_at`, `is_used`. |
| `PushToken` | FCM/APNs device token. Fields: `user` (FK), `token`, `platform` (ios/android). |
| `UserInvite` | Invitation link for new users. Tracks inviter, invitee email, role, and expiry. |
| `AuthAuditLog` | Immutable record of every auth event (login, logout, OTP send/verify, OAuth, failed attempt). |
| `LoginAttempt` | Tracks failed login attempts per email for rate-limiting / lockout. |

---

## Roles

Defined as `User.Role` (TextChoices):

```
tenant | agent | admin | supplier | owner
```

Role is set at registration and should not be changed except by an admin. The API
enforces this via serializer validation.

---

## Permission Classes

Located in `apps/accounts/permissions.py`:

```python
IsAdmin              # role == admin
IsAgentOrAdmin       # role in (agent, admin)
IsOwner              # role == owner
IsOwnerOrStaff       # role in (owner, agent, admin)
IsSupplier           # role == supplier
IsTenant             # role == tenant
```

Use these in view `permission_classes` lists. In tests, verify that each role gets the
correct HTTP response (200/201 for allowed, 403 for denied).

---

## Auth Flow

```
POST /api/v1/auth/register/
  → validates email uniqueness, creates User + Person
  → returns {access, refresh, user}

POST /api/v1/auth/login/
  → checks credentials, returns {access, refresh, user}

POST /api/v1/auth/token/refresh/
  → returns new access token

GET  /api/v1/auth/me/
  → returns current user profile (requires Bearer token)
```

---

## OTP Flow

```
POST /api/v1/auth/otp/send/   → generates 6-digit OTPCode, sends via SMS/email
POST /api/v1/auth/otp/verify/ → validates code, marks is_used=True, returns JWT
```

OTP codes expire after a configured timeout. Using an expired or already-used code
must return 400.

---

## OAuth

Social login is supported via `apps/accounts/oauth_views.py`. Providers (e.g. Google)
exchange an OAuth token for a Tremly JWT. A new User + Person is created on first login.

---

## Audit Logging

Every auth event is written to `AuthAuditLog` (via `apps/accounts/audit.py`).
Events include: `login_success`, `login_failed`, `otp_sent`, `otp_verified`,
`token_refreshed`, `logout`, `oauth_login`.

The audit log is append-only — records are never updated or deleted.

---

## Key Invariants

- `email` must be unique across all users
- `role` cannot be changed by the user themselves; only admin can change it
- OTP codes are single-use (`is_used=True` after verification)
- OTP codes expire (check `created_at + OTP_EXPIRY_SECONDS < now`)
- A `Person` with a `linked_user` is a OneToOne relationship — one person per user
- `is_active=False` users cannot authenticate

---

## Integration Dependencies

- **Firebase Admin SDK** — push tokens registered via `POST /api/v1/auth/push-token/`
- **Email service** — OTP and invite emails sent via Django email backend (SMTP/SES)

---

## Known Test Areas

- Registration with valid data → 201 + JWT returned
- Registration with duplicate email → 400 + field error
- Registration with missing required fields → 400
- Login with correct credentials → 200 + tokens
- Login with wrong password → 401
- Login with non-existent email → 401
- OTP: send → verify (valid) → 200 + JWT
- OTP: send → verify (wrong code) → 400
- OTP: send → verify (expired code) → 400
- OTP: reuse of already-used code → 400
- JWT refresh with valid refresh token → 200
- JWT refresh with expired/invalid refresh → 401
- `GET /auth/me/` unauthenticated → 401
- `GET /auth/me/` authenticated → 200 + correct user data
- Permission: tenant denied on agent-only endpoint → 403
- Permission: agent allowed on agent-only endpoint → 200
- Permission: admin allowed everywhere → 200

---

## Coverage Gaps

- `UserInvite` workflow: create invite → accept invite → user created with correct role
- OAuth flow: token exchange, new user creation, existing user login
- `AuthAuditLog` completeness: verify every auth action creates a log entry
- `LoginAttempt` lockout: N failed attempts → account temporarily blocked
- `PushToken` registration and deduplication
