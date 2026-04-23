---
discovered_by: ux-onboarding
discovered_during: UX-002
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: UX
---

## What I found
The AI chat empty state (`ChatListView.vue`) shows "No conversations yet / Start a new chat with your AI assistant" but gives no indication of what the assistant can actually help with. A first-time tenant does not know whether to use the chat for maintenance, lease questions, or general queries. The FAB is the only call to action and its function is not described.

## Why it matters
If tenants do not understand what the AI chat does, they will not use it, and the maintenance triage feature (which relies on chat to draft tickets) goes untouched. Lower engagement with the chat means more agent phone calls and slower triage.

## Where I saw it
- `tenant/src/views/chat/ChatListView.vue:11` — generic empty state; no suggested prompts, no capability description

## Suggested acceptance criteria (rough)
- [ ] Empty state includes 2–3 suggested starter prompts (e.g. "Report a repair", "When is my rent due?", "What does my lease say about pets?")
- [ ] Subtitle copy updated to describe the assistant's scope: lease, maintenance, and property questions
- [ ] FAB label or tooltip says "New conversation" (currently unlabelled icon only)

## Why I didn't fix it in the current task
Copy and UI changes outside the audit scope; requires design sign-off on suggested prompts.
