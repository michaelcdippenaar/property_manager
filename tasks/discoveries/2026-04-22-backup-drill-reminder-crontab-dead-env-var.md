---
discovered_by: rentals-reviewer
discovered_during: OPS-003
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: OPS
---

## What I found
`docker-compose.backup.yml` sets `CRONTAB_CONTENT: "0 8 1 * * /scripts/drill-reminder.sh"` for the `drill_reminder` service, but `Dockerfile.backup` never reads that env var. The CMD runs `supercronic /etc/crontab.backup`, which contains only the backup schedule (`0 0 * * *`). The `drill_reminder` container therefore fires `backup.sh` at midnight nightly instead of `drill-reminder.sh` on the 1st.

## Why it matters
AC-5 of OPS-003 ("drill executed monthly — cron reminder") is silently broken in production. The ops team will never receive the monthly reminder, and `backup.sh` will run twice nightly (once in each container), doubling S3 writes and potentially causing a second concurrent dump.

## Where I saw it
- `deploy/docker-compose.backup.yml:67` — `CRONTAB_CONTENT` env var set but never consumed
- `deploy/Dockerfile.backup:30-33` — hardcoded crontab and CMD; no entrypoint that reads `CRONTAB_CONTENT`

## Suggested acceptance criteria (rough)
- [ ] `drill_reminder` service uses its own crontab file (e.g. `/etc/crontab.drill`) that schedules `drill-reminder.sh` at `0 8 1 * *`, OR the Dockerfile entrypoint writes the crontab from `CRONTAB_CONTENT` before invoking supercronic
- [ ] `CRONTAB_CONTENT` env var removed from `docker-compose.backup.yml` (fix chosen was the dedicated crontab approach per reviewer recommendation)
- [ ] `backup.sh` no longer runs inside the `drill_reminder` container

## Why I didn't fix it in the current task
Out of scope for review; the implementer flagged it as a known loose end and the reviewer's role is to verify, not rewrite.
