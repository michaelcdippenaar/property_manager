# Android Release Signing — Setup Guide

## Why a separate upload key?

Google Play uses a two-key model:
- **Upload key** — you sign the APK/AAB with this before uploading to Play Console.
- **App signing key** — Google re-signs the final binary delivered to devices.
- If the upload key is compromised you can reset it without losing the app.

## Generate the upload keystore (one-time)

```bash
keytool -genkey -v \
  -keystore klikk-agent-upload.jks \
  -alias klikk-agent \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -dname "CN=Klikk Technologies, O=Klikk Technologies, L=Stellenbosch, S=Western Cape, C=ZA"
```

Store the resulting `.jks` file and passwords in **1Password** under the
*Klikk — Android signing* vault item. Never commit this file or any passwords
to source control.

## Create keystore.properties

Copy the template and fill in real values:

```bash
cp agent-app/src-capacitor/android/keystore.properties.template \
   agent-app/src-capacitor/android/keystore.properties
```

Fill in:
```properties
storeFile=../klikk-agent-upload.jks   # relative to android/ directory
storePassword=<store password>
keyAlias=klikk-agent
keyPassword=<key password>
```

The `.gitignore` in the `android/` directory already excludes `keystore.properties`.

## Build the release AAB

```bash
# From agent-app/
npm run build:android

# Then from src-capacitor/android/
./gradlew bundleRelease
```

Output: `app/build/outputs/bundle/release/app-release.aab`

## Upload to Play Store (internal track)

1. Open Play Console → Klikk Agent → Production/Internal Testing
2. Create a new release → upload the `.aab`
3. Add release notes (see `store-metadata/android/` directory)
4. Rollout to internal testers (immediately available)

## Version bumping

Bump `versionCode` (must increment every upload) and `versionName` in
`app/build.gradle`:

```groovy
versionCode 2        // monotonically increasing integer
versionName "1.0.1"  // semantic version shown to users
```

Or pass via Gradle flags:

```bash
./gradlew bundleRelease -PversionCode=2 -PversionName=1.0.1
```

## CI/CD (GitHub Actions)

The release workflow (`agent-app-release.yml`) reads the keystore from
encrypted GitHub secrets and writes `keystore.properties` at build time:

| Secret name | Content |
|-------------|---------|
| `ANDROID_KEYSTORE_BASE64` | Base64-encoded `.jks` file |
| `ANDROID_KEYSTORE_STORE_PASSWORD` | storePassword |
| `ANDROID_KEYSTORE_KEY_ALIAS` | keyAlias |
| `ANDROID_KEYSTORE_KEY_PASSWORD` | keyPassword |
| `SENTRY_DSN_ANDROID` | Sentry DSN for the android project |

## Play Store internal track — first-time setup

1. Play Console → Setup → App signing → enroll in Play App Signing
2. Upload your signing key or let Google generate one
3. Download the **upload certificate** and keep it — needed if you reset later
