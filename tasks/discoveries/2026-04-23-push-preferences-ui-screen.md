---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-007
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
RNT-QUAL-007 acceptance criteria includes an in-app screen to toggle push notification categories per device (lease, mandate, rent, maintenance, chat). The backend `GET/POST /auth/push-preferences/` API is now built. The UI screen is not yet implemented in agent-app or tenant app.

## Why it matters
Without the UI screen, users cannot manage their notification preferences. This is also a POPIA disclosure requirement — users must have easy access to change data-use consent.

## Where I saw it
- `backend/apps/accounts/views.py` — `PushPreferenceView` (GET/POST, now implemented)
- `backend/apps/notifications/models.py` — `PushPreference` model (now implemented)
- Agent-app: no settings/preferences screen exists for push categories
- Tenant app: no notification preferences screen

## Suggested acceptance criteria (rough)
- [ ] Agent-app: "Notifications" section in settings screen with category toggles (lease, mandate, rent, maintenance, chat), persisted via POST /auth/push-preferences/
- [ ] Tenant app: equivalent toggles in Settings/My Account screen
- [ ] Both apps load current preferences from GET /auth/push-preferences/ on mount

## Why I didn't fix it in the current task
Building two full UI settings screens is a separate UI task. The API surface is ready so this can be implemented independently.
