---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-026
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
Three ad-hoc XFF extractors remain in the codebase after RNT-SEC-026 migrated the three targeted sites. All three still blindly trust the first XFF hop without honouring `NUM_PROXIES` or `TRUSTED_PROXY_IPS`.

## Why it matters
Any request that reaches these paths can carry a spoofed `X-Forwarded-For` header that will be recorded verbatim in `LoginAttempt`, `UserConsent` (registration path), and e-signing audit data — defeating the hardening delivered by RNT-SEC-026.

## Where I saw it
- `backend/apps/accounts/views.py:55-59` — `LoginView._get_client_ip()` private method, used for lockout decisions and `LoginAttempt` recording
- `backend/apps/accounts/serializers.py:106-107` — inline XFF in `RegistrationSerializer._record_consent()`, stores consent IP directly
- `backend/apps/esigning/views.py:628-629` — inline XFF in the e-signing submit view, stored in `audit_data["ip_address"]`

## Suggested acceptance criteria
- [ ] `accounts/views.py` `LoginView._get_client_ip` replaced with `get_client_ip(request)` from `utils.http`
- [ ] `accounts/serializers.py` `RegistrationSerializer._record_consent` inline extractor replaced with `get_client_ip(request)`
- [ ] `esigning/views.py` inline XFF block (line ~628) replaced with `get_client_ip(request)`
- [ ] No remaining raw `HTTP_X_FORWARDED_FOR` reads outside `utils/http.py` in the `apps/` tree (grep check)

## Why I didn't fix it in the current task
These sites were not listed in the task's "Files likely touched" scope. Expanding would double the diff and conflate two distinct pieces of work.
