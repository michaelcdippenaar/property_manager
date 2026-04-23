---
id: RNT-QUAL-009
stream: rentals
title: "Maintenance SLA timers + overdue surfacing across agent and owner views"
feature: maintenance_workflow
lifecycle_stage: 11
priority: P1
effort: S
v1_phase: "1.0"
status: testing
asana_gid: "1214177140664256"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Each maintenance ticket has a target SLA based on priority (emergency = 4h ack / 24h resolve; urgent = 24h / 72h; routine = 72h / 14d). Surface countdown and overdue on agent dashboard, supplier view, and owner dashboard.

## Acceptance criteria
- [x] `MaintenanceTicket.sla_ack_deadline` + `sla_resolve_deadline` computed from priority
- [x] Countdown chip on ticket list (green > 50%, yellow 20–50%, red < 20% or overdue)
- [x] Agent dashboard: widget "Overdue maintenance" with count + CTA
- [x] Owner dashboard: same widget scoped to their properties
- [x] Beat task: auto-escalate (notify agency admin) on overdue by >48h
- [x] SLA rules tuneable per agency

## Files likely touched
- `backend/apps/maintenance/models.py`
- `backend/apps/maintenance/tasks.py`
- `admin/src/views/maintenance/TicketList.vue`
- `admin/src/components/SLACountdownChip.vue` (new)

## Test plan
**Automated:**
- `pytest backend/apps/maintenance/tests/test_sla.py`

**Manual:**
- Create emergency ticket → chip shows 4h countdown → roll forward time → chip goes red → escalation email sent

## Handoff notes

### 2026-04-22 — implementer

**What was done:**

1. **Backend model changes** (`backend/apps/maintenance/models.py`):
   - Added `DEFAULT_SLA_HOURS` dict mapping priority → `(ack_hours, resolve_hours)`. Urgent=4h/24h, High=24h/72h, Medium/Low=72h/336h (14d).
   - Added `AgencySLAConfig` model with a FK to `Agency` + per-priority override. `get_hours(agency, priority)` classmethod falls back to defaults.
   - Added `sla_ack_deadline`, `sla_resolve_deadline` (DateTimeField, nullable), and `sla_escalated` (BooleanField) fields to `MaintenanceRequest`.
   - Added `sla_ack_pct`, `sla_resolve_pct`, and `is_sla_overdue` computed properties.

2. **Signal** (`backend/apps/maintenance/signals.py`): `set_sla_deadlines` receiver fires on `MaintenanceRequest` post_save; uses `update()` to avoid recursion.

3. **Migration**: `0015_sla_deadlines_and_agency_config.py` — clean, no data migration needed (deadlines computed on next save/signal).

4. **Beat task** (`backend/apps/maintenance/tasks.py`): `escalate_overdue_maintenance()` — finds tickets with `sla_resolve_deadline < now - 48h`, `sla_escalated=False`, open/in-progress; sends email to agency admins; marks `sla_escalated=True`. Written as a plain function (no Celery decorator) so it can be scheduled via any beat runner. Reviewer should wire it into CELERY_BEAT_SCHEDULE or equivalent.

5. **Overdue API endpoint** (`/maintenance/overdue/`): DRF action on `MaintenanceRequestViewSet`. Scoped by role: owner sees only their properties, agents see accessible properties, admin sees all.

6. **Serializer**: Added `sla_ack_pct`, `sla_resolve_pct`, `is_sla_overdue` read-only fields.

7. **Admin**: Registered `AgencySLAConfig` in Django admin.

8. **Frontend** (`admin/src/components/SLACountdownChip.vue`): New component — shows countdown (e.g. "3h left") with green/yellow/red colour based on `resolvePct`. Hidden for resolved/closed tickets.

9. **Frontend** (`admin/src/views/maintenance/RequestsView.vue`): Chip inserted in the ticket card badge row.

10. **Frontend** (`admin/src/components/OverdueMaintenanceWidget.vue`): Widget that calls `/maintenance/overdue/`, shows list of overdue tickets with hours-overdue label and priority badge. Has a "View all →" CTA. Self-hides when count = 0.

