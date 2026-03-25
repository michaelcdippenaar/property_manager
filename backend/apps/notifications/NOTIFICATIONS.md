# Notifications app (`apps.notifications`)

Sends **email** (Django mail), **SMS**, and **WhatsApp** (Twilio when configured). Outbound email is logged in **`NotificationLog`** (Django admin → Notifications).

**First-time setup:** create the log table (required before `send_test_email` or any `send_email` logging works):

```bash
python manage.py migrate notifications
```

Use **`send_email()`** from `apps.notifications.services` anywhere in the codebase.

## Gmail (personal Google account) — SMTP

Google does not allow normal passwords for SMTP. Use **2-Step Verification** and an **App password**.

1. Open [Google Account → Security](https://myaccount.google.com/security).
2. Enable **2-Step Verification** if it is off.
3. Search for **App passwords** (or: Security → How you sign in to Google → App passwords).
4. Create an app password for “Mail” / “Other” and copy the **16-character** password.

In `.env` (or environment):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=You <you@gmail.com>
```

Remove spaces from the app password in `.env` if Google shows them grouped (`xxxxxxxxxxxxxxxx`).

### Verify

```bash
cd backend
python manage.py send_test_email your.friend@example.com
```

Or self-test to your own Gmail:

```bash
python manage.py send_test_email
```

(Uses `DEFAULT_FROM_EMAIL` as the recipient.)

### Troubleshooting

| Symptom | Likely cause |
|--------|----------------|
| `Authentication failed` | Wrong app password, or 2FA not enabled |
| `Daily sending limit exceeded` | Gmail limits; use Google Workspace or a transactional provider later |
| Email in Spam | Normal for new domains; add SPF/DKIM when you use a custom domain |

### Development without Gmail

Leave defaults (or set explicitly):

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Emails print in the terminal; no credentials needed.

## Code usage

```python
from apps.notifications.services import send_email

send_email(
    subject="Sign your lease",
    body="Please open: https://…",
    to_emails="tenant@example.com",
    html_body="<p>Please <a href='https://…'>sign</a>.</p>",  # optional
)
```

## SMS / WhatsApp (optional)

Configure `TWILIO_*` in settings (see `services.py`). If Twilio is missing, SMS/WhatsApp calls log a stub and write a **failed** `NotificationLog` with a clear error message.

## Settings reference

| Variable | Purpose |
|----------|---------|
| `EMAIL_BACKEND` | `smtp.EmailBackend` for real send; `console` for dev |
| `EMAIL_HOST` / `PORT` / `TLS` | Gmail: `smtp.gmail.com`, `587`, `True` |
| `EMAIL_HOST_USER` / `PASSWORD` | Gmail address + app password |
| `DEFAULT_FROM_EMAIL` | From header (should match or be allowed for that account) |
| `NOTIFICATIONS_ENABLE_LOG` | Log rows to `NotificationLog` (default `True`) |
| `NOTIFICATIONS_DEFAULT_DIAL_CODE` | SA default `+27` for normalizing local numbers |
