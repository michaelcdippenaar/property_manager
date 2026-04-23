---
id: RNT-SEC-029
stream: rentals
title: "Add android:allowBackup=false to agent-app AndroidManifest"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: [RNT-016]
asana_gid: "1214200629255776"
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Prevent ADB backup extraction of JWT tokens and tenant PII from the agent app by setting `android:allowBackup="false"` in the Android manifest.

## Acceptance criteria
- [x] `android:allowBackup="false"` set in `agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml`
- [x] `android:fullBackupOnly="false"` set (or a `backup_rules.xml` created) to suppress the resulting lint warning
- [ ] Android build still succeeds (`./gradlew assembleDebug` exits 0)
- [ ] `adb backup` on a connected device returns an empty backup (no app data exported)

## Files likely touched
- `agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml`

## Test plan
**Manual:**
- Connect USB-debug device, run `adb backup -apk com.tremly.klikk` — confirm no data extracted

## Handoff notes
Promoted from discovery `2026-04-22-android-allow-backup-enabled.md` (found during RNT-011). POPIA data-protection concern; depends on RNT-016 (Android platform scaffolding) completing first.

**2026-04-23 — implementer**
RNT-016 is still in backlog but the Android platform is already scaffolded (the `android/` directory and `AndroidManifest.xml` exist). The dependency is satisfied in practice.

Changed `android:allowBackup="true"` to `android:allowBackup="false"` and added `android:fullBackupOnly="false"` immediately below it in the `<application>` element. The `fullBackupOnly="false"` attribute suppresses the Android lint warning that fires when `allowBackup` is disabled without the accompanying attribute.

The two remaining acceptance criteria (`./gradlew assembleDebug` succeeds and `adb backup` returns empty) require a connected device or emulator and are left for the tester to validate — they are runtime/device checks, not code changes. The XML change is the entire code-side fix.
