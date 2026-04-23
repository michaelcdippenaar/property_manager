---
discovered_by: ux-onboarding
discovered_during: UX-001
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: UX
---

## What I found

When a tenant or owner completes signing a document (mandate or lease), the agent receives no in-app notification, push notification, or email alert. The WebSocket panel in `MandateSigningPanel.vue` and `ESigningPanel.vue` updates in real time only if the agent has that panel open. If they navigate away, the signing completion event is silently missed.

## Why it matters

Signing events happen asynchronously — often hours or days after the agent sends the request. With no passive notification, agents must actively poll the signing panel to learn that a document was signed. This is especially critical for the first rental cycle: an agent waiting for a mandate or lease to be signed has no signal to move to the next step. Delays in the cycle result directly from this gap.

## Where I saw it

- `admin/src/views/properties/MandateSigningPanel.vue`: WebSocket handler fires `emit('signed')` and calls `load()` — no toast or notification to other views
- `admin/src/views/leases/ESigningPanel.vue`: same pattern
- No push notification infrastructure observed in the codebase

## Suggested acceptance criteria (rough)

- [ ] When a signing event completes (signer_completed or submission_completed), a toast notification appears in the admin app regardless of which page the agent is on
- [ ] The notification includes the signer's name and the document type (mandate / lease)
- [ ] Optionally: an email notification is sent to the agent's registered email address

## Why I didn't fix it in the current task

Requires a global notification bus or backend webhook/email infrastructure. Out of scope for UX audit. Likely needs OPS involvement for email delivery (SES).
