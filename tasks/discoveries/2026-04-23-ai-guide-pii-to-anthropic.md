---
discovered_by: rentals-reviewer
discovered_during: RNT-022
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
The AI Guide endpoint (and by extension Tenant Chat) forwards raw user message text to Anthropic's API with no PII redaction, no input classification, and no system-level user warning. Users may paste SA ID numbers, banking details, or other special-personal-info into a "navigation assistant" textbox and have it exit to a cross-border third-party processor.

## Why it matters
POPIA s72 requires a lawful basis for cross-border transfer of personal information. If Anthropic is in the operator register with a signed DPA this is fine, but there is no user-facing notice and no server-side scrubber. For RNT-022 this is a platform-level gap, not a per-task bug — Tenant Chat has the same shape.

## Where I saw it
- `backend/apps/ai/guide_views.py:91` — `messages=[{"role": "user", "content": message}]` sent verbatim
- `backend/apps/ai/guide_views.py:200-207` — also persisted verbatim to `GuideInteraction.message`
- Same pattern likely in `TenantChatSession` flow

## Suggested acceptance criteria (rough)
- [ ] Operator register entry for Anthropic recorded in legal pack
- [ ] User-facing notice "messages you send here are processed by an AI service" on chat widgets
- [ ] Server-side PII scrubber (regex for SA ID, bank account numbers) applied before `messages.create` and before persistence
- [ ] Retention policy for GuideInteraction.message (e.g. 90 days)

## Why I didn't fix it in the current task
Cross-cutting concern covering all AI surfaces — Tenant Chat and Agent Assist have the same pattern. Needs a platform-level decision (redaction layer vs. operator-register + notice) rather than an ad-hoc fix in one endpoint.
