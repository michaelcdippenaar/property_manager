# DNS Runbook — klikk.co.za

Zone hosted in **AWS Route 53**, region `af-south-1` (Cape Town).
EC2 instance: allocate an Elastic IP before cutting DNS (placeholder `<EC2_EIP>` below).

> **Staging-first:** Point staging-* A records first. Verify TLS + smoke on staging
> before flipping production A records.

---

## Full zone record set

### A / AAAA records (all point at the same EC2 Elastic IP)

| Record | Type | Value | TTL | Notes |
|--------|------|-------|-----|-------|
| `klikk.co.za` | A | `<EC2_EIP>` | 300 | Apex — marketing site (Astro) |
| `www.klikk.co.za` | A | `<EC2_EIP>` | 300 | Caddy redirects → `klikk.co.za` |
| `app.klikk.co.za` | A | `<EC2_EIP>` | 300 | Admin SPA |
| `agent.klikk.co.za` | A | `<EC2_EIP>` | 300 | Sunset redirect → `app.klikk.co.za`; remove after 90 days |
| `tenant.klikk.co.za` | A | `<EC2_EIP>` | 300 | Tenant web app |
| `mobile-agent.klikk.co.za` | A | `<EC2_EIP>` | 300 | Agent mobile PWA |
| `mobile-tenant.klikk.co.za` | A | `<EC2_EIP>` | 300 | Tenant mobile PWA |
| `api.klikk.co.za` | A | `<EC2_EIP>` | 300 | Django API |
| `backend.klikk.co.za` | A | `<EC2_EIP>` | 300 | Sunset redirect → `api.klikk.co.za`; remove after 90 days |
| `staging-www.klikk.co.za` | A | `<EC2_EIP>` | 60 | Staging marketing (noindex) |
| `staging-app.klikk.co.za` | A | `<EC2_EIP>` | 60 | Staging admin SPA (noindex) |
| `staging-tenant.klikk.co.za` | A | `<EC2_EIP>` | 60 | Staging tenant web app (noindex) |
| `staging-mobile-agent.klikk.co.za` | A | `<EC2_EIP>` | 60 | Staging agent PWA (noindex) |
| `staging-api.klikk.co.za` | A | `<EC2_EIP>` | 60 | Staging Django API (noindex) |

Use TTL=300 (5 min) for production records initially, raise to 3600 once stable.
Use TTL=60 (1 min) for staging records for fast rotation during smoke testing.

> AAAA records: add only if the EC2 instance has an IPv6 address assigned (requires
> a dual-stack VPC subnet). Omit for now — Route 53 will answer A queries only.

---

### Email authentication

#### SPF — `klikk.co.za` (apex)

The apex already has a Google Workspace SPF record. **Extend it** to add SES — do not
replace it.

```
klikk.co.za.  TXT  "v=spf1 include:_spf.google.com include:amazonses.com ~all"
```

When you are confident all senders are listed, harden `~all` to `-all` (hard fail).

> If the existing SPF record only has Google's entry, the update looks like:
> Old: `"v=spf1 include:_spf.google.com ~all"`
> New: `"v=spf1 include:_spf.google.com include:amazonses.com ~all"`

#### DKIM — `klikk.co.za` (SES CNAME records)

AWS SES domain verification generates three CNAME records (selectors are unique to your
account — retrieve them from the SES console under **Verified identities → klikk.co.za →
Authentication → DKIM**).

```
<selector1>._domainkey.klikk.co.za.  CNAME  <selector1>.dkim.amazonses.com.
<selector2>._domainkey.klikk.co.za.  CNAME  <selector2>.dkim.amazonses.com.
<selector3>._domainkey.klikk.co.za.  CNAME  <selector3>.dkim.amazonses.com.
```

These coexist with Google Workspace DKIM selectors — Google and SES use different
selector names so there is no conflict.

#### DMARC — `klikk.co.za` (apex)

Launch policy: `p=quarantine`. Move to `p=reject` after 30 days of clean RUA reports.

```
_dmarc.klikk.co.za.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@klikk.co.za; ruf=mailto:dmarc@klikk.co.za; fo=1; pct=100"
```

Update to `p=reject` once DMARC reports confirm no legitimate sources are failing:

```
_dmarc.klikk.co.za.  TXT  "v=DMARC1; p=reject; rua=mailto:dmarc@klikk.co.za; ruf=mailto:dmarc@klikk.co.za; fo=1; pct=100"
```

#### MX — null MX (klikk.co.za does not receive mail on the apex)

