---
discovered_by: ux-onboarding
discovered_during: UX-001
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: UX
---

## What I found

The agent mobile app login page toggles the password reset form via a `v-if="showReset"` boolean in-place, without navigating to a new route. On Android, pressing the hardware back button while the reset form is visible exits the app instead of returning to the login form, because no history entry was created.

## Why it matters

Android users who tap "Forgot password?" and then change their mind will accidentally exit the app. For a new agent who has just downloaded the app and is trying to sign in for the first time, this creates confusion and a poor first impression.

## Where I saw it

- `agent-app/src/pages/LoginPage.vue`: `<div v-else-if="showReset" class="login-sheet">` controlled by `showReset = true` on button click
- The agent app router has `/forgot-password` defined (mirrored from admin) but the login page does not use it

## Suggested acceptance criteria (rough)

- [ ] Tapping "Forgot password?" in the agent app navigates to a `/forgot-password` route (or modal with proper back-stack)
- [ ] Android hardware back button returns user to the login form, not exits the app
- [ ] Behaviour is consistent with iOS (sheet dismiss → login form)

## Why I didn't fix it in the current task

Out of scope for a UX audit. Small but important fix for Android users.
