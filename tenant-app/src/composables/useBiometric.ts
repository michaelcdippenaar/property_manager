import { ref } from 'vue'
import { NativeBiometric, BiometryType } from 'capacitor-native-biometric'

const SERVER_KEY = 'co.klikk.tenant'

export function useBiometric() {
  const isAvailable    = ref(false)
  const biometryType   = ref<BiometryType>(BiometryType.NONE)
  const hasCredentials = ref(false)

  /** Call on mount — populates isAvailable, biometryType, hasCredentials */
  async function checkAvailability() {
    try {
      const result = await NativeBiometric.isAvailable()
      isAvailable.value  = result.isAvailable
      biometryType.value = result.biometryType

      if (result.isAvailable) {
        try {
          await NativeBiometric.getCredentials({ server: SERVER_KEY })
          hasCredentials.value = true
        } catch {
          hasCredentials.value = false
        }
      }
    } catch {
      isAvailable.value = false
    }
  }

  /** Store credentials in the device keychain after a successful login */
  async function saveCredentials(username: string, password: string) {
    if (!isAvailable.value) return
    try {
      await NativeBiometric.setCredentials({ username, password, server: SERVER_KEY })
      hasCredentials.value = true
    } catch {
      // Non-fatal — biometric is optional
    }
  }

  /**
   * Prompt the user with Face ID / Touch ID / fingerprint.
   * Returns { username, password } on success, throws on failure/cancel.
   */
  async function authenticate() {
    const label = biometryLabel(biometryType.value)
    await NativeBiometric.verifyIdentity({
      reason: `Sign in to Klikk`,
      title: `Sign in with ${label}`,
      subtitle: 'Use your biometric to continue',
    })
    return NativeBiometric.getCredentials({ server: SERVER_KEY })
  }

  async function clearCredentials() {
    try {
      await NativeBiometric.deleteCredentials({ server: SERVER_KEY })
    } catch { /* ignore */ }
    hasCredentials.value = false
  }

  /** Human-readable label for the active biometry type */
  function biometryLabel(type: BiometryType): string {
    switch (type) {
      case BiometryType.FACE_ID:             return 'Face ID'
      case BiometryType.TOUCH_ID:            return 'Touch ID'
      case BiometryType.FINGERPRINT:         return 'Fingerprint'
      case BiometryType.FACE_AUTHENTICATION: return 'Face Unlock'
      case BiometryType.IRIS_AUTHENTICATION: return 'Iris Scan'
      default:                               return 'Biometrics'
    }
  }

  return {
    isAvailable,
    biometryType,
    hasCredentials,
    biometryLabel: () => biometryLabel(biometryType.value),
    checkAvailability,
    saveCredentials,
    authenticate,
    clearCredentials,
  }
}
