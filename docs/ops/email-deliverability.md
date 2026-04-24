# Email Deliverability — Klikk Transactional Email

> **Architecture decision (DEC-023, 2026-04-24):** All transactional mail is sent from
> `no-reply@klikk.co.za` via **AWS SES af-south-1**. Reply-to is `support@klikk.co.za`.
> The apex domain `klikk.co.za` is shared with Google Workspace (human mailboxes such as
> `mc@klikk.co.za`). The SES and Google senders coexist on the apex — see the
> "Dual-sender coexistence" section below.

---

## Sender identity summary

| Field | Value |
|-------|-------|
| From address | `no-reply@klikk.co.za` |
| Friendly name | `Klikk` |
| Reply-To | `support@klikk.co.za` |
| AWS region | `af-south-1` (Cape Town) |
| SMTP host | `email-smtp.af-south-1.amazonaws.com` |
| SMTP port | 587 (STARTTLS) |
| Django setting | `DEFAULT_FROM_EMAIL=Klikk <no-reply@klikk.co.za>` |

---

## Dual-sender coexistence on `klikk.co.za`

`klikk.co.za` has two authorised mail senders:

1. **Google Workspace** — human mailboxes (`mc@klikk.co.za`, `support@klikk.co.za`, `dmarc@klikk.co.za`, etc.)
2. **AWS SES af-south-1** — transactional outbound only (`no-reply@klikk.co.za`)

Both senders share the same apex domain. The coexistence rules are:

