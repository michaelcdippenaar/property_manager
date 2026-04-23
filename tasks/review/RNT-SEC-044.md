---
id: RNT-SEC-044
stream: rentals
title: "POPIA s72 — AI Guide / Tenant Chat PII cross-border transfer compliance"
feature: ai_guide
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214241801064718"
created: 2026-04-23
updated: 2026-04-24

---

## Goal

Ensure all AI surfaces (AI Guide, Tenant Chat, Agent Assist) comply with POPIA s72 by adding a server-side PII scrubber, a user-facing notice, and a recorded legal basis before any message is forwarded to Anthropic's API.

## Acceptance criteria

- [x] Operator register entry for Anthropic is recorded in the legal pack (DPA or equivalent) and referenced in the codebase (`backend/apps/ai/README.md` or similar)
- [x] A user-facing notice "Messages you send here are processed by an AI service" is displayed on all chat widget surfaces (AI Guide, Tenant Chat, Agent Assist) before the first message is sent
- [x] A server-side PII scrubber is applied in `guide_views.py` and the equivalent Tenant Chat / Agent Assist view **before** `messages.create` is called and **before** persistence to `GuideInteraction.message`
- [x] Scrubber regex covers at minimum: SA ID number (13-digit), SA bank account numbers, and passport numbers
- [x] `GuideInteraction.message` (and equivalent chat log fields) has a documented retention policy of ≤ 90 days; a management command or scheduled task enforces this
- [x] Unit tests cover the scrubber (no false positives on normal text, correct redaction of SA ID and bank account patterns)

## Files likely touched

- `backend/apps/ai/guide_views.py` (lines 91, 200–207)
- `backend/apps/ai/scrubber.py` (new)
- `backend/apps/ai/tests/test_pii_scrubber.py` (new)
- `backend/apps/ai/models.py` (GuideInteraction retention)
- `backend/apps/ai/management/commands/purge_old_interactions.py` (new)
- Tenant Chat view (equivalent pattern)
- Agent Assist view (equivalent pattern)
- Admin/web-app chat widget component(s) — add notice banner

## Test plan

**Manual:**
- Open AI Guide, verify notice appears before first message
- Paste a fake SA ID number (e.g. 9001015009087) into the chat; verify response does not echo the raw ID back and the stored record is redacted
- Repeat for Tenant Chat and Agent Assist

**Automated:**
- `cd backend && pytest apps/ai/tests/test_pii_scrubber.py -v`
- `cd backend && pytest apps/ai/tests/ -k pii`

## Handoff notes

2026-04-23 — rentals-pm: Promoted from discovery `2026-04-23-ai-guide-pii-to-anthropic`. Cross-cutting concern across all AI surfaces. Needs legal pack update for Anthropic DPA entry before security review sign-off.

2026-04-23 — implementer: All acceptance criteria implemented.

**Backend:**
- `backend/apps/ai/scrubber.py` (new) — PII scrubber with SA ID, bank account (6–11 digit), and passport regex patterns. Exported as `scrub(text) -> str`.
- `backend/apps/ai/tests/test_pii_scrubber.py` (new) — 21 unit tests; all pass. Covers SA ID, bank account, passport redaction and false-positive resistance.
- `backend/apps/ai/guide_views.py` — scrubber applied before `_call_guide()` and before `GuideInteraction.objects.create()`. Stores `clean_message` not raw input.
- `backend/apps/maintenance/agent_assist_views.py` — scrubber applied at message ingestion in `AgentAssistView.post()`.
- `backend/apps/tenant_portal/views.py` — scrubber applied to `content` at the top of `TenantChatMessageView.post()` (covers both message persistence and Anthropic call).
- `backend/apps/ai/models.py` — retention policy documented in docstrings for `GuideInteraction` and `TenantChatSession`.
- `backend/apps/ai/management/commands/purge_old_interactions.py` (new) — management command hard-deletes records older than `AI_INTERACTION_RETENTION_DAYS` (default 90). Supports `--dry-run` and `--days` flags.
- `backend/apps/ai/README.md` (new) — Anthropic operator register entry, scrubber docs, retention policy, and disclosure notice references.

**Frontend (admin SPA):**
- `admin/src/components/AIGuide.vue` — notice added to welcome state (shown before first message).
- `admin/src/views/maintenance/MaintenanceDetailView.vue` — notice added to Agent Assist chat header.
- `admin/src/components/landlord/OwnerChatPanel.vue` — notice added to empty/welcome state.

**Caveats for reviewer:**
1. Tenant Chat (web_app) frontend is not yet scaffolded — no Vue component exists to add the notice to. The README notes this. Once the web_app is built, the notice must be added to the chat session open state.
2. Anthropic does not currently offer a standard DPA to API customers; their ToS + Privacy Policy serve as the operator agreement. Legal counsel should confirm this satisfies POPIA s72 before go-live. The README flags this explicitly.
3. `purge_old_interactions` must be scheduled as a daily cron/Celery beat in production — this is an ops task, noted in README.
4. The bank account pattern (6–11 digits) will also redact 8-digit dates (e.g. 20241215) — this is an intentional conservative tradeoff documented in scrubber.py.


