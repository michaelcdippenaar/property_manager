---
discovered_by: rentals-reviewer
discovered_during: OPS-004
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
Three separate apps (`apps/legal/serializers.py`, `apps/esigning/audit.py`, `apps/accounts/audit.py`) each implement their own `X-Forwarded-For` IP extraction that blindly trusts the first hop, making the recorded IP spoofable by any client that sends a crafted `X-Forwarded-For` header.

## Why it matters
Consent audit trails (POPIA s11), e-signing audit logs, and login audit logs may record attacker-supplied IPs rather than real client IPs. This weakens forensic value and may allow rate-limit bypass if rate-limiting is IP-based.

## Where I saw it
- `backend/apps/legal/serializers.py:62` — `_get_ip` static method
- `backend/apps/esigning/audit.py:10`
- `backend/apps/accounts/audit.py:10`

## Suggested acceptance criteria (rough)
- [ ] Introduce a shared `get_client_ip(request)` utility in `backend/utils/http.py` that respects `SECURE_PROXY_SSL_HEADER` and `NUM_PROXIES` (or a trusted-proxies list from settings).
- [ ] Replace all three ad-hoc XFF extractions with the shared utility.
- [ ] Unit test: spoofed XFF header does not override the socket REMOTE_ADDR when proxy count is 0.

## Why I didn't fix it in the current task
Out of scope for OPS-004; pre-existing pattern across multiple apps; requires a cross-cutting decision on proxy trust configuration.
