---
id: RNT-SEC-003
stream: rentals
title: "Enforce 2FA for agents, agency admins, and staff users"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177452385365"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Require TOTP-based 2FA for every user role that can modify property, lease, or financial data. Tenants optional but offered.

## Acceptance criteria
- [ ] 2FA enforced (cannot skip) for: `staff`, `agency_admin`, `agent`, `managing_agent`, `estate_agent`, `owner`
- [ ] 2FA optional for: `tenant`, `supplier`
- [ ] TOTP (RFC 6238) via `django-otp` or `django-two-factor-auth`
- [ ] Enrollment on first login post-release; 7-day grace period, then hard-blocked
- [ ] Recovery codes issued on enrollment (10 codes, printable)
- [ ] Admin SPA login flow supports 2FA challenge
- [ ] Mobile agent app (Quasar) supports 2FA challenge
- [ ] Tenant web app (`web_app/`) supports 2FA challenge for tenants who opt in
- [ ] 2FA reset requires email verification + existing recovery code
- [ ] Flutter tenant mobile app deferred to v2 — no 2FA wiring needed there for v1.0

## Files likely touched
- `backend/apps/users/models.py` (UserProfile.twofa_required, twofa_enrolled_at)
- `backend/apps/users/views.py` (enrollment, challenge, reset)
- `backend/apps/users/serializers.py`
- `admin/src/views/auth/*.vue` (challenge screen, enrollment)
- `agent-app/src/features/auth/*` (Quasar agent app challenge)
- `web_app/src/views/auth/*` (tenant web opt-in)

## Test plan
**Automated:**
- `pytest backend/apps/users/tests/test_2fa.py`

**Manual:**
- Agent logs in → prompted to enroll → scans QR → enters TOTP → logs in
- After enrolment, login requires TOTP every time
- Recovery code lets user in when phone lost

## Handoff notes
