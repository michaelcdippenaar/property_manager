# Klikk — Backup & Restore Runbook

> Ops team reference for the automated nightly backup pipeline and the monthly
> restore drill procedure.  Run all commands from the repo root on the server
> (`~/apps/property_manager`).

---

## 1. Overview

| What | How | Frequency | Destination |
|------|-----|-----------|-------------|
| Postgres database | `pg_dump --format=custom` + age encryption | Nightly 02:00 SAST | S3 `daily/` prefix |
| Monthly archive | S3-side copy of day-1 daily dump | 1st of each month | S3 `monthly/` prefix |
| Django media (incl. Vault `.enc` blobs) | `aws s3 sync --no-delete` | Nightly 02:00 SAST | S3 `media/` prefix |

S3 bucket: **`klikk-backups-af`** (af-south-1)
S3 versioning: enabled on the bucket (AWS console — do not disable)

S3 lifecycle rules (set in AWS console — not managed by this repo):

| Rule | Transition | Expiry |
|------|-----------|--------|
| `daily/*` | Standard → Glacier IR after 30 days | Expire after 30 days |
| `monthly/*` | Standard → Glacier IR after 365 days | Expire after 395 days |
| `media/*` | (versioned — no expiry on current version) | Non-current → Glacier after 90 days |

---

## 2. IAM Backup User

A dedicated IAM user (`klikk-backup`) is used for all backup operations.

**Policy (attach to `klikk-backup` in AWS IAM):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BackupWriteList",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetBucketVersioning",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::klikk-backups-af",
        "arn:aws:s3:::klikk-backups-af/*"
      ]
    }
  ]
}
```

Note: `s3:DeleteObject` is intentionally absent.  The backup user cannot delete
objects.  Monthly prune / Glacier transitions happen via lifecycle rules only.

Store the access key + secret in Bitwarden under **"Klikk → Backup IAM credentials"**.

---

## 3. age Encryption

Backups are encrypted with [age](https://age-encryption.org/) before upload.
A **recipient public key** (`AGE_PUBLIC_KEY`) is stored in `backend/.env.secrets`.
The **private key** (needed to decrypt/restore) is stored in Bitwarden under
**"Klikk → Backup age private key"**.

Generate a new keypair (run locally, save private key to Bitwarden immediately):
```bash
age-keygen -o klikk-backup-age.key
# output: Public key: age1xxxxxxxxxxxxxxxxxxxxxxxx
# add the public key to backend/.env.secrets as AGE_PUBLIC_KEY=age1xxx...
# copy klikk-backup-age.key contents to Bitwarden, then delete the file
```

---

## 4. Environment Variables

### 4a. Non-secret config (committed — `backend/.env.staging` / `backend/.env.production`)

These are safe to commit.  They differ between staging and production:

| Variable | Staging | Production |
|----------|---------|-----------|
| `BACKUP_S3_BUCKET` | `klikk-backups-af` | `klikk-backups-af-prod` |
| `BACKUP_S3_PREFIX` | `klikk-staging` | `klikk-production` |
| `BACKUP_AWS_REGION` | `af-south-1` | `af-south-1` |

**Staging-first deployment:** provision and test on staging before enabling
production.  The non-secret stubs are already present in `backend/.env.staging`.

### 4b. Secrets (`backend/.env.secrets` — never committed)

Add these lines to the secrets file on every server:

```bash
# ── Backup ────────────────────────────────────────────────────────────────────
# IAM user klikk-backup (write + list, no delete)
# Retrieve from Bitwarden "Klikk → Backup IAM credentials"
AWS_ACCESS_KEY_ID=<klikk-backup IAM key>
AWS_SECRET_ACCESS_KEY=<klikk-backup IAM secret>
# Canonical env var name; script also accepts legacy alias AGE_PUBLIC_KEY.
BACKUP_ENCRYPTION_KEY=age1<...>             # recipient public key (NOT the private key)
SLACK_WEBHOOK_URL=https://hooks.slack.com/... # optional; set for failure alerts
ALERT_EMAIL=mc@tremly.com                    # optional; backup failure email
```

### 4c. Graceful skip (CI / pre-provisioning)

`backup.sh` checks for infrastructure credentials before running.  If
`BACKUP_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`BACKUP_ENCRYPTION_KEY`, or `BACKUP_AWS_REGION` are absent the script logs a
`SKIP:` message and exits **0** (non-fatal).  This means:
- CI pipelines that execute `backup.sh` will not fail while infra is unprovisioned.
- Staging containers will start cleanly and attempt a real backup once secrets are populated.

Database variables (`DB_HOST`, `DB_PASSWORD`, etc.) remain fatal — a missing DB
password is always a misconfiguration.

### 4d. Env var aliases

| Canonical name | Legacy alias | Notes |
|----------------|-------------|-------|
| `BACKUP_ENCRYPTION_KEY` | `AGE_PUBLIC_KEY` | Script promotes legacy value automatically |
| `BACKUP_AWS_REGION` | `AWS_DEFAULT_REGION` | Script promotes legacy value; AWS CLI still reads `AWS_DEFAULT_REGION` |

---

## 5. Starting the Backup Service

The backup service runs in a separate Docker Compose file layered on top of the
main stack.  Use the appropriate base file for your environment:

```bash
ssh mc@<server>
cd ~/apps/property_manager

# Staging (recommended first deployment target — uses klikk-backups-af bucket)
docker compose \
  -f deploy/docker-compose.staging.yml \
  -f deploy/docker-compose.backup.yml \
  -f deploy/docker-compose.backup.staging.yml \
  up -d backup drill_reminder

# Production (uses klikk-backups-af-prod bucket via .env.production)
docker compose \
  -f deploy/docker-compose.prod.yml \
  -f deploy/docker-compose.backup.yml \
  up -d backup drill_reminder

# View backup logs
docker compose \
  -f deploy/docker-compose.prod.yml \
  -f deploy/docker-compose.backup.yml \
  logs -f backup
```

