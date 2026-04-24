---
id: RNT-QUAL-060
stream: rentals
title: "Build push notification preferences UI screen in agent-app and tenant app"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Implement the notification preferences settings screen in both agent-app and tenant app, backed by the existing `GET/POST /auth/push-preferences/` API, so users can toggle push notification categories and satisfy POPIA data-use consent disclosure.

## Acceptance criteria
- [ ] Agent-app: "Notifications" section in settings screen with category toggles (lease, mandate, rent, maintenance, chat), persisted via `POST /auth/push-preferences/`
- [ ] Tenant app: equivalent toggles in Settings / My Account screen
- [ ] Both apps load current preferences from `GET /auth/push-preferences/` on screen mount
- [ ] Toggle changes are saved immediately (or on explicit save button) with success/error feedback
- [ ] Screen is reachable from the main settings navigation

## Files likely touched
- `agent-app/src/views/settings/NotificationPreferencesView.vue` (new)
- `agent-app/src/router/index.ts` (add route)
- `tenant/src/views/settings/NotificationPreferencesView.vue` (new)
- `tenant/src/router/index.ts` (add route)
- `backend/apps/accounts/views.py` — `PushPreferenceView` (no changes expected)

## Test plan
**Manual:**
- Open settings in agent-app; navigate to Notifications; toggle a category off; re-open — confirm persisted
- Repeat in tenant app

**Automated:**
- `cd backend && pytest apps/accounts/tests/ -v -k push_pref`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-push-preferences-ui-screen.md`. Backend `PushPreferenceView` and `PushPreference` model are fully implemented. Only UI screens are missing.
