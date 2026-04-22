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

## 4. Required Secrets (`backend/.env.secrets`)

Add these lines to the secrets file on every server:

```bash
# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_S3_BUCKET=klikk-backups-af
BACKUP_S3_PREFIX=klikk-production          # or klikk-staging
AWS_DEFAULT_REGION=af-south-1
AWS_ACCESS_KEY_ID=<klikk-backup IAM key>
AWS_SECRET_ACCESS_KEY=<klikk-backup IAM secret>
AGE_PUBLIC_KEY=age1<...>                    # recipient public key (NOT the private key)
SLACK_WEBHOOK_URL=https://hooks.slack.com/... # optional; set for failure alerts
ALERT_EMAIL=mc@tremly.com                    # optional; backup failure email
```

---

## 5. Starting the Backup Service

The backup service runs in a separate Docker Compose file that is layered on top
of the main production stack:

```bash
ssh mc@<server>
cd ~/apps/property_manager

# Start/restart backup service alongside production stack
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
docker compose \
  -f deploy/docker-compose.prod.yml \
  -f deploy/docker-compose.backup.yml \
  exec backup /scripts/backup.sh
```

Check the exit code: `echo $?` should be `0`.

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
