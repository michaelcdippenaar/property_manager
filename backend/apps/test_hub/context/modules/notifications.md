# Module: notifications

**App path:** `apps/notifications/`
**Domain:** Push notifications (Firebase FCM) and email notifications. Triggered by domain events across other apps.

---

## Models

The notifications app does not define its own notification model. Notification records
are not persisted (fire-and-forget pattern). Push tokens are stored in `accounts.PushToken`.

---

## Services

**File:** `apps/notifications/services.py`

Provides dispatch functions called by other apps when events occur:

| Function (expected) | Trigger | Channel |
|---------------------|---------|---------|
| `send_push(user, title, body, data)` | Any app event | Firebase FCM |
| `send_email(to, subject, template, context)` | Lease events, invite, OTP | Email backend (SMTP/SES) |
| Maintenance dispatch notification | Job sent to supplier | Firebase or email |
| Lease signing notification | Submission created | Firebase + email |

Currently notifications log to console. Firebase and email backends are wired but
under active development.

---

## Push Token Storage

Push tokens are stored in `apps.accounts.PushToken`:

```
user     → FK→User
token    → CharField (FCM/APNs device token)
platform → "ios" | "android"
```

`POST /api/v1/auth/push-token/` registers or updates a device token.
Duplicate tokens (same `token` value) should be deduplicated.

---

## Firebase Integration

**SDK:** `firebase_admin` Python SDK
**Method:** `messaging.send(message)` where `message` is a `messaging.Message` object.

In tests, always mock Firebase:

```python
@patch("apps.notifications.services.messaging.send")
def test_push_dispatched_on_job_award(self, mock_send):
    mock_send.return_value = "projects/tremly/messages/abc123"
    # trigger job award
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert call_args.token == expected_device_token
```

---

## Email Integration

**Backend:** Django email backend (SMTP in development, SES in production)
**Method:** `django.core.mail.send_mail` or `send_mass_mail`

In tests, use `django.test.utils.override_settings` with `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` and check `django.core.mail.outbox`:

```python
from django.core import mail

def test_invite_email_sent(self):
    # trigger invite
    assert len(mail.outbox) == 1
    assert "invited" in mail.outbox[0].subject.lower()
```

---

## Integration Dependencies

- **Firebase Admin SDK** — push notification dispatch
- **Django email backend** — email dispatch
- `apps.accounts.PushToken` — device token lookup
- Triggered by: `apps.maintenance` (job dispatch), `apps.esigning` (signing requests), `apps.leases` (lease events), `apps.accounts` (OTP, invites)

---

## Current Status

This app currently has **no test coverage** — it is a known gap.

The notification dispatch layer is functional (logs to console) but not fully tested.
Firebase and email paths need mocked integration tests.

---

## Key Areas Needing Tests

- `send_push`: valid user with push token → Firebase `messaging.send` called with correct token
- `send_push`: user with no push token → no Firebase call; no exception raised
- `send_push`: Firebase raises exception → exception caught, logged, does not bubble up
- `send_email`: correct `to`, `subject`, `body` passed to email backend
- `send_email`: invalid email address → handled gracefully
- Push token registration: `POST /auth/push-token/` with new token → 201 + `PushToken` created
- Push token registration: same token submitted twice → deduplicated (not duplicated)
- Push token: different platforms (ios vs android) handled independently
- Email backend: verify `locmem` backend captures outbox in tests

---

## Testing Setup Checklist

Before writing notification tests:

1. Set `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` in test settings
2. Mock Firebase: `@patch("apps.notifications.services.messaging.send")`
3. Clear `mail.outbox` in `setUp` (Django clears it per test automatically with `locmem`)
4. Create a `PushToken` for the user under test using the accounts factory or directly:

```python
from apps.accounts.models import PushToken
PushToken.objects.create(user=tenant, token="fcm-token-abc", platform="android")
```
