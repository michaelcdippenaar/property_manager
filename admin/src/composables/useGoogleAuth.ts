import { ref } from 'vue'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const GSI_SCRIPT_URL = 'https://accounts.google.com/gsi/client'

let gsiLoaded = false
let gsiLoadPromise: Promise<void> | null = null

function loadGsiScript(): Promise<void> {
  if (gsiLoaded) return Promise.resolve()
  if (gsiLoadPromise) return gsiLoadPromise

  gsiLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = GSI_SCRIPT_URL
    script.async = true
    script.defer = true
    script.onload = () => { gsiLoaded = true; resolve() }
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'))
    document.head.appendChild(script)
  })

  return gsiLoadPromise
}

// Shared callback resolver — set by promptGoogleSignIn, called by GSI callback
let _resolve: ((credential: string) => void) | null = null
let _reject: ((error: Error) => void) | null = null
let _initialized = false

export function useGoogleAuth() {
  const loading = ref(false)
  const error = ref('')

  /**
   * Initialize GSI and render the Google button into a container element.
   * Call this from onMounted with a ref to the button container div.
   */
  async function renderGoogleButton(container: HTMLElement) {
    if (!GOOGLE_CLIENT_ID || !container) return

    await loadGsiScript()
    const google = (window as any).google

    if (!_initialized) {
      google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response: { credential: string }) => {
          loading.value = false
          if (response.credential && _resolve) {
            _resolve(response.credential)
            _resolve = null
            _reject = null
          } else if (_reject) {
            _reject(new Error('No credential received from Google.'))
            _resolve = null
            _reject = null
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      })
      _initialized = true
    }

    google.accounts.id.renderButton(container, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      width: container.offsetWidth || 320,
      text: 'signin_with',
    })
  }

  /**
   * Returns a promise that resolves with the Google ID token credential.
   * Must be called before the user clicks the Google button.
   * The promise resolves when the GSI callback fires.
   */
  function waitForCredential(): Promise<string> {
    loading.value = true
    error.value = ''

    return new Promise<string>((resolve, reject) => {
      _resolve = (credential) => {
        loading.value = false
        resolve(credential)
      }
      _reject = (err) => {
        loading.value = false
        error.value = err.message
        reject(err)
      }

      // Timeout after 2 minutes
      setTimeout(() => {
        if (_reject) {
          loading.value = false
          _reject(new Error('Google sign-in timed out.'))
          _resolve = null
          _reject = null
        }
      }, 120000)
    })
  }

  return {
    renderGoogleButton,
    waitForCredential,
    loading,
    error,
    isConfigured: !!GOOGLE_CLIENT_ID,
  }
}
