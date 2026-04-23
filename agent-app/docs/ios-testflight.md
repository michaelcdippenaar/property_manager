# iOS TestFlight Distribution — Manual Steps

This document covers the one-time App Store Connect setup and the repeatable
build + upload flow for distributing Klikk Agent to internal testers.

## Prerequisites

| Item | Detail |
|------|--------|
| Apple Developer account | mc@tremly.co.za (Team: Klikk Technologies) |
| Bundle ID | `za.co.klikk.agentapp` — register in Identifiers section |
| Xcode version | 15+ (required for iOS 15.0 deployment target) |
| CocoaPods | `brew install cocoapods` → `pod install` in `src-capacitor/ios/App/` |

## One-time App Store Connect setup

1. **Create the App ID** in Identifiers:
   - Bundle ID: `za.co.klikk.agentapp`
   - Enable capability: **Associated Domains** (for Universal Links)
   - Enable capability: **Push Notifications** (needed later)

2. **Create a Distribution certificate** (iOS Distribution) in Certificates.

3. **Create a Provisioning Profile** of type *App Store Distribution*:
   - Attach it to the `za.co.klikk.agentapp` App ID
   - Download and double-click to install in Xcode keychain

4. **Create the App record** in App Store Connect → My Apps → New App:
   - Platform: iOS
   - Bundle ID: `za.co.klikk.agentapp`
   - Primary language: English (South Africa)
   - SKU: `klikk-agent-001`

5. **Host the AASA file** on agent.klikk.co.za (see `universal-links.md`)

## Build & upload

```bash
# From agent-app/
npm install

# Build the Quasar SPA and copy to iOS
npm run build:ios

# Open Xcode (or run from Xcode directly)
open src-capacitor/ios/App/App.xcworkspace
```

In Xcode:
- Select scheme **App → Any iOS Device (arm64)**
- Product → Archive
- Distribute App → App Store Connect → Upload
- Enable "Automatically manage signing" (Automatic in project settings)

## Environment variables for production builds

| Variable | Purpose |
|----------|---------|
| `API_URL` | Must be `https://api.klikk.co.za/api/v1` |
| `SENTRY_DSN` | Sentry DSN for the `klikk-agent-ios` project |
| `SENTRY_ENVIRONMENT` | `production` |
| `SENTRY_RELEASE` | Git tag (e.g. `v1.0.0`) — used for Sentry source maps |
| `CAPACITOR_SERVER_URL` | Leave **unset** in production |

## Version bumping

Bump both fields before every TestFlight upload:

```bash
# In src-capacitor/ios/App/App.xcodeproj/project.pbxproj
MARKETING_VERSION = 1.0.1;        # Shown to users
CURRENT_PROJECT_VERSION = 2;      # Must increment for every upload
```

## TestFlight internal testers

Add testers under TestFlight → Internal Testing → Add Testers.
Builds are available immediately after processing (no review required).

## TestFlight external testers / beta review

External testing requires a one-time Beta App Review (~24 h).
Add `beta-testers@tremly.co.za` group under TestFlight → External Groups.
