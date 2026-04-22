# Klikk Agent App — Mobile Smoke Matrix
**Date:** 2026-04-22
**Task:** QA-004
**App version:** 1.0.0 (Bundle ID: `za.co.klikk.agentapp`)
**Tester:** _to be filled on execution_
**Status:** SCRIPT READY — awaiting device execution

---

## Overview

This document provides the scripted smoke matrix for the Klikk Agent Quasar/Capacitor app before TestFlight and Google Play Beta distribution. It covers four device targets × three flows. Each cell must be marked PASS, FAIL, or SKIP (with a reason).

### Device matrix

| ID | Platform | Device | OS | Screen class | Notes |
|----|----------|--------|----|-------------|-------|
| D1 | iOS | iPhone 15 | iOS 17 | 6.1" standard | Primary test device |
| D2 | iOS | iPhone SE (3rd gen) | iOS 17 | 4.7" compact | Small-screen regression |
| D3 | Android | Pixel 7 | Android 14 | 6.3" standard | Primary Android device |
| D4 | Android | Low-end budget device (e.g. Samsung A14 or equivalent) | Android 12 | 6.6" FHD+ | Low-end regression |

### Flow matrix

| ID | Flow |
|----|------|
| F1 | Login (email + password + 2FA TOTP) |
| F2 | Create mandate (direct lease via property) |
| F3 | Book viewing |

Simulator use is acceptable for D1 + D3 during the initial pass. At least one real device per OS must complete a final pass before TestFlight/Play Beta submission.

---

## Prerequisites

Before running, confirm:
- [ ] Test agent account exists: `agent.smoke@klikk.co.za` (AGENT role, 2FA enrolled, TOTP seed known)
- [ ] At least one property with one vacant unit exists in the test environment
- [ ] API base URL set correctly in build (`VITE_API_URL` / env config): `https://api.klikk.co.za/api/v1/` or staging equivalent
- [ ] Devices/simulators are on the same network as the backend (or staging URL is reachable)
- [ ] App build is a release/production build, not dev server WebView

---

## Flow F1 — Login

### Steps

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | Cold-launch the app | Splash screen appears, then Login screen with Klikk logo, navy hero, "Welcome back" heading |
| 2 | Tap the Email field | Keyboard raises (email type). Field is focussed |
| 3 | Enter `agent.smoke@klikk.co.za` | Text appears in field |
| 4 | Tap Password field | Keyboard switches to default. Field shows masked bullets |
| 5 | Toggle the eye icon | Password text is revealed / re-masked |
| 6 | Enter valid password | Text accepted |
| 7 | Tap Sign In | Loading spinner appears on button. API call made |
| 8 | 2FA challenge screen appears | "Verification required" heading. TOTP code input visible |
| 9 | Enter 6-digit TOTP code | Digits appear in input |
| 10 | Tap Verify | Spinner. On success, redirected to Today screen (bottom nav visible) |
| 11 | Verify Today screen loads | Today page content visible (no blank/error state) |

### Error sub-cases

| Sub-case | Action | Expected result |
|----------|--------|-----------------|
| E1 | Wrong password | "Invalid credentials" error message below form |
| E2 | Wrong TOTP code | "Invalid code" error on challenge screen |
| E3 | Tap "Forgot password?" | Reset password form shown in same sheet |

### Matrix

| Device | F1 main | E1 | E2 | E3 | Tester | Date |
|--------|---------|----|----|-----|--------|------|
| D1 iPhone 15 | | | | | | |
| D2 iPhone SE | | | | | | |
| D3 Pixel 7 | | | | | | |
| D4 Low-end Android | | | | | | |

---

## Flow F2 — Create Mandate (Direct Lease)

**Entry point:** Properties tab → select a property → tap the "+" FAB (or "New Lease" action) → Create Lease form

### Steps

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | From Today or bottom nav, tap Properties tab | Properties list loads |
| 2 | Tap on a property with a vacant unit | Property detail screen opens |
| 3 | Tap the FAB ("+" button, bottom-right) | Options sheet or direct navigation to Create Lease |
| 4 | Confirm Create Lease / New Mandate option | Create Direct Lease screen opens with property name pre-filled |
| 5 | Select a vacant unit from the dropdown | Unit populates; rent amount auto-fills if configured |
| 6 | Under Tenant section, search for an existing person by name | Dropdown shows matching persons |
| 7 | Select a tenant from the list | Tenant fields populate (name, ID/passport, email, phone) |
| 8 | Enter lease start date via date picker | Date picker opens, date selected, input updates |
| 9 | Enter lease duration (months) or end date | Field accepts input |
| 10 | Enter monthly rent (ZAR) | Numeric keyboard. Field accepts amount |
| 11 | Enter deposit amount | Field accepts amount |
| 12 | Tap Create Lease | Loading indicator. Success toast appears |
| 13 | Lease appears in Leases list | Navigate to Leases tab; new lease visible with status "pending" |

### Error sub-cases

| Sub-case | Action | Expected result |
|----------|--------|-----------------|
| E1 | Submit with no unit selected | Validation error on unit field |
| E2 | Submit with no tenant | Validation error on tenant field |
| E3 | Submit with missing start date | Validation error on date field |

### Matrix

| Device | F2 main | E1 | E2 | E3 | Tester | Date |
|--------|---------|----|----|-----|--------|------|
| D1 iPhone 15 | | | | | | |
| D2 iPhone SE | | | | | | |
| D3 Pixel 7 | | | | | | |
| D4 Low-end Android | | | | | | |