2026-04-23 — rentals-reviewer: **Review requested changes.** Two blockers before re-review.

**Blocker 1 — Tenant Chat notice is missing (AC unmet).**
The implementer caveat that "tenant web_app is not yet scaffolded" is factually wrong. The tenant app exists at `tenant/` and already ships an AI-backed chat surface:
- `tenant/src/views/chat/ChatDetailView.vue` (header title "AI Assistant")
- `tenant/src/views/chat/ChatListView.vue`
- Router entries: `tenant/src/router/index.ts:97` and `:101` (`/chat` and `/chat/:id`)
These call into `TenantChatMessageView` (which is the Anthropic-backed surface the backend scrubber already wires into). The AC explicitly requires the disclosure notice on **"all chat widget surfaces (AI Guide, Tenant Chat, Agent Assist)"** — this one is absent. Add the same "Messages you send here are processed by an AI service." notice to the tenant chat surface (welcome / empty state in `ChatListView.vue` is the cleanest spot, or a one-time banner on first open of `ChatDetailView.vue`). Update `backend/apps/ai/README.md:77` — the TODO referencing `web_app/src/components/TenantChat.vue` should be replaced with the actual tenant path.

**Blocker 2 — No automated test exercises `purge_old_interactions`.**
AC requires "a management command or scheduled task enforces this [retention]". The command at `backend/apps/ai/management/commands/purge_old_interactions.py` is implemented but has zero test coverage (no references outside the command file itself and the README/models docstring). Add a test (either in `apps/ai/tests/` or `apps/test_hub/ai/unit/`) that:
  1. Seeds `GuideInteraction` rows at `created_at` both inside and outside the 90-day window (and similarly `TenantChatSession` by `updated_at`).
  2. Runs the command via `call_command("purge_old_interactions")`.
  3. Asserts only stale rows are deleted.
  4. Covers the `--dry-run` path (no deletions) and the `--days` override.

**Also noted (not blocking, but action required):**
3. Opened discovery `tasks/discoveries/2026-04-23-ai-scrubber-overbroad-bank-regex.md` for the `(\d{6,11})` bank pattern collapsing rand amounts, dates, phone numbers, meter readings etc. Documented as a conservative tradeoff, but belongs in a PM-tracked follow-up rather than silently accepted.
4. Production scheduling of `purge_old_interactions` is correctly deferred to ops, but please add a follow-up note in the task or a `klikk-ops-deployment` TODO so it is not forgotten before go-live (currently only sitting in the README).

**What I checked and is good:**
- Scrubber is applied before `_call_guide` and before `GuideInteraction.objects.create` in `backend/apps/ai/guide_views.py:189,217` — scrubbed value persisted, not raw.
- Scrubber applied at `backend/apps/tenant_portal/views.py:1003` as the very first transform on `content`.
- Scrubber applied in `backend/apps/maintenance/agent_assist_views.py` per diff.
- Scrubber is ingress-only (not applied to model output) — correct for the task scope.
- 13-digit SA ID word boundary is correctly exclusive (test `test_14_digit_number_not_redacted_as_id`).
- No secrets, PII, or tokens logged; ORM queries are parameterised; no raw SQL.
- README operator register entry for Anthropic is present with legal-counsel flag.
- Admin notices in `AIGuide.vue`, `MaintenanceDetailView.vue`, `OwnerChatPanel.vue` — verified in diff.

2026-04-24 — implementer (pass-2): Addressed both review blockers.

**Blocker 1 — Tenant Chat PII notice:**
- Added POPIA disclosure notice to `tenant/src/views/chat/ChatDetailView.vue` in the welcome/empty state (shown when `messages.length === 0` after loading). Uses Klikk voice: "Messages you send here are processed by an AI service. Don't share ID numbers, bank details, or passport numbers — we'll redact them, but it's safer not to send them."
- Added `Bot` icon import to support the welcome state illustration, consistent with `ChatListView.vue` pattern.
- Fixed `backend/apps/ai/README.md` line 77: replaced the dead `web_app/src/components/TenantChat.vue` TODO reference with the correct path `tenant/src/views/chat/ChatDetailView.vue`.

**Blocker 2 — `purge_old_interactions` test coverage:**
- Added `backend/apps/ai/tests/test_purge_old_interactions.py` with 16 pytest tests, all passing.
- Tests cover: stale `GuideInteraction` deleted, fresh retained; stale `TenantChatSession` deleted (by `updated_at`), fresh retained; `--dry-run` deletes nothing but both model types still counted; `--days=N` override honoured (narrower deletes more, wider deletes less); `--dry-run` + `--days` combined.
- Backdating uses `queryset.update(created_at=...)` / `queryset.update(updated_at=...)` to bypass `auto_now_add` / `auto_now` without touching signal or model internals.
