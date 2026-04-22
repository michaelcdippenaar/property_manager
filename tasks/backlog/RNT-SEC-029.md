---
id: RNT-SEC-029
stream: rentals
title: "Add android:allowBackup=false to agent-app AndroidManifest"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [RNT-016]
asana_gid: "1214200629255776"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent ADB backup extraction of JWT tokens and tenant PII from the agent app by setting `android:allowBackup="false"` in the Android manifest.

## Acceptance criteria
- [ ] `android:allowBackup="false"` set in `agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml`
- [ ] `android:fullBackupOnly="false"` set (or a `backup_rules.xml` created) to suppress the resulting lint warning
- [ ] Android build still succeeds (`./gradlew assembleDebug` exits 0)
- [ ] `adb backup` on a connected device returns an empty backup (no app data exported)

## Files likely touched
- `agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml`

## Test plan
**Manual:**
- Connect USB-debug device, run `adb backup -apk com.tremly.klikk` — confirm no data extracted

## Handoff notes
Promoted from discovery `2026-04-22-android-allow-backup-enabled.md` (found during RNT-011). POPIA data-protection concern; depends on RNT-016 (Android platform scaffolding) completing first.
