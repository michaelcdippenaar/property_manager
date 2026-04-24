#!/usr/bin/env bash
# =============================================================================
#  Klikk — nightly backup script
#  Runs inside the `backup` Docker service (deploy/docker-compose.backup.yml)
#  or on the host via cron.
#
#  What it does:
#   1. pg_dump --format=custom → age-encrypt → upload to S3
#   2. rclone sync media/ to S3 (versioning on, no delete)
#   3. Prune daily dumps older than 30 days
#   4. Send a Slack/email alert on failure
#
#  Required environment variables:
#   DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#   BACKUP_S3_BUCKET          e.g. klikk-backups-af (env-driven; staging uses klikk-backups-af, prod klikk-backups-af-prod)
#   BACKUP_S3_PREFIX          e.g. klikk-staging or klikk-production  (no trailing slash)
#   BACKUP_ENCRYPTION_KEY     age1... recipient key (alias: AGE_PUBLIC_KEY)
#   AWS_ACCESS_KEY_ID         backup IAM user (write-only)
#   AWS_SECRET_ACCESS_KEY     backup IAM user
#   BACKUP_AWS_REGION         af-south-1 (alias: AWS_DEFAULT_REGION)
#   MEDIA_DIR                 host path to Django MEDIA_ROOT (mounted into container)
#
#  Optional:
#   SLACK_WEBHOOK_URL         if set, POSTs failure/skip JSON to this URL
#   ALERT_EMAIL               if set, sends failure email via mailx
#   MONTHLY_BACKUP_PREFIX     e.g. klikk-production/monthly  (defaults derived)
#   DEPLOY_ENV                set to "production" to enable prod-safety checks
#   BACKUP_ALLOW_SKIP_IN_PROD if set to "true", silently skip even in production
#                             (NOT recommended — for emergency break-glass use only)
#   BACKUP_HEARTBEAT_URL      dead-man's switch URL pinged after every successful
#                             S3 upload (UptimeRobot Heartbeat / healthchecks.io).
#                             The monitor must alert if no ping arrives in ~26 hours.
#
#  Graceful skip: if AWS credentials or encryption key are absent the script
#  logs a warning and exits 0 (non-fatal) so CI pipelines do not break.
#  EXCEPTION: when DEPLOY_ENV=production and BACKUP_ALLOW_SKIP_IN_PROD is not
#  "true", missing infra creds are treated as fatal (exit 1) to prevent silent
#  no-ops in prod.  Staging/CI can still skip silently.
#  The DB credential check remains fatal — a missing DB_PASSWORD is a
#  misconfiguration that should surface immediately.
# =============================================================================
set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

die() {
  log "ERROR: $*"
  _alert_failure "$*"
  exit 1
}

