<template>
  <div class="login-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark">
        <span class="logo-wordmark">Klikk<span class="logo-dot">.</span></span>
        <span class="role-pill">TENANT</span>
      </div>
      <h1 class="login-title">Welcome back</h1>
      <p class="login-sub">Sign in to your tenant account</p>
    </div>

    <!-- Form sheet -->
    <div class="login-sheet">

      <div class="list-section">
        <div class="list-row">
          <span class="row-label">Email</span>
          <input
            v-model="email"
            type="email"
            placeholder="your@email.com"
            autocomplete="email"
            class="row-input"
            @keyup.enter="focusPassword"
          />
        </div>
        <div class="list-row">
          <span class="row-label">Password</span>
          <input
            ref="passwordRef"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="••••••••"
            autocomplete="current-password"
            class="row-input"
            @keyup.enter="handleEmailLogin"
          />
          <button class="eye-btn" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword" type="button">
            <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" size="18px" color="grey-5" />
          </button>
        </div>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button class="btn-primary klikk-btn-primary" :disabled="loading" @click="handleEmailLogin">
        <q-spinner-dots v-if="loading" color="white" size="20px" />
        <span v-else>Sign In</span>
      </button>

      <!-- Biometric -->
      <button
        v-if="biometric.isAvailable.value && biometric.hasCredentials.value"
        class="btn-biometric"
        :aria-label="`Sign in with ${biometric.biometryLabel()}`"
        @click="handleBiometricLogin"
      >
        <q-icon :name="biometricIcon" size="22px" />
        <span>Sign in with {{ biometric.biometryLabel() }}</span>
      </button>

      <!-- Divider -->
      <div v-if="googleConfigured" class="divider">
        <span>or continue with</span>
      </div>

      <!-- Google -->
      <div v-if="googleConfigured" ref="googleBtnContainer" class="google-wrap" />

    </div>

    <p class="footer-text">Klikk Property Management &copy; {{ currentYear }}</p>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGoogleAuth } from '../composables/useGoogleAuth'
import { useBiometric } from '../composables/useBiometric'
import { BiometryType } from 'capacitor-native-biometric'

const router = useRouter()
const auth   = useAuthStore()
const { renderGoogleButton, waitForCredential, isConfigured: googleConfigured } = useGoogleAuth()
const biometric = useBiometric()

const email              = ref('')
const password           = ref('')
const showPassword       = ref(false)
const loading            = ref(false)
const error              = ref('')
const passwordRef        = ref<HTMLInputElement | null>(null)
const googleBtnContainer = ref<HTMLElement | null>(null)

const currentYear = computed(() => new Date().getFullYear())

// Icon name for the active biometry type
const biometricIcon = computed(() => {
  switch (biometric.biometryType.value) {
    case BiometryType.FACE_ID:
    case BiometryType.FACE_AUTHENTICATION: return 'face'
    default:                               return 'fingerprint'
  }
})

function focusPassword() {
  passwordRef.value?.focus()
}

async function handleEmailLogin() {
  if (!email.value || !password.value) {
    error.value = 'Please enter your email and password.'
    return
  }
  error.value   = ''
  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    // Save for future biometric login
    await biometric.saveCredentials(email.value.trim(), password.value)
    await router.replace('/dashboard')
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}

async function handleBiometricLogin() {
  error.value   = ''
  loading.value = true
  try {
    const { username, password: storedPassword } = await biometric.authenticate()
    await auth.login(username, storedPassword)
    await router.replace('/dashboard')
  } catch (err: unknown) {
    const msg = (err as Error)?.message || ''
    // User cancelled — don't show an error
    if (!msg.includes('cancel') && !msg.includes('Cancel')) {
      error.value = 'Biometric sign-in failed. Please use your password.'
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await biometric.checkAvailability()

  if (!googleConfigured || !googleBtnContainer.value) return
  const credentialPromise = waitForCredential()
  await renderGoogleButton(googleBtnContainer.value)
  credentialPromise.then(async (credential) => {
    error.value   = ''
    loading.value = true
    try {
      await auth.loginWithGoogle(credential)
      await router.replace('/dashboard')
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: string; detail?: string } } }
      error.value = axiosErr.response?.data?.error || axiosErr.response?.data?.detail || 'Google sign-in failed.'
    } finally {
      loading.value = false
    }
  }).catch(() => {})
})
</script>

