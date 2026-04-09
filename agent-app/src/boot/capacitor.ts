import { boot } from 'quasar/wrappers'
import { Platform } from 'quasar'

export default boot(async () => {
  // Only run native Capacitor setup in app context (not browser dev)
  if (!Platform.is.capacitor) return

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
})
