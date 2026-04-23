---
id: RNT-SEC-044
stream: rentals
title: "POPIA s72 — AI Guide / Tenant Chat PII cross-border transfer compliance"
feature: ai_guide
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214241801064718"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Ensure all AI surfaces (AI Guide, Tenant Chat, Agent Assist) comply with POPIA s72 by adding a server-side PII scrubber, a user-facing notice, and a recorded legal basis before any message is forwarded to Anthropic's API.

## Acceptance criteria

- [ ] Operator register entry for Anthropic is recorded in the legal pack (DPA or equivalent) and referenced in the codebase (`backend/apps/ai/README.md` or similar)
- [ ] A user-facing notice "Messages you send here are processed by an AI service" is displayed on all chat widget surfaces (AI Guide, Tenant Chat, Agent Assist) before the first message is sent
- [ ] A server-side PII scrubber is applied in `guide_views.py` and the equivalent Tenant Chat / Agent Assist view **before** `messages.create` is called and **before** persistence to `GuideInteraction.message`
- [ ] Scrubber regex covers at minimum: SA ID number (13-digit), SA bank account numbers, and passport numbers
- [ ] `GuideInteraction.message` (and equivalent chat log fields) has a documented retention policy of ≤ 90 days; a management command or scheduled task enforces this
- [ ] Unit tests cover the scrubber (no false positives on normal text, correct redaction of SA ID and bank account patterns)

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
