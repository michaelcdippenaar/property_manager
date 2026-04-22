---
discovered_by: rentals-reviewer
discovered_during: RNT-011
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml` has `android:allowBackup="true"` — the Capacitor scaffold default. This allows ADB full-data backup of app storage (JWT tokens, cached user data) on unencrypted USB-debug connections.

## Why it matters
Any developer or tester with USB access to a device running a debug or production build can extract the app's data directory via `adb backup`. For a property-management app handling tenant PII and lease documents this is a POPIA data-protection concern. Google Play also warns against `allowBackup=true` for apps handling sensitive data.

## Where I saw it
- `agent-app/src-capacitor/android/app/src/main/AndroidManifest.xml:4` — `android:allowBackup="true"`

## Suggested acceptance criteria (rough)
- [ ] Set `android:allowBackup="false"` in `AndroidManifest.xml`
- [ ] Set `android:fullBackupOnly="false"` (or configure a `backup_rules.xml` that explicitly excludes sensitive paths) to suppress the resulting lint warning

## Why I didn't fix it in the current task
Scaffold default; out of scope for the Android platform-scaffolding task. Requires a deliberate policy decision on which data (if any) should participate in Android Auto Backup.
