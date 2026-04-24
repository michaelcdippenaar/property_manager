---
id: RNT-QUAL-063
stream: rentals
title: "Replace placeholder app icons and splash screens with Klikk-branded assets"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Replace all placeholder launcher icons (default Android robot vector, unverified iOS AppIcon PNG) and splash screens with official Klikk-branded assets so the agent app passes App Store Connect and Play Console review.

## Acceptance criteria
- [ ] Designer delivers a 1024x1024 Klikk "K" logomark on a transparent background (for icon foreground)
- [ ] iOS: `AppIcon-512@2x.png` and all `AppIcon.appiconset` sizes replaced with the official Klikk Agent icon; Xcode shows no "unassigned image" warnings
- [ ] Android: `drawable-v24/ic_launcher_foreground.xml` and all `mipmap-*/ic_launcher_foreground.png` densities replaced with Klikk-branded assets; background remains Navy `#2B2D6E` (already set in RNT-007)
- [ ] iOS `Splash.imageset/` and Android `drawable-port-*/splash.png` reviewed and replaced with branded full-bleed splash if currently placeholder
- [ ] Build passes App Store Connect and Play Console asset validation checks

## Files likely touched
- `agent-app/src-capacitor/ios/App/App/Assets.xcassets/AppIcon.appiconset/`
- `agent-app/src-capacitor/android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml`
- `agent-app/src-capacitor/android/app/src/main/res/mipmap-*/`
- `agent-app/src-capacitor/ios/App/App/Assets.xcassets/Splash.imageset/`
- `agent-app/src-capacitor/android/app/src/main/res/drawable-port-*/splash.png`

## Test plan
**Manual:**
- Build and install on iOS simulator: confirm correct icon and splash
- Build and install on Android emulator: confirm correct icon and splash
- Submit test build to App Store Connect / Play Console internal track; verify no asset rejection

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-agent-app-icon-artwork-missing.md`. Requires branded asset files from design team; cannot be generated from code. Background colour (Navy) already set by RNT-007.
