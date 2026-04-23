---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-029
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
The Flutter tenant app manifest at `mobile/android/app/src/main/AndroidManifest.xml` does not set `android:allowBackup="false"`. The `<application>` element has no `allowBackup` attribute, meaning Android defaults to `true` and ADB backup can extract tenant JWT tokens and PII.

## Why it matters
Same POPIA data-protection risk that motivated RNT-SEC-029: an attacker with USB access or a compromised backup service could extract the tenant's session token and personal data from the device backup.

## Where I saw it
- `mobile/android/app/src/main/AndroidManifest.xml` — `<application>` block, lines 8–12: no `allowBackup` attribute present.

## Suggested acceptance criteria (rough)
- [ ] `android:allowBackup="false"` added to `<application>` in `mobile/android/app/src/main/AndroidManifest.xml`
- [ ] `android:fullBackupOnly="false"` added (or a `backup_rules.xml` created) to suppress lint warning
- [ ] Flutter build still succeeds (`flutter build apk --debug` exits 0)
- [ ] `adb backup` on a connected device returns an empty backup for the tenant app

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-029 is scoped to the agent-app Capacitor manifest only. Fixing the Flutter tenant app is a separate change with a separate test surface.
