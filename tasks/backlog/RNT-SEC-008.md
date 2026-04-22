---
id: RNT-SEC-008
stream: rentals
title: "Tamper-evident audit log on high-risk actions (lease/mandate/signing/payment)"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177379875861"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Every action that creates, modifies, or terminates a mandate, lease, signing session, payment record, or deposit must be appended to a tamper-evident (hash-chained) audit log that cannot be silently edited. This is evidence for RHA disputes, POPIA investigations, and FICA audits.

## Acceptance criteria
- [ ] `AuditEvent` model: actor, action, target (GFK), before_snapshot (JSON), after_snapshot (JSON), timestamp, ip, user_agent, prev_hash, self_hash
- [ ] Hash chain: `self_hash = sha256(prev_hash || canonical_json(event))`; seed from genesis event at migration
- [ ] Hooked via Django signals on: `RentalMandate`, `Lease`, `ESigningSession`, `RentPayment`, `DepositRecord`, `User` role change
- [ ] Admin SPA view: per-entity timeline of audit events (read-only)
- [ ] Management command `verify_audit_chain` walks the chain and confirms integrity
- [ ] Events retained minimum 5 years (FICA + RHA)

## Files likely touched
- `backend/apps/audit/models.py` (new app)
- `backend/apps/audit/signals.py`
- `backend/apps/audit/management/commands/verify_audit_chain.py`
- `admin/src/components/AuditTimeline.vue`

## Test plan
**Automated:**
- `pytest backend/apps/audit/tests/` — chain breaks are detected; every signal emits exactly one event

**Manual:**
- Run `verify_audit_chain` on staging → passes
- Manually tamper with a row in DB → re-run verify → fails and points to the broken link

## Handoff notes