---

## Flow F3 — Book Viewing

**Entry point:** Viewings tab → FAB ("+" button) → Book Viewing form (multi-step stepper)

### Steps

| Step | Action | Expected result |
|------|--------|-----------------|
| 1 | From bottom nav tap Viewings | Viewings list (or pipeline) loads |
| 2 | Tap the FAB ("+" button) | Book Viewing screen opens at Step 1 "Viewing Details" |
| 3 | Tap Property dropdown | Property list loads with search |
| 4 | Select a property | Units dropdown activates; available units shown |
| 5 | Optionally select a unit | Unit selection persists |
| 6 | Tap date field | Date picker opens |
| 7 | Select a viewing date (future) | Date updates in form |
| 8 | Tap time field | Time picker opens |
| 9 | Select a viewing time | Time updates |
| 10 | Tap Continue / Next | Advances to Step 2 "Prospect Details" |
| 11 | Enter prospect first name | Text accepted |
| 12 | Enter prospect last name | Text accepted |
| 13 | Enter prospect email | Email keyboard shown; text accepted |
| 14 | Enter prospect phone (SA format: 0XX XXX XXXX) | Phone keyboard shown |
| 15 | Tap Continue / Next | Advances to Step 3 review or confirm |
| 16 | Tap Book Viewing (submit) | Loading spinner. Success toast |
| 17 | New viewing appears in Viewings list | Navigate to Viewings; new entry visible with correct property + time |

### Error sub-cases

| Sub-case | Action | Expected result |
|----------|--------|-----------------|
| E1 | No property selected, tap Next | Validation error on property field |
| E2 | Past date selected | Validation error or warning (date must be future) |
| E3 | Missing prospect name, tap submit | Validation error on name field |

### Matrix

| Device | F3 main | E1 | E2 | E3 | Tester | Date |
|--------|---------|----|----|-----|--------|------|
| D1 iPhone 15 | | | | | | |
| D2 iPhone SE | | | | | | |
| D3 Pixel 7 | | | | | | |
| D4 Low-end Android | | | | | | |

---

## Privacy manifest & permissions check

### iOS — Privacy manifest

Apple requires a `PrivacyInfo.xcprivacy` file declaring all privacy-sensitive APIs used by the app and its SDKs (required for App Store submission as of spring 2024).

| Check | Status | Notes |
|-------|--------|-------|
| `PrivacyInfo.xcprivacy` exists at `App/App/PrivacyInfo.xcprivacy` | **MISSING** | File not present — see discovery `2026-04-22-missing-ios-privacy-manifest.md` |
| NSUserDefaults usage declared | PENDING | Capacitor uses NSUserDefaults internally |
| File timestamp APIs declared | PENDING | Capacitor accesses file system |
| No unnecessary NSUsageDescription keys in Info.plist | PASS | Info.plist contains no permission usage strings (camera, location, contacts not requested) |

Action required: Create `PrivacyInfo.xcprivacy` before TestFlight submission. See discovery task.

### Android — Permission manifest

| Check | Status | Notes |
|-------|--------|-------|
| Android platform scaffolded (`android/` dir) | **MISSING** | `npx cap add android` not yet run — see discovery `2026-04-22-android-platform-not-scaffolded.md` |
| INTERNET permission only (no camera/location/contacts) | PENDING | Cannot verify until Android platform is added |
| No WRITE_EXTERNAL_STORAGE (not needed) | PENDING | |
| No READ_PHONE_STATE (not needed) | PENDING | |
| targetSdkVersion >= 34 (Android 14) | PENDING | |

Action required: Scaffold Android platform and verify manifest. See discovery task.

---

## App Store / Play Store screenshots

Screenshots are a pre-submission requirement. They must be produced from the final production build, not from a dev environment.

### iOS HIG requirements

| Size | Required for | Notes |
|------|-------------|-------|
| 1290 × 2796 px | iPhone 6.7" (iPhone 15 Pro Max) — required | |
| 1179 × 2556 px | iPhone 6.1" (iPhone 15) — optional but recommended | |
| 1284 × 2778 px | iPhone 6.5" (older max) | |
| 886 × 1920 px | iPhone SE / 4.7" — optional | |

Minimum 3 screenshots required; maximum 10.

Checklist:
- [ ] Dashboard / Today screen (authenticated state)
- [ ] Viewings list or calendar
- [ ] Book Viewing stepper (Step 1)
- [ ] Create Lease form
- [ ] Login screen (as onboarding preview)

### Play Store MD3 requirements

| Size | Required for |
|------|-------------|
| 1080 × 1920 px (or 1920 × 1080) | Phone screenshots — at least 2 required |

Checklist:
- [ ] Same 5 screens as iOS above, captured on Pixel 7 or emulator at 1080p
- [ ] Feature graphic: 1024 × 500 px (required for Play listing)

### Approval gate

Screenshots are reviewed against HIG/MD3 guidelines by the designer before store submission. Sign-off documented in this section by the reviewer.

| Platform | Reviewer | Decision | Date |
|----------|---------|---------|------|
| iOS App Store | | PENDING | |
| Google Play | | PENDING | |

---

## Issue log

Issues found during execution are logged here and promoted to RNT tasks by the PM.

| ID | Device | Flow | Step | Description | Severity | RNT task |
|----|--------|------|------|-------------|---------|---------|
| | | | | | | |

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Reviewer | | | |
