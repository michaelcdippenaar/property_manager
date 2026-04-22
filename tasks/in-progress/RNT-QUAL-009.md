---
id: RNT-QUAL-009
stream: rentals
title: "Maintenance SLA timers + overdue surfacing across agent and owner views"
feature: full_maintenance_workflow
lifecycle_stage: 11
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177140664256"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Each maintenance ticket has a target SLA based on priority (emergency = 4h ack / 24h resolve; urgent = 24h / 72h; routine = 72h / 14d). Surface countdown and overdue on agent dashboard, supplier view, and owner dashboard.

## Acceptance criteria
- [ ] `MaintenanceTicket.sla_ack_deadline` + `sla_resolve_deadline` computed from priority
- [ ] Countdown chip on ticket list (green > 50%, yellow 20–50%, red < 20% or overdue)
- [ ] Agent dashboard: widget "Overdue maintenance" with count + CTA
- [ ] Owner dashboard: same widget scoped to their properties
- [ ] Beat task: auto-escalate (notify agency admin) on overdue by >48h
- [ ] SLA rules tuneable per agency

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