11. **Frontend**: Widget added to `AgencyDashboardView.vue` (agent/admin view) and `OwnerDashboard.vue` (owner-scoped via backend).

12. **Tests** (`backend/apps/maintenance/tests/test_sla.py`): 15 tests passing. Cover default SLA hours, agency overrides, deadline computation, pct properties, `is_sla_overdue`, escalation task marking, no-re-escalation.

**Caveats for reviewer:**
- The beat task is a plain Python function, not a `@shared_task`. Reviewer should confirm whether Celery is available and wire it up, or use an alternative (e.g. Django management command + cron). A discovery note is **not** filed since this is in scope — just needs the wiring.
- Existing tickets in the DB won't have `sla_ack_deadline` set until they are next saved. A one-off management command to backfill could be added if needed (the `compute_sla_deadlines` method on the model makes this trivial).
- The `MaintenanceRequest.Priority` choices in the existing code use `urgent/high/medium/low` — the task spec mentioned "emergency/urgent/routine" but those were conceptual labels; the implementation maps them as: emergency=urgent, urgent=high, routine=medium/low. This is consistent with the existing DB data.

### 2026-04-22 — reviewer: changes requested

Two blockers must be fixed before this can proceed to testing.

**1. Signal does not re-compute deadlines on priority change — `backend/apps/maintenance/signals.py:135`**

The docstring says "first created or its priority changes" but the guard reads:
```python
if not instance.sla_ack_deadline or not instance.sla_resolve_deadline:
```
Once deadlines are written, a subsequent save (e.g. agent escalates `medium` → `urgent`) will not recalculate. The deadline stays at 14 days instead of switching to the 4h/24h window. Fix: also trigger when `created=True`, and when `update_fields` is `None` (full save) or contains `"priority"`. Simplest safe approach:

```python
should_compute = (
    created
    or not instance.sla_ack_deadline
    or not instance.sla_resolve_deadline
    or (update_fields is None)
    or ("priority" in (update_fields or []))
)
```

Add a test to `test_sla.py`: create urgent ticket → update priority to medium → assert resolve deadline extended.

**2. Beat task is unwired — acceptance criterion "Beat task: auto-escalate on overdue by >48h" is not satisfied**

`escalate_overdue_maintenance()` in `backend/apps/maintenance/tasks.py` is a plain Python function with no `@shared_task` decorator and no entry in `CELERY_BEAT_SCHEDULE`. No `celery.py` or `celeryconfig.py` exists in the project. The function is correct and well-tested, but it will never run automatically. This is an in-scope delivery gap, not reviewer housekeeping.

Required: either (a) add `@shared_task` + a `CELERY_BEAT_SCHEDULE` entry in `backend/core/settings.py`, or (b) create a Django management command `call_command("escalate_overdue_maintenance")` + document a cron entry, or (c) file a discovery for Celery setup and mark this criterion explicitly deferred in the task. Do not leave it silently unwired.

**3. Minor — `feature` field in task YAML**

Task header has `feature: full_maintenance_workflow` but `content/product/features.yaml` has `maintenance_workflow`. Update the header field to match the canonical key so tooling that reads the field stays consistent.

No security issues found. Auth on `/maintenance/overdue/` inherits `IsAuthenticated` from the viewset. Role scoping is consistent with `get_queryset`. ORM queries are parameterised. No PII logged. SLA fields are correctly `read_only` in the serializer.

### 2026-04-22 — implementer (re-submission)

**Fix 1 — signal recalculates on priority change (`backend/apps/maintenance/signals.py:135`)**

Replaced the bare `if not instance.sla_ack_deadline or not instance.sla_resolve_deadline:` guard with a `should_compute` block that also fires when `created=True`, `update_fields is None` (full save), or `"priority"` is in `update_fields`. The existing self-loop guard (skip when `update_fields` contains `"sla_ack_deadline"`) is preserved so the `update()` call doesn't recurse.

Added `TestSLADeadlineRecomputeOnPriorityChange.test_priority_change_recalculates_deadlines` to `test_sla.py`: creates an urgent ticket, then saves with priority=medium and asserts the resolve deadline extended to the medium window (~336h).

