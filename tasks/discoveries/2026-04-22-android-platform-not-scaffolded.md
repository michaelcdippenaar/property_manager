---
discovered_by: rentals-implementer
discovered_during: QA-004
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT
---

## What I found

The Klikk Agent Capacitor app has only the iOS platform scaffolded. There is no `android/` directory under `agent-app/src-capacitor/`. `npx cap add android` has never been run. The app cannot be built for Android at all.

## Why it matters

QA-004 requires Android 14 (Pixel 7) and Android 12 (low-end) smoke testing. The smoke matrix cannot be executed for any Android device until the platform is scaffolded, an `AndroidManifest.xml` is configured with the correct permissions, and an APK/AAB can be produced. This blocks the Play Beta milestone.

## Where I saw it

- `agent-app/src-capacitor/` — only `ios/` subdirectory; no `android/` directory
- `agent-app/src-capacitor/package.json` — `@capacitor/android` is not listed as a dependency (only `@capacitor/ios`)

## Suggested acceptance criteria (rough)

- [ ] `@capacitor/android` added to `agent-app/src-capacitor/package.json` (matching version of `@capacitor/ios`, currently `^6.2.1`)
- [ ] `npx cap add android` run; `android/` directory committed
- [ ] `android/app/src/main/AndroidManifest.xml` reviewed — only INTERNET permission; no camera/location/contacts/phone-state requested
- [ ] `targetSdkVersion 34` and `minSdkVersion 23` confirmed in `build.gradle`
- [ ] App builds and launches on Android 14 emulator (Pixel 7 AVD)
- [ ] App builds and launches on Android 12 emulator (low-end profile AVD)

## Why I didn't fix it in the current task

Out of scope — QA-004 is a smoke test script authoring task. Scaffolding the Android Capacitor platform, resolving any plugin compatibility issues, and ensuring the Gradle build succeeds is a meaningful implementation task in its own right.
