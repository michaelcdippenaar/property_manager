---
id: RNT-QUAL-009
stream: rentals
title: "Maintenance SLA timers + overdue surfacing across agent and owner views"
feature: full_maintenance_workflow
lifecycle_stage: 11
priority: P1
effort: S
v1_phase: "1.0"
status: review
asana_gid: "1214177140664256"
assigned_to: reviewer
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