**Fix 2 — beat task wired as management command (`backend/apps/maintenance/management/commands/escalate_overdue_maintenance.py`)**

No Celery is configured in this project (no `celery.py`, no `celeryconfig.py`, no Celery in settings). The underlying `escalate_overdue_maintenance()` function in `tasks.py` is correct and unchanged. Added a Django management command that calls it, plus a `--dry-run` flag. Cron guidance is documented in the command's module docstring:

```
0 * * * * /path/to/venv/bin/python /path/to/manage.py escalate_overdue_maintenance >> /var/log/klikk/sla_escalation.log 2>&1
```

When Celery Beat is introduced in a future task, the command docstring notes that `tasks.escalate_overdue_maintenance` can be decorated with `@shared_task` and registered in `CELERY_BEAT_SCHEDULE`; the management command can then be retired.

**Fix 3 — `feature` YAML key**

Already correct in the working copy (`feature: maintenance_workflow`). No change needed.

### 2026-04-22 — reviewer: Review passed

All three blockers from the previous cycle are resolved.

1. **Signal priority-change guard** (`backend/apps/maintenance/signals.py:135`): the `should_compute` block matches the exact spec given in round 1. The anti-recursion guard (exit on `sla_ack_deadline` in `update_fields`) is preserved and fires first, so no infinite loop is possible. Logic verified in source.

2. **Beat task wired** (`backend/apps/maintenance/management/commands/escalate_overdue_maintenance.py`): clean Django management command wrapping the unchanged `tasks.escalate_overdue_maintenance()` function. `--dry-run` flag re-queries rather than re-using the same `tasks.py` logic, which is acceptable. No Celery in project confirmed. Cron guidance and future `@shared_task` migration path documented in the module docstring. The acceptance criterion is satisfied.

3. **Feature YAML key**: `feature: maintenance_workflow` in task header matches canonical key in `content/product/features.yaml:185`. Confirmed.

4. **New test** (`backend/apps/maintenance/tests/test_sla.py`, `TestSLADeadlineRecomputeOnPriorityChange`): covers urgent→medium priority downgrade and asserts both extension of deadline and rough sanity against expected hours. `timedelta` import is present at module level (line 16). Test is correct.

5. **Security pass (re-confirmed)**: no new endpoints introduced in this commit. Existing `/maintenance/overdue/` auth and role-scoping unchanged. No raw SQL, no PII logged, no secrets.

No outstanding issues. Proceed to test plan: `pytest backend/apps/maintenance/tests/test_sla.py` + manual emergency-ticket countdown scenario.

### 2026-04-22 — tester

**Test run**

- `pytest backend/apps/maintenance/tests/test_sla.py` — **16 passed** (39.47s). All default SLA hours, agency override, deadline computation, pct properties, overdue flag, escalation marking, no-re-escalation, and priority-change recompute tests pass.
- Manual UI — "Create emergency ticket → chip shows 4h countdown → roll forward time → chip goes red → escalation email sent" — **BLOCKED: untestable locally.** The time-rollforward and escalation-email steps require either a Django `freeze_time` / shell time-travel helper or a local mail sink (e.g. Mailpit/MailHog). Neither is configured in the dev environment. The component logic and escalation task are verified correct by code review (SLACountdownChip.vue colour thresholds match spec; management command wired). Test plan must be updated to either (a) add a pytest test using `freezegun` for the time-roll scenario + assert `sla_escalated=True`, or (b) explicitly accept that the time-rollforward step is covered by existing unit tests and drop the live-UI time-travel requirement.

## Reconciliation note (2026-04-23)
Unblocked during reconciliation pass. All 6 code ACs are [x]; 16/16 pytest tests pass. Blocked only on manual UI time-rollforward step (emergency ticket → chip turns red → escalation email). This is a human-only validation step requiring a running dev environment with a mail sink. Moved from blocked → testing.
Remaining: MC or human tester to create an emergency maintenance ticket, advance system time past the 4h SLA window, and confirm the SLACountdownChip turns red and the escalation management command sends the expected email.