- **SPF:** Extend the existing Google SPF record to add `include:amazonses.com`. Do not replace it.
- **DKIM:** SES generates CNAME-based DKIM records with unique selectors (different from Google's selector). Both sets of CNAME records coexist in Route 53 without conflict.
- **DMARC:** A single `_dmarc.klikk.co.za` TXT record covers both senders. Start at `p=quarantine`; move to `p=reject` after 30 days of clean RUA reports.
- **MX:** Google Workspace MX records remain unchanged — SES is outbound only and does not touch MX.
- **Inbound to `no-reply@`:** This address does not receive mail. Replies route to `support@klikk.co.za` via the Reply-To header.

---

## DNS records

### SPF — `klikk.co.za` apex

The apex already has a Google Workspace SPF record. **Extend it** — do not replace it.

```
klikk.co.za.  TXT  "v=spf1 include:_spf.google.com include:amazonses.com ~all"
```

Harden `~all` to `-all` once you are confident all legitimate senders are listed and DMARC
reports are clean.

> **Check before applying:** `dig +short TXT klikk.co.za | grep spf`. If the existing record
> already contains `include:amazonses.com`, no change is needed. Route 53 UPSERT replaces the
> entire record set — include ALL existing TXT values when updating.

### DKIM — SES CNAME records

Verify the domain `klikk.co.za` in the SES console (**Verified identities → Create identity →
Domain → klikk.co.za → Easy DKIM → RSA 2048**). SES generates three CNAME records:

```
<selector1>._domainkey.klikk.co.za.  CNAME  <selector1>.dkim.amazonses.com.
<selector2>._domainkey.klikk.co.za.  CNAME  <selector2>.dkim.amazonses.com.
<selector3>._domainkey.klikk.co.za.  CNAME  <selector3>.dkim.amazonses.com.
```

Replace `<selector1/2/3>` with the values shown in the SES console — they are unique to your
AWS account. These coexist with Google Workspace DKIM selectors because each selector name is
globally unique.

After adding the CNAMEs to Route 53, the SES console will show **"DKIM: Verified"** within
~15 minutes.

### DMARC — `_dmarc.klikk.co.za`

Launch policy: `p=quarantine`. Update to `p=reject` after 30 days of clean aggregate reports.

**Launch record (apply now):**
```
_dmarc.klikk.co.za.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@klikk.co.za; ruf=mailto:dmarc@klikk.co.za; fo=1; pct=100"
```

**Post-30-day hardened record:**
```
_dmarc.klikk.co.za.  TXT  "v=DMARC1; p=reject; rua=mailto:dmarc@klikk.co.za; ruf=mailto:dmarc@klikk.co.za; fo=1; pct=100"
```

Fields:
- `rua` — aggregate reports sent daily to `dmarc@klikk.co.za` (Google Workspace mailbox)
- `ruf` — forensic/failure reports (per-message, PII-lite); same address
- `fo=1` — generate failure report if either SPF or DKIM fails (not both)
- `pct=100` — policy applies to 100% of messages

### MX — no changes

Google Workspace MX records handle `@klikk.co.za` inbound. Leave them untouched.
SES is outbound only.

---

## Django configuration

All email settings are env-driven. See `backend/config/settings/base.py` (email section)
and the env files below.

### `.env.staging`

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.af-south-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
# EMAIL_HOST_USER=<from SSM /klikk/staging/ses/smtp-user>
# EMAIL_HOST_PASSWORD=<from SSM /klikk/staging/ses/smtp-password>
DEFAULT_FROM_EMAIL=Klikk Staging <no-reply@klikk.co.za>
SERVER_EMAIL=no-reply@klikk.co.za
EMAIL_REPLY_TO=support@klikk.co.za
AWS_SES_REGION=af-south-1
```

### `.env.production`

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.af-south-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
# EMAIL_HOST_USER=<from SSM /klikk/production/ses/smtp-user>
# EMAIL_HOST_PASSWORD=<from SSM /klikk/production/ses/smtp-password>
DEFAULT_FROM_EMAIL=Klikk <no-reply@klikk.co.za>
SERVER_EMAIL=no-reply@klikk.co.za
EMAIL_REPLY_TO=support@klikk.co.za
AWS_SES_REGION=af-south-1
```

### Credentials bootstrap (SSM Parameter Store)

SES SMTP credentials are never committed. Retrieve them at instance boot:

```bash
# Staging
export EMAIL_HOST_USER=$(aws ssm get-parameter \
  --name /klikk/staging/ses/smtp-user --with-decryption \
  --query Parameter.Value --output text)
export EMAIL_HOST_PASSWORD=$(aws ssm get-parameter \
  --name /klikk/staging/ses/smtp-password --with-decryption \
  --query Parameter.Value --output text)

# Production
export EMAIL_HOST_USER=$(aws ssm get-parameter \
  --name /klikk/production/ses/smtp-user --with-decryption \
  --query Parameter.Value --output text)
export EMAIL_HOST_PASSWORD=$(aws ssm get-parameter \
  --name /klikk/production/ses/smtp-password --with-decryption \
  --query Parameter.Value --output text)
```

Store these in `/etc/klikk/.env.secrets` (mode 0600, owner `klikk`) or inject them via
`systemd` `EnvironmentFile=` on the EC2 instance.

### IAM policy for SES SMTP user

Create a dedicated IAM user (not a role) for SMTP credentials. Attach a minimal policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "ses:SendRawEmail",
    "Resource": "arn:aws:ses:af-south-1:<account-id>:identity/klikk.co.za"
  }]
}
```

Generate SMTP credentials via **IAM → User → Security credentials → Create SMTP credentials**
(not access key — the SMTP password is derived differently).

---

## SES sandbox → production access

New SES accounts start in the **sandbox**, which can only send to verified addresses.
To send to real users, request production access:

1. AWS Console → SES → **Account dashboard → Request production access**
2. Use case: **Transactional**
3. Describe: lease notifications, rent reminders, OTP codes for SA property management platform
4. Expected volume: < 10 000 emails/month at launch; growing to ~50 000 within 12 months
5. Bounce/complaint handling: SNS → Lambda (see Bounce handling section below)

Approval typically takes < 24 hours.

---

## Bounce and complaint handling

Configure SES SNS notifications to auto-suppress bounced/complained addresses:

1. SES Console → **klikk.co.za identity → Notifications → Edit**
2. Set **Bounces** → SNS topic: `klikk-ses-bounces`
3. Set **Complaints** → SNS topic: `klikk-ses-complaints`
4. Subscribe the Klikk API endpoint (or a Lambda) to each topic

The `apps.notifications` app's `NotificationLog` model tracks delivery status.
A spike in `status=failed` rows triggers a Sentry alert.

Suppression endpoint pattern (implement when building the notification suppression list):

```
POST /api/v1/notifications/ses-bounce/
POST /api/v1/notifications/ses-complaint/
```

Both endpoints verify the SNS message signature before processing.

---

## Warmup schedule

Sending from a new domain triggers spam filters if volume spikes suddenly.
Ramp slowly for the first 4–6 weeks:

| Week | Daily volume cap | Notes |
|------|-----------------|-------|
| 1 | 50 emails/day | Staff + beta users only |
| 2 | 200 emails/day | First real agent accounts |
| 3 | 500 emails/day | |
| 4 | 1 000 emails/day | |
| 5–6 | 2 000 emails/day | |
| 7+ | Remove cap | Monitor bounce/complaint rates |

**Stop the warmup and investigate if:**
- Bounce rate > 2%
- Spam complaint rate > 0.08%
- Gmail or Outlook starts bulk-foldering Klikk mail

---

## Testing

### Local development

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

All emails print to the Django console — no SMTP credentials needed.

### Integration / CI

Use [Mailpit](https://mailpit.axllent.org/) as a local SMTP sink:

```bash
docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
```

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
```

