# Deep Links — iOS Universal Links + Android App Links

## URL scheme

The app handles two URL types:

| Type | Example URL | Notes |
|------|-------------|-------|
| Universal Link (iOS) / App Link (Android) | `https://agent.klikk.co.za/viewings/42` | Preferred — opens directly in app |
| Custom scheme | `za.co.klikk.agentapp://viewings/42` | Fallback if domain verification fails |

## Route mapping (hash router)

Because Quasar uses hash-mode routing (`#`), the path after the domain is
a URL fragment and is not sent to the server. The deep-link URL that gets
verified against AASA/assetlinks only needs to match the host; the fragment
is handled entirely client-side by Vue Router.

| Deep-link URL | Vue Router route |
|---------------|-----------------|
| `https://agent.klikk.co.za/#/viewings/42` | `viewing-detail` |
| `https://agent.klikk.co.za/#/viewings/42/lease` | `create-lease` |
| `https://agent.klikk.co.za/#/properties/7` | `property-detail` |
| `https://agent.klikk.co.za/#/leases` | `leases` |

## iOS — Apple App Site Association (AASA)

Host the following JSON at:
`https://agent.klikk.co.za/.well-known/apple-app-site-association`

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["<TEAM_ID>.za.co.klikk.agentapp"],
        "components": [
          { "/": "/*", "comment": "Match all paths — router handles routing client-side" }
        ]
      }
    ]
  }
}
```

Replace `<TEAM_ID>` with the 10-character Apple Developer Team ID
(visible in App Store Connect → Membership).

Requirements:
- Served over HTTPS with a valid certificate
- Content-Type: `application/json`
- No redirects on this URL
- CDN: ensure the CDN does not cache a stale version

The `com.apple.developer.associated-domains` entitlement is already configured
in `App/App/App.entitlements`:
```xml
<string>applinks:agent.klikk.co.za</string>
<string>applinks:klikk.co.za</string>
```

## Android — Digital Asset Links (assetlinks.json)

Host the following JSON at:
`https://agent.klikk.co.za/.well-known/assetlinks.json`

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "za.co.klikk.agentapp",
      "sha256_cert_fingerprints": [
        "<UPLOAD_CERT_SHA256_FINGERPRINT>"
      ]
    }
  }
]
```

Get the fingerprint from the upload certificate:
```bash
keytool -list -v -keystore klikk-agent-upload.jks -alias klikk-agent \
  | grep "SHA256:"
```

Or find it in Play Console → Setup → App integrity → App signing key certificate.

The `android:autoVerify="true"` attribute is already set in
`AndroidManifest.xml` for the `https://agent.klikk.co.za` intent filter.

## Testing deep links (local / staging)

```bash
# iOS Simulator
xcrun simctl openurl booted 'za.co.klikk.agentapp://viewings/42'

# Android Emulator
adb shell am start -a android.intent.action.VIEW \
  -d 'za.co.klikk.agentapp://viewings/42' za.co.klikk.agentapp
```