<style scoped lang="scss">
$navy: $primary;

.login-page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: $surface;
  font-family: -apple-system, 'SF Pro Text', 'Inter', sans-serif;
}

.login-hero {
  background: linear-gradient(160deg, $navy 0%, #1A1B44 100%);
  padding: calc(64px + env(safe-area-inset-top, 0px)) 24px 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.logo-mark {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
}

.logo-wordmark {
  font-size: 44px;
  font-weight: 800;
  color: white;
  line-height: 1;
  letter-spacing: -0.03em;
}

.logo-dot {
  color: #FF3D7F;
}

.role-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(255, 61, 127, 0.15);
  border: 1px solid rgba(255, 61, 127, 0.30);
  color: #FF3D7F;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  line-height: 1;
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: white;
  margin: 0 0 6px;
}

.login-sub {
  font-size: 14px;
  color: rgba(255,255,255,0.72);
  margin: 0;
}

.login-sheet {
  flex: 1;
  background: $surface;
  border-radius: 28px 28px 0 0;
  margin-top: -32px;
  padding: 32px 20px 24px;
  box-shadow: 0 -6px 32px rgba(0,0,0,0.10);
}

.mode-toggle {
  display: flex;
  background: rgba(0,0,0,0.04);
  border-radius: 10px;
  padding: 3px;
}

.toggle-btn {
  flex: 1;
  padding: 10px;
  font-size: 14px;
  font-weight: 500;
  color: var(--klikk-text-secondary);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;

  &--active {
    background: white;
    color: #111827;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
}

.list-section {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  margin-bottom: 16px;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  min-height: 52px;
  background: white;

  & + .list-row {
    border-top: 0.5px solid var(--klikk-border);
  }
}

.row-label {
  font-size: 15px;
  color: var(--klikk-text-secondary);
  width: 72px;
  flex-shrink: 0;
}

.row-input {
  flex: 1;
  font-size: 15px;
  color: var(--klikk-text-primary);
  border: none;
  outline: none;
  background: transparent;
  padding: 14px 0;

  &::placeholder { color: var(--klikk-text-faint); }
}

.eye-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.error-msg {
  font-size: 13px;
  color: $negative;
  text-align: center;
  margin: 0 0 12px;
  padding: 0 8px;
}

.otp-info {
  font-size: 13px;
  color: var(--klikk-text-secondary);
  text-align: center;
  margin: 0 0 12px;
}

// Mirrors admin .btn-primary — navy bg, accent-pink hover ring, rounded-lg.
.btn-primary {
  width: 100%;
  padding: 16px;
  background: $navy;
  color: white;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: var(--klikk-radius-btn);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s, box-shadow 0.15s, transform 0.15s, opacity 0.15s;
  letter-spacing: 0.01em;

  &:hover:not(:disabled),
  &:focus-visible {
    background: var(--klikk-navy-dark);
    box-shadow: var(--klikk-ring-accent);
    outline: none;
  }

  &:active { opacity: 0.85; transform: scale(0.98); }
  &:disabled { opacity: 0.6; cursor: not-allowed; }
}

.btn-link {
  display: block;
  width: 100%;
  margin-top: 12px;
  text-align: center;
  font-size: 14px;
  color: $navy;
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
}

/* ── Biometric button ── */
.btn-biometric {
  width: 100%;
  margin-top: 12px;
  padding: 14px;
  background: transparent;
  border: 1.5px solid var(--klikk-border-strong);
  border-radius: var(--klikk-radius-btn);
  color: var(--klikk-text-primary);
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: background-color 0.15s, opacity 0.15s;

  &:active { opacity: 0.7; }
}

/* ── Divider ── */
.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  color: var(--klikk-text-muted);
  font-size: 13px;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 0.5px;
    background: var(--klikk-border);
  }
}

/* ── Google button ── */
.google-wrap {
  display: flex;
  justify-content: center;
}

.footer-text {
  text-align: center;
  font-size: 12px;
  color: var(--klikk-text-muted);
  padding: 16px 0 calc(16px + env(safe-area-inset-bottom, 0px));
  margin: 0;
}
</style>
