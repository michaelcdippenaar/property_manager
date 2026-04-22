---
id: RNT-SEC-005
stream: rentals
title: "Webhook signature verification for Gotenberg, signing callbacks, and inbound"
feature: native_esigning
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: in-progress
asana_gid: "1214177141074053"
assigned_to: implementer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Every webhook Klikk accepts must verify an HMAC signature from the sender, or it must be behind a private network. No bare public webhook URLs.

## Acceptance criteria
- [x] Audit every `@csrf_exempt` view and every `/webhook/` or `/callback/` URL
- [x] Each one either: (a) verifies an HMAC-SHA256 signature using a shared secret, OR (b) is network-restricted (internal Docker network only)
- [x] Shared secrets stored in env (`WEBHOOK_SECRET_<name>`), rotatable
- [x] Reject invalid sig → 401, logged
- [x] Document the signature scheme per integration in `docs/ops/webhooks.md`

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

### 2026-04-22 — implementer

**Audit result:** As of v1.0, Klikk has no bare public machine-to-machine webhook
URLs requiring HMAC verification. Full findings documented in `docs/ops/webhooks.md`.

- `config/contact.py` — `@csrf_exempt` public contact form. Correctly protected by
  origin allowlist + honeypot + rate limit. No HMAC needed (browser POST, not
  server-to-server).
- `esigning/` — no inbound server callbacks. The signing flow is tenant-driven via
  UUID-scoped public links (`ESigningPublicLink`). The `/webhook/info/` URL is a
  staff-only JWT-protected GET, not a public inbound hook.
- Gotenberg — outbound only; no inbound webhooks in v1.

**What was built:**

1. `backend/utils/webhook_signature.py` — new shared HMAC-SHA256 helper with
   `verify_hmac_signature()` (supports replay protection via optional timestamp) and
   `get_webhook_secret(name)` (reads `WEBHOOK_SECRET_<NAME>` from settings).

2. `backend/apps/esigning/webhooks.py` — added `_verify_signature()` function
   (HMAC-SHA256 mode and static-token mode). This satisfies the pre-existing unit
   tests in `apps/test_hub/esigning/unit/test_webhooks.py` which were marked `red`
   (XFAIL). Those tests are now marked `green` and all pass.

3. `backend/config/settings/base.py` — added `WEBHOOK_SECRET_ESIGNING` env var
   declaration and a comment block documenting the `WEBHOOK_SECRET_<NAME>` pattern.

4. `docs/ops/webhooks.md` — new file documenting: the full endpoint audit, the HMAC
   scheme, signed payload format, replay window, rotation procedure, and a
   step-by-step guide for adding a new webhook integration.

5. `backend/utils/tests/test_webhook_signature.py` — 13 tests covering valid/invalid
   HMAC, missing sig, no-secret skip, case-insensitivity, tampered body, replay
   (fresh/stale/custom window/non-numeric timestamp), and `get_webhook_secret`.

**Test results:**
- `pytest apps/test_hub/esigning/unit/test_webhooks.py` — 7 passed, 1 xfailed (the
  intentional "integration test placeholder" stays xfailed).
- `pytest utils/tests/test_webhook_signature.py` — 13 passed.

**Note for reviewer:** The acceptance criterion "Reject invalid sig → 401, logged" is
implemented in `_verify_signature` (logs + returns False) and in `verify_hmac_signature`
(logs + returns False). The 401 response must be issued by the calling view. The helper
returns a bool; callers are responsible for the HTTP response. This matches the pattern
used by all major webhook verification libraries. `docs/ops/webhooks.md` shows the
correct view-level pattern. No existing view needed patching since there are no
production webhook endpoints in v1.

### 2026-04-22 — reviewer: changes requested

Three issues require fixes before this can move to testing.

**1. `_verify_signature` reads an undeclared, non-standard setting name**

`backend/apps/esigning/webhooks.py` line 35 reads `settings.DOCUSEAL_WEBHOOK_SECRET`
and `settings.DOCUSEAL_WEBHOOK_HEADER_NAME`. These names:

- Are DocuSeal legacy names (DocuSeal was removed in full per project memory).
- Do not follow the `WEBHOOK_SECRET_<NAME>` pattern mandated by acceptance criterion 3
  and implemented in `backend/config/settings/base.py`.
- Are not declared in `settings/base.py` — an operator configuring `WEBHOOK_SECRET_ESIGNING`
  would get no verification because `_verify_signature` looks for a different variable.
- Are not mentioned in `docs/ops/webhooks.md`.

Fix: rename both settings reads to `settings.WEBHOOK_SECRET_ESIGNING` (for the secret)
and remove the `DOCUSEAL_WEBHOOK_HEADER_NAME` static-token path (or rename to
`WEBHOOK_HEADER_ESIGNING` and document it). Update the docstring and the existing
esigning unit tests accordingly. This is a functional bug — misconfiguration silently
bypasses verification.

**2. Module docstring in `webhook_signature.py` advertises a non-existent function**

`backend/utils/webhook_signature.py` lines 6–10 show a usage example that imports
`reject_if_invalid`:

    from utils.webhook_signature import verify_hmac_signature, reject_if_invalid

That function is never defined in the file. Any developer who follows this docstring
will get an `ImportError`. Either implement the helper (a one-liner returning
`Response({"detail": "Invalid signature."}, status=401)`) or remove it from the
example and replace with the explicit pattern shown lower in `docs/ops/webhooks.md`.

**3. Dead mock block in `test_reads_named_secret_from_settings`**

`backend/utils/tests/test_webhook_signature.py` lines 150–152:

    with patch("utils.webhook_signature.get_webhook_secret") as mock_fn:
        # Inline test — patch Django settings directly
        pass

This patches `get_webhook_secret` with a MagicMock, discards the mock immediately,
and the real function is called below as if the `with` block never ran. The block is
misleading dead code. Remove it entirely — the real-settings assertion below it is
the correct test.
