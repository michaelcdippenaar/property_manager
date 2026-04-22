---
discovered_by: rentals-implementer
discovered_during: QA-004
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT
---

## What I found

The Klikk Agent iOS app has no `PrivacyInfo.xcprivacy` file. Apple has required this privacy manifest for all apps and third-party SDKs since spring 2024. Without it, App Store Connect will reject the build.

## Why it matters

TestFlight and App Store submission will be blocked. Capacitor core and its plugins (splash-screen, keyboard, status-bar) all use privacy-sensitive APIs (NSUserDefaults, file timestamps) that must be declared. Missing declaration = rejection during App Review.

## Where I saw it

- `agent-app/src-capacitor/ios/App/App/` — no `PrivacyInfo.xcprivacy` present
- Apple requirement: https://developer.apple.com/documentation/bundleresources/privacy_manifest_files

## Suggested acceptance criteria (rough)

- [ ] `PrivacyInfo.xcprivacy` created at `agent-app/src-capacitor/ios/App/App/PrivacyInfo.xcprivacy`
- [ ] Declares `NSPrivacyAccessedAPICategoryUserDefaults` (Capacitor uses NSUserDefaults for preferences)
- [ ] Declares `NSPrivacyAccessedAPICategoryFileTimestamp` (Capacitor file plugin accesses file timestamps)
- [ ] Privacy manifest added to Xcode project target membership
- [ ] Build passes App Store Connect upload validation (`xcrun altool` or Xcode Organizer shows no privacy manifest warnings)

## Why I didn't fix it in the current task

Out of scope — QA-004 is a smoke test script authoring task. Creating and wiring an Xcode privacy manifest requires Xcode project edits and is a separate implementation unit of work.
