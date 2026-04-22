# Email Deliverability — Klikk Transactional Email

## Sender domain

All transactional email is sent from `@klikk.co.za` (or `noreply@klikk.co.za`).
`DEFAULT_FROM_EMAIL` in settings should be set to `Klikk <noreply@klikk.co.za>`.

---

## DNS records required

### SPF

Create a TXT record on `klikk.co.za` authorising the sending provider:

```
klikk.co.za.  TXT  "v=spf1 include:amazonses.com ~all"
```

Adjust `include:` to match your ESP (Amazon SES, Mailgun, Postmark, etc.).
Use `-all` (hard fail) once you are confident all legitimate senders are listed.

### DKIM

Your ESP will generate a DKIM key pair. They provide the public key as a TXT record, e.g.:

```
<selector>._domainkey.klikk.co.za.  TXT  "v=DKIM1; k=rsa; p=<public_key>"
```

Follow your ESP's DKIM setup guide and verify with `dig TXT <selector>._domainkey.klikk.co.za`.

### DMARC

```
_dmarc.klikk.co.za.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc-reports@klikk.co.za; ruf=mailto:dmarc-reports@klikk.co.za; fo=1"
```

Start with `p=none` (monitor only). Promote to `p=quarantine` after 30 days of clean reports,
then `p=reject` after another 30 days.

---

## Warmup schedule

Sending from a new domain triggers spam filters if volume spikes suddenly. Ramp slowly:

| Week | Daily volume cap | Notes |
|------|-----------------|-------|
| 1 | 50 emails/day | Staff + beta users only |
| 2 | 200 emails/day | First real agent accounts |
| 3 | 500 emails/day | |
| 4 | 1 000 emails/day | |
| 5–6 | 2 000 emails/day | |
| 7+ | Remove cap | Monitor bounce/complaint rates |

**Stop the warmup and investigate if:**
- Bounce rate > 2 %
- Spam complaint rate > 0.1 %
- Major ISP (Gmail, Outlook) starts bulk-foldering

### Engagement signals

Send only to confirmed users. Never purchase lists. Use double opt-in for marketing email.
Transactional email (leases, rent, password reset) is exempt from unsubscribe but must still
comply with POPIA (data is processed under legitimate interest / contractual necessity).

---

## ESP recommendation

For v1 scale (< 10 000 emails/month), **Amazon SES** is the most cost-effective option
available in `af-south-1` (Cape Town region). Monthly free tier: 62 000 emails.

Setup steps:
1. Verify the domain `klikk.co.za` in SES (adds DNS records above automatically).
2. Set `EMAIL_BACKEND = 'django_ses.SESBackend'` in production settings.
3. Install `django-ses` in `requirements.txt`.
4. Add `AWS_SES_REGION_NAME = 'af-south-1'` to settings.
5. Request production access (exit the SES sandbox) via the AWS console — required
   to send to unverified recipients.

---

## Testing

- **Local dev:** `EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend`
- **Integration test:** use [Mailpit](https://mailpit.axllent.org/) (`docker run -p 1025:1025 -p 8025:8025 axllent/mailpit`)
  then set `EMAIL_HOST=localhost EMAIL_PORT=1025` — all emails land in the Mailpit web UI.
- **Pre-launch quality check:** send to [mail-tester.com](https://www.mail-tester.com/) — target score ≥ 9/10.
  Check: SPF pass, DKIM pass, DMARC pass, no blacklist hits, valid unsubscribe link.

---

## Monitoring

| Signal | Tool | Threshold |
|--------|------|-----------|
| Bounce rate | SES dashboard / bounce SNS topic | Alert > 2 % |
| Complaint rate | SES dashboard / complaint SNS topic | Alert > 0.08 % |
| Delivery success | `NotificationLog` (channel=email, status=sent) | — |
| Failed sends | `NotificationLog` (status=failed) → Sentry | Alert on spike |

Set up SNS → Lambda (or direct → Klikk API endpoint) to ingest SES bounce/complaint
notifications and auto-suppress those addresses.

---

## POPIA compliance notes

- Only send to users who have accepted Klikk's terms or who have an active contractual
  relationship (tenant, agent, owner).
- Every marketing or non-essential email must include an **unsubscribe link**.
- Transactional emails (lease/rent/security) are sent under legitimate interest and do
  not require a separate marketing consent, but must still be proportionate and relevant.
- Information Officer contact: **privacy@klikk.co.za** — included in every email footer.
- Data subject access requests for email logs: respond within 30 days per POPIA s.23.