---

## 6. Triggering a Manual Backup

```bash
# Staging
docker compose \
  -f deploy/docker-compose.staging.yml \
  -f deploy/docker-compose.backup.yml \
  -f deploy/docker-compose.backup.staging.yml \
  exec backup /scripts/backup.sh

# Production
docker compose \
  -f deploy/docker-compose.prod.yml \
  -f deploy/docker-compose.backup.yml \
  exec backup /scripts/backup.sh
```

Check the exit code: `echo $?` should be `0`.
A `SKIP:` exit (code 0) means infrastructure credentials are not yet set — see
§ 4c.

---

## 7. Verifying a Backup

```bash
# List the last 5 daily dumps
aws s3 ls s3://klikk-backups-af/klikk-production/daily/ | tail -5

# Download the latest dump locally
LATEST=$(aws s3 ls s3://klikk-backups-af/klikk-production/daily/ \
  | sort | tail -1 | awk '{print $4}')
aws s3 cp "s3://klikk-backups-af/klikk-production/daily/${LATEST}" /tmp/latest.dump.age

# Verify the file is a valid age-encrypted stream (first bytes = "age-encryption.org")
head -c 30 /tmp/latest.dump.age
```

---

## 8. Restore Procedure (Restore Drill)

Run this procedure monthly and record the result in `docs/ops/restore-drills.md`.

### Prerequisites (run locally)

- `age` CLI installed (`brew install age` on macOS)
- `docker` running locally
- age private key available (from Bitwarden → "Klikk → Backup age private key")
  saved as `/tmp/klikk-backup-age.key`

### Step-by-step

```bash
# 1. Download the latest encrypted dump
LATEST=$(aws s3 ls s3://klikk-backups-af/klikk-production/daily/ \
  | sort | tail -1 | awk '{print $4}')
aws s3 cp "s3://klikk-backups-af/klikk-production/daily/${LATEST}" /tmp/latest.dump.age
echo "Downloaded: /tmp/latest.dump.age"

# 2. Record the checksum of the encrypted file
ENCRYPTED_CHECKSUM=$(sha256sum /tmp/latest.dump.age | awk '{print $1}')
echo "Encrypted checksum: ${ENCRYPTED_CHECKSUM}"
# Cross-check against the S3 object metadata:
#   aws s3api head-object --bucket klikk-backups-af \
#     --key "klikk-production/daily/${LATEST}" \
#     | jq .Metadata

# 3. Decrypt
age --decrypt \
  --identity /tmp/klikk-backup-age.key \
  --output /tmp/latest.dump \
  /tmp/latest.dump.age
echo "Decrypted dump size: $(du -sh /tmp/latest.dump | cut -f1)"

# 4. Start a fresh Postgres container
docker run -d \
  --name klikk_restore_test \
  -e POSTGRES_DB=klikk_db \
  -e POSTGRES_USER=klikk_user \
  -e POSTGRES_PASSWORD=restore_test_pass \
  -p 15432:5432 \
  postgres:16.3

# Wait for Postgres to accept connections (≈5 s)
until docker exec klikk_restore_test pg_isready -U klikk_user; do sleep 1; done

# 5. Restore the dump
PGPASSWORD=restore_test_pass pg_restore \
  --host=127.0.0.1 \
  --port=15432 \
  --username=klikk_user \
  --dbname=klikk_db \
  --no-owner \
  --no-privileges \
  /tmp/latest.dump
echo "Restore exit code: $?"

# 6. Checksum comparison — row counts for key tables
PGPASSWORD=restore_test_pass psql \
  -h 127.0.0.1 -p 15432 -U klikk_user -d klikk_db \
  -c "SELECT tablename, n_live_tup AS approx_rows
      FROM pg_stat_user_tables
      ORDER BY n_live_tup DESC
      LIMIT 20;"

# Compare counts to what you see in the production DB:
# (SSH to prod server and run the same query against the live DB)

# 7. Tear down the restore container
docker stop klikk_restore_test && docker rm klikk_restore_test
rm -f /tmp/latest.dump /tmp/latest.dump.age

# 8. Record the result in docs/ops/restore-drills.md
```

---

## 9. Failure Alerts

If `backup.sh` exits non-zero it will:

1. POST to `SLACK_WEBHOOK_URL` (if set) — fires immediately
2. Send an email to `ALERT_EMAIL` (if set) via `mailx`

If neither is set, the failure is logged to `/var/log/backup/backup.log` only.
Recommendation: always set at least one alert channel.

---

## 10. Retention Summary

| Type | Copies kept | Storage class |
|------|-------------|---------------|
| Daily dumps | 30 | S3 Standard → Glacier IR after 30 d → deleted |
| Monthly dumps | 12 | S3 Standard → Glacier IR after 365 d → deleted after 395 d |
| Media objects | indefinite (current version) | S3 Standard; non-current → Glacier after 90 d |

---

## 11. Disaster Recovery RTO / RPO

| Metric | Target |
|--------|--------|
| RPO (max data loss) | 24 hours (nightly backup) |
| RTO (time to restore) | < 2 hours (documented drill procedure) |

---

## 12. References

- `deploy/backup.sh` — backup script
- `deploy/docker-compose.backup.yml` — backup service definition
- `deploy/Dockerfile.backup` — backup container image
- `docs/ops/restore-drills.md` — timestamped drill log
- Bitwarden: "Klikk → Backup IAM credentials", "Klikk → Backup age private key"
