# Notifications App — System Documentation

Centralized **outbound notifications** for the Tremly / Klikk backend.

### Current scope (as deployed)

| Status | Detail |
|--------|--------|
| **Set up** | `apps.notifications` is installed; run `migrate notifications` on each environment. |
| **In use** | **Email only** — Django SMTP (e.g. Gmail + app password). Use `send_email()` from `apps.notifications.services`. |
| **Not in use (yet)** | **SMS** and **WhatsApp** — implemented via Twilio in code but **ignored operationally** until `TWILIO_*` is configured. No Twilio keys required for email-only. |

The app persists an **audit trail** in **`NotificationLog`** (Django Admin → Notifications).

**Related:** Gmail `.env` values, smoke test, and quick examples → [`../NOTIFICATIONS.md`](../NOTIFICATIONS.md). This document covers **architecture**, **model design**, **service behaviour**, and **operational instructions** (including Twilio for when you turn it on).

---

## Table of contents

0. [Current scope](#current-scope-as-deployed) *(above)*
1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Model design](#3-model-design)
4. [Service layer (`services.py`)](#4-service-layer-servicespy)
5. [Phone number normalization](#5-phone-number-normalization)
6. [Configuration reference](#6-configuration-reference)
7. [Twilio: SMS and WhatsApp](#7-twilio-sms-and-whatsapp)
8. [Integrations elsewhere in the codebase](#8-integrations-elsewhere-in-the-codebase)
9. [Django Admin](#9-django-admin)
10. [Migrations and first-time setup](#10-migrations-and-first-time-setup)
11. [Operational notes](#11-operational-notes)
12. [Testing and mocking](#12-testing-and-mocking)

---

## 1. Overview

**Primary path today:** **email** via `send_email()` → Django mail → SMTP (see §6.1).

| Capability | Implementation | When it sends “for real” |
|------------|----------------|---------------------------|
| **Email** | `django.core.mail.EmailMultiAlternatives` | When `EMAIL_BACKEND` is SMTP (or another non-stub backend) and credentials/host are valid |
| SMS *(optional)* | Twilio `messages.create` | Only when `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_SMS_FROM` are set |
| WhatsApp *(optional)* | Twilio `messages.create` with `whatsapp:` addresses | Only when Twilio credentials and `TWILIO_WHATSAPP_FROM` are set, and the sender is approved for the recipient |

If Twilio is **not** configured (email-only deployments), `send_sms` / `send_whatsapp` **return `False`**, log a **stub line** to the application logger, and (unless logging is disabled) create a **`NotificationLog` row with `status=failed`** and an explanatory `error_message`. That is **expected** until you add Twilio.

Email failures are caught, logged with `logger.exception`, and recorded per recipient in `NotificationLog` as **failed**.

---

## 2. Architecture

**Email-only today:** callers use **`send_email`** → Django mail → **`NotificationLog`**.

```
┌─────────────────────────────────────────────────────────────────┐
│ Callers (leases, maintenance, accounts, future apps)             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ apps.notifications.services                                      │
│  send_email  ◄── primary in use                                   │
│  send_sms │ send_whatsapp │ …  ◄── optional (Twilio)             │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
             ▼                               ▼
┌────────────────────────┐      ┌──────────────────────────────────┐
│ Django mail (SMTP/…)   │      │ Twilio REST (SMS + WhatsApp)      │
│ ◄── active             │      │ ◄── inactive until TWILIO_* set   │
└────────────────────────┘      └──────────────────────────────────┘
             │                               │
             └───────────────┬───────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ NotificationLog (optional, NOTIFICATIONS_ENABLE_LOG)             │
└─────────────────────────────────────────────────────────────────┘
```

**Design choices:**

- **No Celery requirement** — sends are synchronous. For high volume, wrap calls in tasks later without changing the public service API.
- **Single log row per logical recipient** for email success/failure (one row per address in `to_emails` / CC expansion).
- **Facade** — `core.notifications.send_sms_otp` imports `deliver_otp_sms` so older imports and tests that patch `core.notifications.send_sms_otp` keep working.
- **Resilience** — `_log()` catches `DatabaseError` and logs a warning so a broken log table does not crash sends.

---

## 3. Model design

### 3.1 Enumerations

#### `NotificationChannel` (`TextChoices`)

Stored as short string values on `NotificationLog.channel`.

| Constant | DB value | Meaning |
|----------|----------|---------|
| `EMAIL` | `email` | Outbound email |
| `SMS` | `sms` | Outbound SMS via Twilio |
| `WHATSAPP` | `whatsapp` | Outbound WhatsApp via Twilio |

#### `NotificationStatus` (`TextChoices`)

| Constant | DB value | Meaning |
|----------|----------|---------|
| `PENDING` | `pending` | Default on the model; current service code writes **`sent`** or **`failed`** directly (see §3.3) |
| `SENT` | `sent` | Provider accepted the message (email handed to backend; Twilio returned a message SID) |
| `FAILED` | `failed` | Send failed or provider not configured (see `error_message`) |

The model default remains `pending` for forward compatibility if future code creates rows before sending.

---

### 3.2 `NotificationLog`

**Purpose:** Audit trail, debugging, and light operational visibility. This is **not** a full “notification inbox” or user preference store — it records **what was attempted** and **what happened**.

| Field | Django type | Max length / notes | Description |
|-------|-------------|-------------------|-------------|
| `id` | `BigAutoField` | — | Primary key |
| `channel` | `CharField` | 16 | One of `NotificationChannel` |
| `to_address` | `CharField` | 320 | Email address, E.164 phone, or `whatsapp:+…` recipient string |
| `subject` | `CharField` | 255, blank OK | Used for **email**; empty for SMS/WhatsApp |
| `body` | `TextField` | — | Stored copy of content; **truncated to 10 000 characters** before insert (suffix `…` if truncated) |
| `status` | `CharField` | 16 | `pending` / `sent` / `failed` |
| `provider_message_id` | `CharField` | 128, blank OK | Twilio **Message SID** when applicable; empty for console email |
| `error_message` | `TextField` | blank OK | Truncated to **2 000** characters on write; human-readable failure reason |
| `created_at` | `DateTimeField` | `auto_now_add` | Row creation time (timezone-aware per project `TIME_ZONE`) |

**Meta:**

- `ordering = ["-created_at"]` — newest first in default querysets.
- **Indexes:**
  - `created_at` descending — list/filter by recency in admin and reports.
  - `(channel, status)` — filter “failed SMS in the last day”, etc.

**`__str__`:** `{channel} → {to_address} ({status})`

---

### 3.3 When rows are created (lifecycle)

| Action | Rows | `status` | `provider_message_id` | `error_message` |
|--------|------|----------|-------------------------|-----------------|
| `send_email` success | One per recipient | `sent` | empty | empty |
| `send_email` exception | One per recipient | `failed` | empty | exception text |
| `send_sms` success | One | `sent` | Twilio `sid` | empty |
| `send_sms` Twilio exception | One | `failed` | empty | exception text |
| `send_sms` not configured | One | `failed` | empty | Fixed message: missing SID/token or `TWILIO_SMS_FROM` |
| `send_whatsapp` | Same pattern as SMS | | | Uses `TWILIO_WHATSAPP_FROM` in not-configured message |
| `NOTIFICATIONS_ENABLE_LOG=False` | None | — | — | — |
| `_log()` hits `DatabaseError` | None (warning log only) | — | — | — |

---

### 3.4 What this model is **not**

- **No** foreign keys to `User`, `Lease`, or `MaintenanceRequest` — correlation is done by recipient address/content if needed. Adding optional `FK` + `metadata` JSON is a natural future extension.
- **No** retry queue or idempotency keys — callers must implement retries if required.
- **No** template versioning — only stored body text (truncated).

---

## 4. Service layer (`services.py`)

Import path:

```python
from apps.notifications.services import (
    send_email,
    send_sms,
    send_whatsapp,
    notify_sms_and_whatsapp,
    deliver_otp_sms,
    normalize_phone_e164,
)
```

### 4.1 `send_email(subject, body, to_emails, *, html_body=None, from_email=None) -> bool`

- **`to_emails`:** Either a single `str` or a **sequence** of addresses.
- **Multi-recipient behaviour:** First address is `To:`; additional addresses are **`Cc:`** on **one** `EmailMultiAlternatives` instance (one SMTP transaction).
- **`html_body`:** Optional; attached as `text/html` alternative; plain `body` remains the text part.
- **`from_email`:** Optional; defaults to `settings.DEFAULT_FROM_EMAIL`.
- **Returns:** `True` if send succeeded; `False` if no recipients or send raised.

### 4.2 `send_sms(to_phone, body) -> bool`

- Normalizes `to_phone` with `normalize_phone_e164`.
- **Returns `False`** if phone empty, Twilio missing, or API error.

### 4.3 `send_whatsapp(to_phone, body) -> bool`

- Normalizes phone, then formats destination as `whatsapp:{e164}` unless already prefixed.
- **`TWILIO_WHATSAPP_FROM`:** If set without `whatsapp:` prefix, the service **prepends** `whatsapp:`.

### 4.4 `notify_sms_and_whatsapp(to_phone, body) -> dict[str, bool]`

Returns `{"sms": bool, "whatsapp": bool}`. Each channel is independent (one can succeed and the other fail).

**Used by:** `apps.maintenance.notifications.notify_supplier` to ping suppliers on both channels when configured.

### 4.5 `deliver_otp_sms(phone, code) -> bool`

Sends a fixed template:

`Your verification code is: {code}. It expires in 10 minutes.`

**Used by:** `core.notifications.send_sms_otp` (called from account OTP flow).

### 4.6 `normalize_phone_e164(phone) -> str`

Documented in [§5](#5-phone-number-normalization).

---

## 5. Phone number normalization

Implemented for **South-Africa-first** defaults; override with `NOTIFICATIONS_DEFAULT_DIAL_CODE`.

**Steps:**

1. Strip whitespace, hyphens, and parentheses.
2. If empty → return `""`.
3. Ensure dial code starts with `+` (if setting is `27`, it becomes `+27`).
4. If input starts with `+` → return unchanged.
5. If input starts with `0` → replace `0` with `NOTIFICATIONS_DEFAULT_DIAL_CODE` + national digits (e.g. `0821234567` → `+27821234567` when default is `+27`).
6. If input already starts with the national digits of the dial code (e.g. `27821234567`) → prefix `+`.
7. Otherwise → prefix full default dial code (covers bare national numbers).

**Edge cases:**

- Invalid or non-numeric garbage may still be passed to Twilio; normalization does not fully validate numbering plans.
- WhatsApp **from** / **to** must match Twilio’s expected formats; the service only ensures `whatsapp:` on the destination and configurable `whatsapp:` on the sender.

---

## 6. Configuration reference

All variables are read in `config.settings.base` via `python-decouple` (typically from `backend/.env`).

### 6.1 Email

| Setting | Purpose |
|---------|---------|
| `EMAIL_BACKEND` | e.g. `django.core.mail.backends.smtp.EmailBackend` or `console` |
| `EMAIL_HOST` | SMTP host |
| `EMAIL_PORT` | Port (often `587`) |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP auth |
| `EMAIL_USE_TLS` | Usually `True` for submission port |
| `DEFAULT_FROM_EMAIL` | Default `From:` |

### 6.2 Twilio

| Setting | Purpose |
|---------|---------|
| `TWILIO_ACCOUNT_SID` | Account SID |
| `TWILIO_AUTH_TOKEN` | Auth token |
| `TWILIO_SMS_FROM` | E.164 sender number for SMS (e.g. `+27123456789`) |
| `TWILIO_WHATSAPP_FROM` | WhatsApp-enabled sender; with or without `whatsapp:` prefix |

### 6.3 App-specific

| Setting | Default | Purpose |
|---------|---------|---------|
| `NOTIFICATIONS_DEFAULT_DIAL_CODE` | `+27` | Normalize local `0…` numbers |
| `NOTIFICATIONS_ENABLE_LOG` | `True` | Persist `NotificationLog` rows |

---

## 7. Twilio: SMS and WhatsApp

**Skip this section** while you are **email-only**. The code paths exist for maintenance/OTP integrations; they no-op with `False` and a failed log row until Twilio is configured.

### 7.1 SMS

1. Buy or verify a Twilio phone number capable of SMS in your target region.
2. Set `TWILIO_SMS_FROM` to that number in E.164.
3. Ensure account balance and geo permissions allow delivery to recipient countries.

### 7.2 WhatsApp

1. Configure **WhatsApp** on your Twilio number (sandbox for development, approved business sender for production).
2. Set `TWILIO_WHATSAPP_FROM` to the WhatsApp sender Twilio shows (often `whatsapp:+1…`).
3. Sandbox: recipient must opt in with Twilio’s join code before messages deliver.

**Same REST API** as SMS (`messages.create`); only addresses differ (`whatsapp:+…`).

---

## 8. Integrations elsewhere in the codebase

| Location | Usage | Email-only note |
|----------|--------|-----------------|
| **New features** | Prefer **`send_email()`** from `apps.notifications.services` | Primary pattern for transactional mail. |
| `core.notifications.send_sms_otp` | Delegates to `deliver_otp_sms` | SMS; returns `False` without Twilio. |
| `apps.accounts.views.OTPSendView` | Uses `send_sms_otp` | OTP still expects SMS unless you add email OTP later. |
| `apps.maintenance.notifications.notify_supplier` | `notify_sms_and_whatsapp` | Fails channels quietly without Twilio; consider **`send_email`** for suppliers when you want mail instead. |

When adding new features, prefer importing from **`apps.notifications.services`** directly unless you need the stable OTP facade.

---

## 9. Django Admin

Model: **Notifications → Notification logs**.

- **List:** `created_at`, `channel`, `to_address`, `status`, `subject`, `provider_message_id`
- **Filters:** `channel`, `status`
- **Search:** `to_address`, `subject`, `body`, `provider_message_id`
- **Read-only:** `created_at`
- **Date hierarchy:** `created_at`

Staff can diagnose delivery issues from `error_message` and Twilio SIDs.

---

## 10. Migrations and first-time setup

Install the app (already in `LOCAL_APPS` as `apps.notifications`).

```bash
cd backend
python manage.py migrate notifications
```

Verify email (optional):

```bash
python manage.py send_test_email you@example.com
```

See [`../NOTIFICATIONS.md`](../NOTIFICATIONS.md) for Gmail-specific `.env` values.

---

## 11. Operational notes

### 11.1 Privacy and retention

`NotificationLog` stores **recipient identifiers** and **message bodies** (truncated). That may include **personal data** under POPIA/GDPR. Define a retention policy (periodic delete or anonymize) if required.

### 11.2 Volume and rate limits

Gmail and Twilio impose **daily** and **per-second** limits. Heavy use should move to a transactional email provider and/or queue workers.

### 11.3 Disabling audit writes

Set `NOTIFICATIONS_ENABLE_LOG=False` to skip database logging (e.g. in a constrained test environment). Sends still occur when providers are configured.

### 11.4 Time zone

Timestamps use Django’s `TIME_ZONE` (`Africa/Johannesburg` in this project).

---

## 12. Testing and mocking

- **OTP tests** often patch `core.notifications.send_sms_otp` — keep that facade when changing OTP delivery.
- **Maintenance dispatch tests** patch `apps.maintenance.views.notify_supplier` — they do not hit Twilio.
- For unit tests on `services` directly, patch `_twilio_client` or Twilio’s `Client` if you need to assert API calls without network access.

---

## File map

| Path | Role |
|------|------|
| `apps/notifications/models.py` | `NotificationLog`, enums |
| `apps/notifications/services.py` | Send + log implementation |
| `apps/notifications/admin.py` | Admin registration |
| `apps/notifications/migrations/` | Schema |
| `apps/notifications/management/commands/send_test_email.py` | SMTP smoke test |
| `apps/notifications/NOTIFICATIONS.md` | Gmail + quick usage |
| `core/notifications.py` | OTP facade |

---

*Last aligned with implementation in `apps.notifications` (models, services, admin, settings). **Production stance:** email in use; SMS/WhatsApp available in code when Twilio is configured. Update this document when behaviour or schema changes.*
