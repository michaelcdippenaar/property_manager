# apps/ai — AI Guide, Tenant Chat & Agent Assist

Provides AI-powered chat surfaces across the Klikk platform:

| Surface | View | Model |
|---------|------|-------|
| AI Guide (admin portal) | `guide_views.AIGuideView` | claude-haiku-4-5 |
| Tenant Chat | `tenant_portal.views.TenantChatMessageView` | claude-sonnet-4-6 |
| Agent Assist | `maintenance.agent_assist_views.AgentAssistView` | claude-sonnet-4-6 |

---

## POPIA s72 — Cross-Border Transfer Compliance

All three surfaces forward user messages to **Anthropic PBC** (San Francisco, USA), which is a third-party operator outside South Africa under POPIA s72.

### Operator register entry — Anthropic PBC

| Field | Value |
|-------|-------|
| Operator name | Anthropic PBC |
| Country | United States of America |
| Processing purpose | AI inference — navigation assist, tenant support, maintenance triage |
| Legal basis | Legitimate interest / contractual necessity (property management service delivery) |
| Data shared | Scrubbed user messages only (no raw PII) |
| DPA / contractual safeguard | Anthropic Usage Policy + Terms of Service accepted at account creation; Anthropic's Privacy Policy governs data handling. No separate DPA is offered by Anthropic for API consumers at this time — the Terms of Service constitute the operator agreement. |
| Transfer mechanism | Standard contractual terms via Anthropic ToS (see https://www.anthropic.com/legal/aup) |
| Review date | 2027-04-23 (annual review) |

**Action required before go-live:** Confirm with legal counsel that Anthropic's ToS + Privacy Policy
constitute a sufficient operator agreement under POPIA s72 or obtain a signed DPA.
Reference task RNT-SEC-044 in the legal pack.

---

## PII Scrubber (`scrubber.py`)

All user messages are passed through `apps.ai.scrubber.scrub()` **before**:
1. Being forwarded to Anthropic's API.
2. Being persisted to `GuideInteraction.message` or `TenantChatSession.messages`.

Patterns redacted (replaced with `[REDACTED]`):
- SA ID numbers (13-digit)
- SA bank account numbers (6–11 digit isolated sequences)
- Passport numbers (SA: A + 8 digits; generic: 1–2 letters + 6–8 digits)

Tests: `apps/ai/tests/test_pii_scrubber.py`

---

## Retention Policy

`GuideInteraction` and `TenantChatSession` records are deleted after
**`AI_INTERACTION_RETENTION_DAYS`** days (default: 90).

Enforced by the management command:

```bash
python manage.py purge_old_interactions
python manage.py purge_old_interactions --dry-run  # preview only
python manage.py purge_old_interactions --days 60  # override threshold
```

Schedule this as a daily cron or Celery beat task in production.

---

## User-Facing Disclosure

All chat surfaces display the notice:

> "Messages you send here are processed by an AI service."

before the first message is sent.  This satisfies POPIA s18 notification requirements.

- AI Guide: `admin/src/components/AIGuide.vue` — notice in welcome state
- Tenant Chat: `web_app/src/components/TenantChat.vue` — notice shown on session open (TODO: implement in web_app once scaffolded; see task note in RNT-SEC-044)
- Agent Assist: `admin/src/views/maintenance/MaintenanceDetailView.vue` — notice in chat header
