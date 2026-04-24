---
id: RNT-QUAL-060
stream: rentals
title: "Build push notification preferences UI screen in agent-app and tenant app"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Implement the notification preferences settings screen in both agent-app and tenant app, backed by the existing `GET/POST /auth/push-preferences/` API, so users can toggle push notification categories and satisfy POPIA data-use consent disclosure.

## Acceptance criteria
- [x] Agent-app: "Notifications" section in settings screen with category toggles (lease, mandate, rent, maintenance, chat), persisted via `POST /auth/push-preferences/`
- [x] Tenant app: equivalent toggles in Settings / My Account screen
- [x] Both apps load current preferences from `GET /auth/push-preferences/` on screen mount
- [x] Toggle changes are saved immediately (or on explicit save button) with success/error feedback
- [x] Screen is reachable from the main settings navigation

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

2026-04-25 — Implemented. Task says `views/settings/` path but agent-app uses `pages/` convention; created `agent-app/src/pages/NotificationPreferencesPage.vue` to match. Tenant app correctly uses `tenant/src/views/settings/NotificationPreferencesView.vue`. Both screens load prefs on mount via GET `/auth/push-preferences/`, save immediately on toggle via POST, and show success/error feedback. Agent-app: added "Notifications" nav row to SettingsPage + route at `/settings/notifications`. Tenant app: added "Notifications" row to SettingsView (above My Data) + depth-2 route at `/settings/notifications`. Both: POPIA s18 purpose-notification disclosure included. vue-tsc clean on tenant; agent-app only shows a pre-existing TS6.0 deprecation warning unrelated to this change.
2026-04-24 — Review passed. Verified: (1) new NotificationPreferencesPage.vue (agent-app) + NotificationPreferencesView.vue (tenant) both call GET/POST /auth/push-preferences/ matching backend PushPreferenceView at backend/apps/accounts/urls.py:29; (2) router wiring correct in both apps (agent-app nested under main layout with showBackBtn, tenant depth-2 requiresAuth); (3) settings nav entries added in SettingsPage.vue and SettingsView.vue; (4) no backend changes; (5) optimistic toggle with revert on failure, loading/saving states, POPIA s18 disclosure present; (6) no PII logging, auth-only endpoint (IsAuthenticated on PushPreferenceView).
