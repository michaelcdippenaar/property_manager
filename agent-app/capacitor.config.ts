import type { CapacitorConfig } from '@capacitor/cli'

// Production server URL is injected via CAPACITOR_SERVER_URL env var at build time.
// Leave blank in development — Capacitor will serve the bundled www/ assets locally.
const serverUrl = process.env.CAPACITOR_SERVER_URL

const config: CapacitorConfig = {
  appId: 'za.co.klikk.agentapp',
  appName: 'Klikk Agent',
  // Points at the Quasar SPA output directory
  webDir: 'dist/spa',

  server: {
    // Use https for all native WebView requests (Android cleartext protection)
    androidScheme: 'https',
    // Allow live-reload from a dev server when CAPACITOR_SERVER_URL is set.
    // MUST be undefined in production builds — never set this via CI release env.
    ...(serverUrl ? { url: serverUrl } : {}),
    // Allow the native app to load content from the API domain
    allowNavigation: [
      'api.klikk.co.za',
      'agent.klikk.co.za',
    ],
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      launchAutoHide: true,
      backgroundColor: '#2B2D6E',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },

    StatusBar: {
      // Light (white) icons — suits the Navy #2B2D6E header
      style: 'light',
      backgroundColor: '#2B2D6E',  // keep in sync with $primary in quasar.variables.scss
      overlaysWebView: false,
    },

    Keyboard: {
      // Body resize: the body element shrinks to fit the visible area
      // so bottom-pinned inputs scroll into view automatically on iOS
      resize: 'body',
      style: 'light',
      resizeOnFullScreen: true,
    },
  },
}

export default config
