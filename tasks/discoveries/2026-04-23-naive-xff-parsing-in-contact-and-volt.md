---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-039
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
Two production call sites still parse `X-Forwarded-For` naively and are spoofable in exactly the same way the RNT-SEC-039 audit middleware was. They do not use the repo's hardened `utils.http.get_client_ip` helper.

1. `backend/config/contact.py:46-51` — `_client_ip()` returns `xff.split(",")[0].strip()` (attacker-controlled leftmost entry).
2. `backend/apps/the_volt/gateway/views.py:142` — stores the entire `HTTP_X_FORWARDED_FOR` string verbatim into `DataRequest` audit `ip_address`.

## Why it matters
- `contact.py` is the public marketing contact endpoint with a 5/hour rate limit keyed on client IP (`RATE_LIMIT_PER_HOUR = 5`). Forging `X-Forwarded-For` trivially bypasses the rate limit by rotating the spoofed IP per request.
- `the_volt/gateway` writes the spoofable value into the Vault33 audit trail (POPIA data-subject request provenance). Same integrity regression pattern as the audit-middleware ticket just fixed — wrong IP on dispute records.
- Note: the_volt is out of Rentals v1 scope per PM memory, but the marketing contact endpoint is in-scope and the rate-limit bypass is exploitable today.

## Where I saw it
- `backend/config/contact.py:46-51`
- `backend/apps/the_volt/gateway/views.py:142`
- Hardened helper already exists: `backend/utils/http.py::get_client_ip` (NUM_PROXIES + TRUSTED_PROXY_IPS gated, unit-tested)

## Suggested acceptance criteria (rough)
- [ ] `config/contact.py::_client_ip` replaced with `utils.http.get_client_ip(request)`; delete the private helper.
- [ ] `apps/the_volt/gateway/views.py:142` replaced with `get_client_ip(request)`.
- [ ] Regression test: forged XFF with `NUM_PROXIES=0` does not bypass `contact_view` rate limiting.
- [ ] `grep -rn "HTTP_X_FORWARDED_FOR" backend/` returns zero production hits outside `utils/http.py`.

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-039 is scoped to audit middleware. Fixing contact.py and volt gateway in the same commit would double the diff and cross stream boundaries (marketing contact + Vault33).
