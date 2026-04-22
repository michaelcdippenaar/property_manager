#!/usr/bin/env bash
# =============================================================================
#  Klikk — monthly restore drill reminder
#  Runs on the 1st of each month via supercronic.
#  Sends a Slack message and/or email reminding the ops team to run the drill.
# =============================================================================
set -euo pipefail

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

MONTH=$(date -u +%Y-%m)
MSG=":drill: *Klikk monthly restore drill due — ${MONTH}*\n\nRun the drill per \`docs/ops/backup-restore.md\` and log the result in \`docs/ops/restore-drills.md\`."

if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
  curl -s -X POST "${SLACK_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    --data "{\"text\":\"${MSG}\"}" \
    && log "Drill reminder sent to Slack"
fi

if [[ -n "${ALERT_EMAIL:-}" ]]; then
  echo -e "Klikk monthly restore drill due for ${MONTH}.\n\nSee docs/ops/backup-restore.md for the procedure." \
    | mailx -s "[Klikk] Monthly restore drill due — ${MONTH}" "${ALERT_EMAIL}" \
    && log "Drill reminder sent to ${ALERT_EMAIL}"
fi

log "Drill reminder done for ${MONTH}"