Klikk does not run an inbound mail server on the apex. Google Workspace handles
`@klikk.co.za` inbound. No changes needed here — leave Google's existing MX records
in place.

---

## Route 53 CLI snippets

Replace `<HOSTED_ZONE_ID>` with your Route 53 zone ID (e.g. `Z1A2B3C4D5E6F7`).
Replace `<EC2_EIP>` with the allocated Elastic IP address.

### Create a single A record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <HOSTED_ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "staging-api.klikk.co.za.",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "<EC2_EIP>"}]
      }
    }]
  }'
```

### Batch-create all staging A records (run once)

```bash
EC2_EIP="<EC2_EIP>"
ZONE_ID="<HOSTED_ZONE_ID>"

STAGING_RECORDS=(
  "staging-api.klikk.co.za"
  "staging-app.klikk.co.za"
  "staging-tenant.klikk.co.za"
  "staging-mobile-agent.klikk.co.za"
  "staging-www.klikk.co.za"
)

CHANGES="["
for name in "${STAGING_RECORDS[@]}"; do
  CHANGES+="{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"${name}.\",\"Type\":\"A\",\"TTL\":60,\"ResourceRecords\":[{\"Value\":\"${EC2_EIP}\"}]}},"
done
CHANGES="${CHANGES%,}]"

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch "{\"Changes\":${CHANGES}}"
```

### Batch-create all production A records (run after staging smoke passes)

```bash
EC2_EIP="<EC2_EIP>"
ZONE_ID="<HOSTED_ZONE_ID>"

PROD_RECORDS=(
  "klikk.co.za"
  "www.klikk.co.za"
  "app.klikk.co.za"
  "agent.klikk.co.za"
  "tenant.klikk.co.za"
  "mobile-agent.klikk.co.za"
  "mobile-tenant.klikk.co.za"
  "api.klikk.co.za"
  "backend.klikk.co.za"
)

CHANGES="["
for name in "${PROD_RECORDS[@]}"; do
  CHANGES+="{\"Action\":\"UPSERT\",\"ResourceRecordSet\":{\"Name\":\"${name}.\",\"Type\":\"A\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"${EC2_EIP}\"}]}},"
done
CHANGES="${CHANGES%,}]"

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch "{\"Changes\":${CHANGES}}"
```

### Update SPF record (extend, do not replace)

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <HOSTED_ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "klikk.co.za.",
        "Type": "TXT",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "\"v=spf1 include:_spf.google.com include:amazonses.com ~all\""}
        ]
      }
    }]
  }'
```

> If there is already a TXT record for `klikk.co.za` with SPF content, use
> `Action: UPSERT` — it replaces the existing record set. Ensure you include ALL
> existing TXT values in the `ResourceRecords` array (Route 53 replaces the whole
> record set, not individual entries).

### Verify records with dig

```bash
# Confirm A records resolve
dig +short staging-api.klikk.co.za A
dig +short api.klikk.co.za A

# Confirm SPF
dig +short TXT klikk.co.za | grep spf

# Confirm DKIM (replace <selector> with value from SES console)
dig +short CNAME <selector1>._domainkey.klikk.co.za

# Confirm DMARC
dig +short TXT _dmarc.klikk.co.za
```

---

## Post-provisioning checklist

- [ ] Elastic IP allocated and noted as `<EC2_EIP>`
- [ ] All staging A records created; `dig +short staging-api.klikk.co.za` returns `<EC2_EIP>`
- [ ] Caddy obtains Let's Encrypt cert for all five `staging-*` hosts (check `caddy.log`)
- [ ] `curl -sI https://staging-api.klikk.co.za/api/v1/` returns `200` or `401` (not TLS error)
- [ ] HSTS header present on all staging responses
- [ ] Staging smoke + RBAC + E2E pass (QA sign-off)
- [ ] All production A records created
- [ ] Caddy obtains Let's Encrypt cert for all production hosts
- [ ] SPF TXT record updated to include `amazonses.com`
- [ ] Three SES DKIM CNAME records created; SES console shows "Verified"
- [ ] DMARC TXT record created at `_dmarc.klikk.co.za`
- [ ] `backend.klikk.co.za` and `agent.klikk.co.za` sunset redirects confirmed working (301)
- [ ] After 30 days of clean DMARC reports: promote `p=quarantine` → `p=reject`
- [ ] After 30 days of stable prod cert: submit to HSTS preload list (hstspreload.org)
- [ ] After 90 days: remove `agent.klikk.co.za` and `backend.klikk.co.za` A records + Caddyfile blocks
