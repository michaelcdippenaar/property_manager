# Accounts App

User authentication, person management, OTP login, and push notification tokens.

## Overview

The accounts app handles all identity and authentication concerns: registration, JWT login, passwordless OTP login via SMS, user profile management, and a Person model for property-related contacts who may or may not have system login accounts.

---

## Models

### User

Custom user model with email-based authentication.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `email` | EmailField | Unique login credential |
| `first_name` | CharField(100) | First name |
| `last_name` | CharField(100) | Last name |
| `phone` | CharField(20) | Phone number |
| `id_number` | CharField(20) | SA ID or passport number |
| `role` | CharField(10) | One of: `tenant`, `agent`, `admin`, `supplier`, `owner` |
| `is_active` | BooleanField | Account active flag (default: true) |
| `is_staff` | BooleanField | Django admin access (default: false) |
| `date_joined` | DateTimeField | Auto-set on creation |

**Computed property:** `full_name` — `"{first_name} {last_name}".strip() or email`

---

### Person

Represents natural persons or companies involved in property transactions. May or may not have a system login.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `linked_user` | OneToOneField → User | System login (nullable, SET_NULL) |
| `person_type` | CharField | `individual` or `company` |
| `full_name` | CharField(200) | Person or company name |
| `id_number` | CharField(20) | SA ID or passport |
| `phone` | CharField(20) | Phone number |
| `email` | EmailField | Email address |
| `company_reg` | CharField(50) | Company registration number |
| `vat_number` | CharField(30) | VAT number |
| `created_at` | DateTimeField | Auto-set on creation |

**Used for:** Property owners, tenants, co-tenants, occupants, guarantors.

---

### OTPCode

| Field | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey → User | Associated user |
| `code` | CharField(6) | 6-digit OTP code |
| `created_at` | DateTimeField | Auto-set on creation |
| `is_used` | BooleanField | Whether OTP has been consumed |

---

### PushToken

FCM/APNs device tokens for push notifications.

| Field | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey → User | Associated user |
| `token` | TextField | Device push token |
| `platform` | CharField | `ios` or `android` |
| `updated_at` | DateTimeField | Auto-updated |

**Unique constraint:** `(user, token)`

---

## API Endpoints

All endpoints prefixed with `/api/v1/auth/`.

---

### 1. Register

```
POST /api/v1/auth/register/
```

**Auth:** None (AllowAny)

**Request:**

```json
{
  "email": "user@example.com",
  "password": "strongpass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "0821234567"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | string | Yes | Must be unique |
| `password` | string | Yes | Min 8 characters |
| `first_name` | string | No | |
| `last_name` | string | No | |
| `phone` | string | No | |

**Response:** `201 Created`

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone": "0821234567",
  "role": "tenant",
  "date_joined": "2026-03-25T10:00:00Z"
}
```

**Errors:** `400` — Duplicate email, missing fields, password too short.

---

### 2. Login

```
POST /api/v1/auth/login/
```

**Auth:** None (AllowAny)

**Request:**

```json
{
  "email": "user@example.com",
  "password": "strongpass123"
}
```

**Response:** `200 OK`

```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "phone": "0821234567",
    "role": "tenant",
    "date_joined": "2026-03-25T10:00:00Z"
  }
}
```

**Errors:** `400` — Invalid credentials or account disabled.

---

### 3. Get / Update Current User

```
GET  /api/v1/auth/me/
PATCH /api/v1/auth/me/
```

**Auth:** Required (Bearer token)

**GET Response:** `200 OK` — UserSerializer object.

**PATCH Request:** Any writable user fields.

```json
{
  "first_name": "Updated",
  "phone": "0829999999"
}
```

**PATCH Response:** `200 OK` — Updated user object.

---

### 4. Token Refresh

```
POST /api/v1/auth/token/refresh/
```

**Auth:** None (AllowAny)

**Request:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

**Response:** `200 OK`

```json
{
  "access": "eyJ0eXAiOiJKV1Qi..."
}
```

**Errors:** `401` — Invalid or expired refresh token.

---

### 5. Send OTP

```
POST /api/v1/auth/otp/send/
```

**Auth:** None (AllowAny)

**Request:**

```json
{
  "phone": "0821234567"
}
```

**Response:** `200 OK` (always the same, regardless of whether the phone exists)

```json
{
  "detail": "OTP sent if phone is registered."
}
```

Generates a 6-digit code, calls `core.notifications.send_sms_otp()`. OTP expires after 10 minutes.

---

### 6. Verify OTP

```
POST /api/v1/auth/otp/verify/
```

**Auth:** None (AllowAny)

**Request:**

```json
{
  "phone": "0821234567",
  "code": "123456"
}
```

**Response:** `200 OK` — Same as login (JWT tokens + user object).

**Errors:** `400` — Invalid, expired (>10 min), or already-used OTP.

---

### 7. Push Token

```
POST   /api/v1/auth/push-token/
DELETE /api/v1/auth/push-token/
```

**Auth:** Required (Bearer token)

**POST Request:**

```json
{
  "token": "abc123def456...",
  "platform": "ios"
}
```

**POST Response:** `200 OK` — `{"detail": "Token registered."}`

Uses `update_or_create` on `(user, token)`. Platform must be `ios` or `android`.

**DELETE Request:**

```json
{
  "token": "abc123def456..."
}
```

**DELETE Response:** `204 No Content`

---

### 8. List Tenants

```
GET /api/v1/auth/tenants/
```

**Auth:** Required

Returns Person records that appear on at least one lease (as primary tenant or co-tenant). Paginated.

**Response:** `200 OK`

```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "person_type": "individual",
      "full_name": "Alice Smith",
      "id_number": "1234567890123",
      "phone": "0821234567",
      "email": "alice@example.com",
      "linked_user": null,
      "created_at": "2026-03-20T10:00:00Z"
    }
  ]
}
```

---

### 9. Persons CRUD

```
GET  /api/v1/auth/persons/
POST /api/v1/auth/persons/
```

**Auth:** Required

**Query Parameters:**

| Param | Description |
|-------|-------------|
| `q` | Search by `full_name` (case-insensitive contains) |

**POST Request:**

```json
{
  "person_type": "individual",
  "full_name": "New Person",
  "id_number": "1234567890123",
  "phone": "0821234567",
  "email": "person@example.com"
}
```

**POST Response:** `201 Created` — PersonSerializer object.

---

### 10. Person Detail

```
GET   /api/v1/auth/persons/<id>/
PATCH /api/v1/auth/persons/<id>/
```

**Auth:** Required

Standard retrieve and partial-update for Person records.

---

## Security Notes

| ID | Severity | Issue |
|----|----------|-------|
| VULN-1 | Critical | **Role escalation** — `role` field is writable via `PATCH /me/`. Users can set their role to `admin`. Fix: add `role` to `read_only_fields` in `UserSerializer`. |
| VULN-6 | Critical | **IDOR** — `/persons/` returns all persons in the system to any authenticated user. |
| VULN-7 | Critical | **IDOR** — `/tenants/` returns all tenants across all properties to any authenticated user. |
