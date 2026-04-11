import { boot } from 'quasar/wrappers'
import { Platform } from 'quasar'

export default boot(async ({ router }) => {
  // Only run native Capacitor setup in app context (not browser dev)
  if (!Platform.is.capacitor) return

  // Brand color — must match $primary in quasar.variables.scss (#2B2D6E)
  try {
    const { StatusBar, Style } = await import('@capacitor/status-bar')
    await StatusBar.setStyle({ style: Style.Light })
    await StatusBar.setBackgroundColor({ color: '#2B2D6E' })
  } catch {
    // StatusBar not available (e.g., web fallback)
  }

  try {
    const { SplashScreen } = await import('@capacitor/splash-screen')
    await SplashScreen.hide()
  } catch {
    // SplashScreen not available
  }

  // Android hardware back button — prevent users getting stuck
  if (Platform.is.android) {
    try {
      const { App } = await import('@capacitor/app')
      App.addListener('backButton', ({ canGoBack }) => {
        if (canGoBack) {
          router.back()
        } else {
          App.exitApp()
        }
      })
    } catch {
      // App plugin not available
    }
  }
})
