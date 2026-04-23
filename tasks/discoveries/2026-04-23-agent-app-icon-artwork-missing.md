---
discovered_by: rentals-implementer
discovered_during: RNT-007
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-QUAL
---

## What I found

The agent app's launcher icons (iOS `AppIcon.appiconset/` and Android `mipmap-*/`) contain
placeholder artwork — a single 1024x1024 PNG on iOS (likely a Quasar default) and the default
Android "robot" vector on Android. The adaptive icon foreground
(`drawable-v24/ic_launcher_foreground.xml`) is the generic Android system icon, not the Klikk
logomark.

## Why it matters

Both App Store Connect and Play Console require final artwork before a build can pass review.
Placeholder icons will cause a rejection or at minimum look unprofessional to beta testers.
The iOS `AppIcon-512@2x.png` file has not been verified to be Klikk-branded.

## Where I saw it

- `agent-app/src-capacitor/ios/App/App/Assets.xcassets/AppIcon.appiconset/` — single PNG, no
  confirmation it is the correct branded asset
- `agent-app/src-capacitor/android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml` —
  default Android robot vector
- `agent-app/src-capacitor/android/app/src/main/res/mipmap-*/ic_launcher_foreground.png` —
  default Android bitmaps (not Klikk branded)

## Suggested acceptance criteria (rough)

- [ ] Designer delivers a 1024x1024 Klikk "K" logomark on transparent background
- [ ] iOS: replace `AppIcon-512@2x.png` with the official Klikk Agent icon; verify Xcode
      reads it cleanly (no "unassigned image" warnings)
- [ ] Android: replace `ic_launcher_foreground.xml` + all `ic_launcher*.png` densities with
      Klikk-branded assets using the Navy (#2B2D6E) background already set in this task
- [ ] Splash screens: iOS `Splash.imageset/` and Android `drawable-port-*/splash.png` reviewed
      and replaced with branded full-bleed splash if the current assets are placeholders

## Why I didn't fix it in the current task

Requires branded asset files from the design team; cannot be generated from code alone.
The background colour is already set to Klikk Navy (#2B2D6E) as part of RNT-007.