# Exit 0 (non-fatal) when infrastructure creds are not yet provisioned.
# In production (DEPLOY_ENV=production) this is fatal unless BACKUP_ALLOW_SKIP_IN_PROD=true.
# Always POSTs to SLACK_WEBHOOK_URL when set, so the miss is visible.
skip() {
  local MISSING="$*"
  log "SKIP: ${MISSING} — backup not configured; exiting without error (set required env vars to enable)"

  # Notify via Slack if webhook is configured (fail-open: webhook failure is non-fatal)
  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -s -X POST "${SLACK_WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      --data "{\"text\":\"backup SKIP in env=${DEPLOY_ENV:-unset} — missing creds: ${MISSING}. Host: $(hostname)\"}" \
      || log "WARNING: Slack skip-alert failed to send"
  fi

  # In production, missing infra creds are fatal unless the break-glass override is set.
  if [[ "${DEPLOY_ENV:-}" == "production" && "${BACKUP_ALLOW_SKIP_IN_PROD:-}" != "true" ]]; then
    log "ERROR: DEPLOY_ENV=production — missing infra creds are fatal. Set BACKUP_ALLOW_SKIP_IN_PROD=true to override (not recommended)."
    exit 1
  fi

  exit 0
}

_alert_failure() {
  local msg="$1"
  local subject="[Klikk Backup] FAILED on $(hostname) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    local slack_text
    slack_text=$':rotating_light: *Klikk backup FAILED*\n'"${msg}"
    curl -s -X POST "${SLACK_WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      --data "{\"text\":\"${slack_text}\"}" \
      || log "WARNING: Slack alert failed to send"
  fi

  if [[ -n "${ALERT_EMAIL:-}" ]]; then
    echo "${subject}"$'\n\n'"${msg}" \
      | mailx -s "${subject}" "${ALERT_EMAIL}" \
      || log "WARNING: email alert failed to send"
  fi

  if [[ -z "${SLACK_WEBHOOK_URL:-}" && -z "${ALERT_EMAIL:-}" ]]; then
    log "WARNING: no alert channel configured (set SLACK_WEBHOOK_URL or ALERT_EMAIL)"
  fi
}

# ── env var aliases ───────────────────────────────────────────────────────────
# BACKUP_ENCRYPTION_KEY is the canonical name; AGE_PUBLIC_KEY is the legacy alias.
# BACKUP_AWS_REGION is the canonical name; AWS_DEFAULT_REGION is the legacy alias.

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" && -n "${AGE_PUBLIC_KEY:-}" ]]; then
  BACKUP_ENCRYPTION_KEY="${AGE_PUBLIC_KEY}"
fi
export BACKUP_ENCRYPTION_KEY

if [[ -z "${BACKUP_AWS_REGION:-}" && -n "${AWS_DEFAULT_REGION:-}" ]]; then
  BACKUP_AWS_REGION="${AWS_DEFAULT_REGION}"
fi
# aws CLI reads AWS_DEFAULT_REGION; keep both in sync
export BACKUP_AWS_REGION
export AWS_DEFAULT_REGION="${BACKUP_AWS_REGION:-}"

# ── validate env ─────────────────────────────────────────────────────────────

# Infrastructure credentials — skip non-fatally if absent (CI/staging without infra)
# Collect ALL missing vars first so the Slack alert lists them all at once.
infra_vars=(
  BACKUP_S3_BUCKET BACKUP_S3_PREFIX
  BACKUP_ENCRYPTION_KEY
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY BACKUP_AWS_REGION
)
missing_infra=()
for var in "${infra_vars[@]}"; do
  [[ -n "${!var:-}" ]] || missing_infra+=("${var}")
done
if [[ ${#missing_infra[@]} -gt 0 ]]; then
  skip "Required infra env vars not set: ${missing_infra[*]}"
fi

# Database credentials — fatal if absent (misconfiguration, not missing infra)
db_vars=(DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD MEDIA_DIR)
for var in "${db_vars[@]}"; do
  [[ -n "${!var:-}" ]] || die "Required env var ${var} is not set"
done

# ── derived paths ─────────────────────────────────────────────────────────────

DATE=$(date -u +%Y-%m-%d)
MONTH=$(date -u +%Y-%m)
DAY_OF_MONTH=$(date -u +%d)

DAILY_PREFIX="${BACKUP_S3_PREFIX}/daily"
MONTHLY_PREFIX="${MONTHLY_BACKUP_PREFIX:-${BACKUP_S3_PREFIX}/monthly}"
MEDIA_S3_PREFIX="${BACKUP_S3_PREFIX}/media"

DUMP_FILE="/tmp/klikk_${DATE}.dump"
DUMP_ENC="${DUMP_FILE}.age"

# ── 1. Postgres dump + encrypt ────────────────────────────────────────────────

log "Starting Postgres dump: ${DB_NAME}@${DB_HOST}:${DB_PORT}"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --format=custom \
  --compress=6 \
  --no-password \
  "${DB_NAME}" \
  > "${DUMP_FILE}" \
  || die "pg_dump failed"

log "Dump size: $(du -sh "${DUMP_FILE}" | cut -f1)"

log "Encrypting dump with age"
age --recipient="${BACKUP_ENCRYPTION_KEY}" --output="${DUMP_ENC}" "${DUMP_FILE}" \
  || die "age encryption failed"

rm -f "${DUMP_FILE}"

DUMP_CHECKSUM=$(sha256sum "${DUMP_ENC}" | awk '{print $1}')
log "Encrypted dump checksum (sha256): ${DUMP_CHECKSUM}"

# ── 2. Upload daily dump ──────────────────────────────────────────────────────

DAILY_S3_KEY="${DAILY_PREFIX}/${DATE}.dump.age"
log "Uploading to s3://${BACKUP_S3_BUCKET}/${DAILY_S3_KEY}"

aws s3 cp "${DUMP_ENC}" "s3://${BACKUP_S3_BUCKET}/${DAILY_S3_KEY}" \
  --metadata "sha256=${DUMP_CHECKSUM},source_db=${DB_NAME},date=${DATE}" \
  || die "s3 upload (daily) failed"

# ── 3. Monthly copy (day 1 of each month) ────────────────────────────────────

if [[ "${DAY_OF_MONTH}" == "01" ]]; then
  MONTHLY_S3_KEY="${MONTHLY_PREFIX}/${MONTH}.dump.age"
  log "First of month — creating monthly copy: s3://${BACKUP_S3_BUCKET}/${MONTHLY_S3_KEY}"
  aws s3 cp \
    "s3://${BACKUP_S3_BUCKET}/${DAILY_S3_KEY}" \
    "s3://${BACKUP_S3_BUCKET}/${MONTHLY_S3_KEY}" \
    || die "s3 copy (monthly) failed"
fi

# ── 4. Prune daily dumps older than 30 days ───────────────────────────────────
# Monthly dumps are pruned by the S3 lifecycle rule after 365 days.
# Daily dumps are pruned here (belt-and-suspenders on top of the 30-day lifecycle rule).

CUTOFF_DATE=$(date -u -d "30 days ago" +%Y-%m-%d 2>/dev/null \
  || date -u -v-30d +%Y-%m-%d)  # macOS fallback

log "Pruning daily dumps older than ${CUTOFF_DATE}"

aws s3 ls "s3://${BACKUP_S3_BUCKET}/${DAILY_PREFIX}/" \
  | awk '{print $4}' \
  | while read -r key; do
      # filename format: YYYY-MM-DD.dump.age
      file_date="${key%.dump.age}"
      if [[ "${file_date}" < "${CUTOFF_DATE}" ]]; then
        log "  Deleting old dump: ${key}"
        aws s3 rm "s3://${BACKUP_S3_BUCKET}/${DAILY_PREFIX}/${key}"
      fi
    done

# ── 5. Media sync ─────────────────────────────────────────────────────────────

log "Syncing media to s3://${BACKUP_S3_BUCKET}/${MEDIA_S3_PREFIX}/"

# --no-delete: never remove objects from S3 (S3 versioning provides the safety net)
aws s3 sync "${MEDIA_DIR}" "s3://${BACKUP_S3_BUCKET}/${MEDIA_S3_PREFIX}/" \
  --no-progress \
  || die "media sync failed"

# ── 6. Dead-man's switch — heartbeat ping ─────────────────────────────────────
# Ping the heartbeat URL on every successful upload so an external monitor
# (UptimeRobot "Heartbeat" / Better Uptime / healthchecks.io) can alert if no
# ping arrives within ~26 hours.  The check is fail-open: a failed ping is
# logged but does NOT fail the backup itself.
if [[ -n "${BACKUP_HEARTBEAT_URL:-}" ]]; then
  log "Pinging dead-man's switch: ${BACKUP_HEARTBEAT_URL}"
  curl -s --max-time 10 "${BACKUP_HEARTBEAT_URL}" \
    || log "WARNING: heartbeat ping failed (backup still succeeded)"
else
  log "INFO: BACKUP_HEARTBEAT_URL not set — dead-man's switch not configured"
fi

# ── 7. Done ───────────────────────────────────────────────────────────────────

rm -f "${DUMP_ENC}"
log "Backup completed successfully. checksum=${DUMP_CHECKSUM} bucket=${BACKUP_S3_BUCKET} prefix=${BACKUP_S3_PREFIX}"
