# Klikk Agent App

Property viewings, prospect capture, and lease creation for agents using Quasar + Capacitor.

## Quick Start

### Prerequisites

- Node.js 18+
- `npm` (included with Node.js)
- Backend API running on `http://localhost:8000` (default) or configured via `.env.*` file

### Development

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment**
   Copy `.env.development.example` to `.env.development` and populate the required values:
   ```bash
   cp .env.development.example .env.development
   # Edit .env.development and set:
   # - API_URL (default: http://localhost:8000/api/v1)
   # - GOOGLE_CLIENT_ID (obtain from Google Cloud Console)
   ```

3. **Run the dev server**
   ```bash
   npm run dev
   ```
   The app opens at `http://localhost:5176` by default.

## Environment Variables

### Development (`.env.development`)
See `.env.development.example` for all available variables.
- `API_URL` — Backend API base URL (default: `http://localhost:8000/api/v1`)
- `GOOGLE_CLIENT_ID` — Google OAuth client ID (required for login)
- Sentry variables — leave blank to skip error reporting in dev

### Staging (`.env.staging`)
See `.env.staging.example` for all available variables.
- Secrets injected at build time via CI environment variables
- Built with `npm run build`

### Production (`.env.production`)
See `.env.production.example` for all available variables.
- All secrets required; injected at build time via CI environment variables
- Built with `npm run build`

## Build

```bash
# Web/PWA build
npm run build

# Capacitor iOS
npm run build:ios

# Capacitor Android
npm run build:android
```

## Mobile Deployment

See `docs/` for detailed guides:
- [iOS TestFlight](docs/ios-testflight.md)
- [Android Signing](docs/android-signing.md)
- [Universal Links](docs/universal-links.md)

## Architecture

- **Framework:** Quasar v2 + Vue 3
- **State Management:** Pinia
- **Styling:** SASS, Quasar design tokens
- **Mobile:** Capacitor (iOS + Android)
- **Error Tracking:** Sentry
- **Auth:** Google OAuth + JWT

## Git Hooks

The project uses pre-commit hooks (via husky) to lint staged files. If a hook fails, fix the issues and commit again.

## Support

For issues or questions, refer to the [Quasar Documentation](https://quasar.dev) or contact the dev team.
