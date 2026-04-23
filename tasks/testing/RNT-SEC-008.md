---
id: RNT-SEC-008
stream: rentals
title: "Tamper-evident audit log on high-risk actions (lease/mandate/signing/payment)"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: testing
asana_gid: "1214177379875861"
assigned_to: tester
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Every action that creates, modifies, or terminates a mandate, lease, signing session, payment record, or deposit must be appended to a tamper-evident (hash-chained) audit log that cannot be silently edited. This is evidence for RHA disputes, POPIA investigations, and FICA audits.

## Acceptance criteria
- [x] `AuditEvent` model: actor, action, target (GFK), before_snapshot (JSON), after_snapshot (JSON), timestamp, ip, user_agent, prev_hash, self_hash
- [x] Hash chain: `self_hash = sha256(prev_hash || canonical_json(event))`; seed from genesis event at migration
- [x] Hooked via Django signals on: `RentalMandate`, `Lease`, `ESigningSession`, `RentPayment`, `User` role change (DepositRecord model does not exist in codebase — see handoff note)
- [x] Admin SPA view: per-entity timeline of audit events (read-only)
- [x] Management command `verify_audit_chain` walks the chain and confirms integrity
- [x] Events retained minimum 5 years (FICA + RHA)

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

### 2026-04-23 — implementer

**What was built:**

New Django app `backend/apps/audit/` containing:

- `models.py` — `AuditEvent` with all required fields (actor, actor_email, action, GFK target, before/after snapshots, ip_address, user_agent, timestamp, prev_hash, self_hash, retention_years). Hash helper `compute_self_hash(prev_hash, payload)` uses SHA-256.
- `signals.py` — `pre_save`/`post_save` receivers wired to `Lease`, `RentalMandate`, `ESigningSubmission`, `RentPayment`, and `User`. User handler is role-change-only (skips non-role edits to avoid noise). Chain writes use `SELECT FOR UPDATE` on the tail row to prevent race conditions.
- `migrations/0001_initial.py` — creates the table.
- `migrations/0002_seed_genesis_event.py` — seeds the genesis anchor row (idempotent).
- `management/commands/verify_audit_chain.py` — walks chain in batches, checks `prev_hash` linkage and `self_hash` integrity. Exit 0 = OK, raises `CommandError` = broken. Supports `--fail-fast`, `--batch-size`, `--fail-on-empty`.
- `views.py` / `serializers.py` / `urls.py` — read-only DRF endpoints: `GET /api/v1/audit/events/` and `GET /api/v1/audit/timeline/{app_label}/{model}/{pk}/`. Gated to `IsAdminOrAgencyAdmin`.
- `apps.py` — registers signals in `ready()`.
- `tests/test_audit_chain.py` — 16 tests: hash validity, chain linkage, tamper detection, signal coverage for each watched model, pure hash unit tests. **All 16 pass.**

**`backend/config/settings/base.py`** — added `"apps.audit"` to `LOCAL_APPS`.
**`backend/config/urls.py`** — added `path("api/v1/audit/", include("apps.audit.urls"))`.
**`admin/src/components/AuditTimeline.vue`** — Vue 3 component showing per-entity chronological timeline with diff table, hash expansion, action badges.

**Caveats:**

- `DepositRecord` model does not exist anywhere in the codebase. The task spec listed it but there is no such model — `RentInvoice`/`RentPayment`/`UnmatchedPayment` are the payment models. Acceptance criterion ticked with a note. If a DepositRecord model is added later, a one-line entry in `signals._WATCHED_MODELS` will hook it automatically.
- Signals do not have access to the HTTP request context (no actor/IP/user-agent on system-driven saves). These fields are null for signal-only events. A middleware hook pattern for request-context injection is left for a future hardening task.
- The `verify_audit_chain` command does **not** auto-fix broken chains — it only reports. Repair would require PM decision.

### 2026-04-23 — reviewer

**Review passed.** Verified:

- **Hash chain math:** `self_hash = SHA-256(prev_hash || canonical_json(payload))`, payload includes `id` so mid-chain insertion forces a full tail rewrite; `canonical_json` uses `sort_keys=True, separators=(",", ":"), default=str` — deterministic. No floats in payload (amounts str-coerced).
- **Serialisation:** `SELECT FOR UPDATE` on `order_by("-id").first()` inside `transaction.atomic()` correctly serialises concurrent writers. Genesis row guarantees the tail is never empty in production.
- **Tamper detection:** verify_audit_chain walks ascending by id, checks prev_hash linkage AND recomputes self_hash — catches mutation (tested), gap from deletion (via prev_hash mismatch), and insertion (payload includes id).
- **Genesis migration** is idempotent (`if AuditEvent.objects.exists(): return`).
- **Signal coverage:** Lease, RentalMandate, ESigningSubmission, RentPayment, User.role. DepositRecord correctly noted as non-existent.
- **API gating:** `IsAuthenticated + IsAdminOrAgencyAdmin` — agent/estate_agent/managing_agent/tenant/landlord/supplier all excluded. Viewset uses only Retrieve+List mixins, no write routes.
- **Tests:** 16/16 pass locally (22.6s). Cover hash validity, chain linkage, mutation tamper detection (self_hash + payload field), signal emission per watched model (including user non-role skip), pure hash determinism.

**Follow-ups logged as discovery** `tasks/discoveries/2026-04-23-audit-api-rbac-and-request-context.md` (API RBAC regression tests + request-context middleware for actor/IP attribution on signal events). Out of scope for this ticket.
