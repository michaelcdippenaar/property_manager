import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'za.co.klikk.agentapp',
  appName: 'Klikk Agent',
  webDir: 'dist/spa',
  server: {
    androidScheme: 'https',
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
      style: 'light',
      backgroundColor: '#2B2D6E',
      overlaysWebView: false,
    },
  },
}

export default config
