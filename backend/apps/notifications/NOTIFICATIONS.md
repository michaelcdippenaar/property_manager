# Notifications app (`apps.notifications`)

## Email template compile step

The base email template lives in two files:

| File | Purpose |
|------|---------|
| `email_templates/base.mjml` | Source of truth — edit this |
| `email_templates/compiled/base.html` | Compiled output committed to the repo — **never edit directly** |

`base.html` must be regenerated whenever `base.mjml` changes. Skipping this causes the compiled file to be stale, which means any `mj-button` or `mj-text` changes are silently lost in production.

### Why we commit compiled output

The Django email service renders `compiled/base.html` at runtime as a Django template (using `{% if cta_url %}`, `{% if note %}`, etc.). Committing the compiled file means the server needs no Node.js runtime. The compile step runs in development and in CI.

### How to recompile

```bash
# from repo root
make compile-emails
```

Or directly:

```bash
bash scripts/compile_email_templates.sh
```

This:
1. Strips the Django `{% if %}` / `{% endif %}` lines (MJML can't parse them) into a temp file
2. Runs `npx mjml` to compile to HTML
3. Runs `scripts/patch_email_conditionals.py` to re-insert the Django conditional blocks
4. Writes the result to `email_templates/compiled/base.html`

### CI guard

`make check-emails` (or `bash scripts/compile_email_templates.sh --check`) runs in:
- GitHub Actions (`ci.yml` → `email-templates` job)
- Pre-commit hook (runs when files under `email_templates/` are staged)

It exits non-zero if:
- `compiled/base.html` differs from a fresh compile of the current `base.mjml`
- Any of `{% if cta_url %}`, `{% if note %}`, `{% if unsubscribe_url %}` is absent from `compiled/base.html`

### Adding a new conditional block

1. Add the `{% if my_var %}` / `{% endif %}` wrapper around the relevant `<mj-*>` tag in `base.mjml` (as a comment marker, it won't survive compile)
2. Add a `<!-- BLOCK: my-block-name -->` comment above it in `base.mjml` so MJML preserves the anchor
3. Add a patch rule to `scripts/patch_email_conditionals.py` mirroring the existing CTA/note patterns
4. Run `make compile-emails` and commit both `base.mjml` and `compiled/base.html`



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