Browse captured emails at `http://localhost:8025`.

### Pre-launch quality check

Send a test email to [mail-tester.com](https://www.mail-tester.com/) from the SES
SMTP relay and verify:

- SPF: pass (aligned)
- DKIM: pass (SES Easy DKIM)
- DMARC: pass
- No blacklist hits
- Valid unsubscribe link (where required)
- Target score: **≥ 9/10**

Run the test from the production SES identity (not sandbox) to get a realistic score.

### Verify DNS records

```bash
# SPF
dig +short TXT klikk.co.za | grep spf

# SES DKIM (replace <selector> with value from SES console)
dig +short CNAME <selector1>._domainkey.klikk.co.za

# DMARC
dig +short TXT _dmarc.klikk.co.za
```

---

## Monitoring

| Signal | Tool | Threshold |
|--------|------|-----------|
| Bounce rate | SES dashboard + SNS bounce topic | Alert > 2% |
| Complaint rate | SES dashboard + SNS complaint topic | Alert > 0.08% |
| Delivery success | `NotificationLog` (channel=email, status=sent) | — |
| Failed sends | `NotificationLog` (status=failed) → Sentry | Alert on spike |
| DMARC reports | `dmarc@klikk.co.za` inbox (Google Workspace) | Review weekly |

---

## POPIA compliance

- Only send to users with an active contractual relationship (tenant, agent, owner) or
  who have explicitly consented.
- Every non-transactional email must include an **unsubscribe link**.
- Transactional email (lease signing, rent reminders, OTP, password reset) is sent under
  legitimate interest / contractual necessity — no separate marketing consent required, but
  must remain proportionate and relevant.
- Information Officer contact: **privacy@klikk.co.za** — included in every email footer.
- Data subject access requests for email logs: respond within 30 days per POPIA s.23.
- Bounce suppression lists constitute personal data — handle under POPIA processing grounds.

---

## Post-launch checklist

- [ ] SES domain identity `klikk.co.za` verified (DKIM shows "Verified" in SES console)
- [ ] SPF record updated to include `include:amazonses.com`
- [ ] Three SES DKIM CNAME records in Route 53; SES console shows "Verified"
- [ ] DMARC TXT record at `_dmarc.klikk.co.za` (`p=quarantine`)
- [ ] SES out of sandbox (production access approved)
- [ ] SMTP credentials stored in SSM Parameter Store; injected at boot via `.env.secrets`
- [ ] SNS bounce + complaint topics configured; Klikk endpoint subscribed
- [ ] Test email to mail-tester.com scores ≥ 9/10
- [ ] Google Workspace mailboxes unaffected (send a test from `mc@klikk.co.za`)
- [ ] After 30 days clean DMARC reports: promote `p=quarantine` → `p=reject`
- [ ] After warmup complete: request SES sending limit increase if needed
