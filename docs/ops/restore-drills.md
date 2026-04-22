# Klikk — Restore Drill Log

Monthly drill procedure: see `docs/ops/backup-restore.md`.

Each drill entry must include:
- Date performed
- Operator
- Dump file restored (date + S3 key)
- Encrypted checksum vs S3 metadata checksum (pass/fail)
- Row count comparison (key tables — note any discrepancy)
- Restore duration (approx)
- Result (PASS / FAIL)
- Notes

Drills are due on the **1st of each month**.  A Slack/email reminder fires
automatically via the `drill_reminder` container.

---

## Drill log

<!-- Add new entries at the TOP (most recent first) -->

### YYYY-MM-DD — PENDING

First drill is due after the backup service has run at least one successful
nightly backup on the production server.

To run the drill: follow `docs/ops/backup-restore.md § 8. Restore Procedure`.
Then replace this placeholder with a real entry.

---

## Entry template

```
### YYYY-MM-DD

| Field | Value |
|-------|-------|
| Operator | mc@tremly.com |
| Dump restored | YYYY-MM-DD.dump.age (s3://klikk-backups-af/klikk-production/daily/YYYY-MM-DD.dump.age) |
| Encrypted checksum | sha256:abc123... |
| S3 metadata checksum | sha256:abc123... — MATCH / MISMATCH |
| Restore duration | ~N min |
| Result | PASS / FAIL |

**Row count comparison (top tables):**

| Table | Production | Restored | Delta |
|-------|-----------|---------|-------|
| leases | 0 | 0 | 0 |
| tenants | 0 | 0 | 0 |
| properties | 0 | 0 | 0 |
| units | 0 | 0 | 0 |

**Notes:**
- Any observations or issues.
```
