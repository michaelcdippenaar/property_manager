---
id: RNT-SEC-005
stream: rentals
title: "Webhook signature verification for Gotenberg, signing callbacks, and inbound"
feature: native_esigning
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177141074053"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Every webhook Klikk accepts must verify an HMAC signature from the sender, or it must be behind a private network. No bare public webhook URLs.

## Acceptance criteria
- [ ] Audit every `@csrf_exempt` view and every `/webhook/` or `/callback/` URL
- [ ] Each one either: (a) verifies an HMAC-SHA256 signature using a shared secret, OR (b) is network-restricted (internal Docker network only)
- [ ] Shared secrets stored in env (`WEBHOOK_SECRET_<name>`), rotatable
- [ ] Reject invalid sig → 401, logged
- [ ] Document the signature scheme per integration in `docs/ops/webhooks.md`

## Files likely touched
- `backend/apps/esigning/webhooks.py` (or equivalent)
- `backend/apps/*/webhooks.py`
- `backend/utils/webhook_signature.py` (new helper)
- `docs/ops/webhooks.md` (new)

## Test plan
**Automated:**
- `pytest backend/utils/tests/test_webhook_signature.py`
- Rejects: missing sig, wrong sig, replay (timestamp >5min old)
- Accepts: valid sig within window

## Handoff notes
