---
discovered_by: rentals-reviewer
discovered_during: OPS-003
discovered_at: 2026-04-24
priority_hint: P0
suggested_prefix: OPS
---

## What I found
`deploy/backup.sh` graceful-skip path (exit 0 with `SKIP:` log) fires any time
infrastructure env vars are absent. There is no guard that distinguishes
"staging/CI without infra yet" from "production deployed with a misconfigured
secrets file." The skip path does not call `_alert_failure()`, so a prod
container with missing creds will no-op every night forever with no Slack / no
email — the operator finds out only when a restore is needed.

## Why it matters
This is the scenario backups exist to prevent. Silent failure on the backup
path = data loss on the restore path. Everyone we onboard before this is fixed
is riding unmonitored backups.

## Where I saw it
- `deploy/backup.sh` lines ~95-101 (`skip()` called from the `infra_vars` loop)
- `deploy/backup.sh` lines 42-48 (`skip()` helper — no Slack/email)
- `docs/ops/backup-restore.md` § 4c acknowledges the behaviour but offers no
  production guard

## Suggested acceptance criteria (rough)
- [ ] Distinguish `DEPLOY_ENV=production` (or equivalent) — missing infra creds
      are fatal (`die()`), not a skip
- [ ] When skipping in non-prod, still POST to `SLACK_WEBHOOK_URL` if set, so
      the miss is visible
- [ ] Add a monitoring hook (UptimeRobot heartbeat URL or dead-man's switch)
      that confirms a real backup landed in S3 in the last ~26h — pure
      exit-code 0 is insufficient signal

## Why I didn't fix it in the current task
This reshapes the skip contract and needs a PM call on which env-var signals
"production" in our stack (`DEPLOY_ENV`, `DJANGO_SETTINGS_MODULE`, something
new). Out of scope for OPS-003 as scoped; belongs in a follow-up.
