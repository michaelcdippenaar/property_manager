<template>
  <div class="login-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark">
        <span class="logo-wordmark">Klikk<span class="logo-dot">.</span></span>
        <span class="role-pill">AGENT</span>
      </div>
      <h1 class="login-title">Welcome back</h1>
      <p class="login-sub">Sign in to your agent account</p>
    </div>

    <!-- ── Sign-in form ── -->
    <div v-if="!showReset" class="login-sheet">

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
            @keyup.enter="handleLogin"
          />
          <button class="eye-btn" type="button" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">
            <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" size="18px" color="grey-5" />
          </button>
        </div>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button class="btn-primary" :disabled="loading" @click="handleLogin">
        <q-spinner-dots v-if="loading" color="white" size="20px" />
        <span v-else>Sign In</span>
      </button>

      <button class="btn-link" @click="showReset = true">Forgot password?</button>

      <!-- Divider -->
      <div v-if="googleConfigured" class="divider">
        <span>or continue with</span>
      </div>

      <!-- Google -->
      <div v-if="googleConfigured" ref="googleBtnContainer" class="google-wrap" />

    </div>

    <!-- ── Reset password ── -->
    <div v-else class="login-sheet">

      <p class="reset-hint">Enter your email and we'll send a reset link.</p>

      <div class="list-section">
        <div class="list-row">
          <span class="row-label">Email</span>
          <input
            v-model="resetEmail"
            type="email"
            placeholder="your@email.com"
            autocomplete="email"
            class="row-input"
            @keyup.enter="handleReset"
          />
        </div>
      </div>

      <p v-if="resetError" class="error-msg">{{ resetError }}</p>
      <p v-if="resetSent" class="success-msg">Reset link sent — check your inbox.</p>

      <button class="btn-primary" :disabled="resetLoading || resetSent" @click="handleReset">
        <q-spinner-dots v-if="resetLoading" color="white" size="20px" />
        <span v-else>Send Reset Link</span>
      </button>

      <button class="btn-link" @click="showReset = false; resetSent = false; resetError = ''">
        Back to sign in
      </button>

    </div>

    <!-- Backend server badge -->
    <div class="server-badge">
      <span class="server-dot" />
      {{ apiHost }}
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGoogleAuth } from '../composables/useGoogleAuth'
import { api } from '../boot/axios'

const router = useRouter()
const auth   = useAuthStore()
const { renderGoogleButton, waitForCredential, isConfigured: googleConfigured } = useGoogleAuth()

// ── Sign-in state ──────────────────────────────────────────────────────────
// Pre-fill dev credentials only if both DEV mode AND env vars are set (opt-in pattern)
const devEmail = import.meta.env.DEV ? (import.meta.env.VITE_DEV_LOGIN_EMAIL || '') : ''
const devPassword = import.meta.env.DEV ? (import.meta.env.VITE_DEV_LOGIN_PASSWORD || '') : ''
const email       = ref(devEmail)
const password    = ref(devPassword)
const showPassword = ref(false)
const loading     = ref(false)
const error       = ref('')
const passwordRef        = ref<HTMLInputElement | null>(null)
const googleBtnContainer = ref<HTMLElement | null>(null)

// ── Reset password state ───────────────────────────────────────────────────
const showReset   = ref(false)
const resetEmail  = ref(devEmail)
const resetLoading = ref(false)
const resetError  = ref('')
const resetSent   = ref(false)

// ── Backend indicator ──────────────────────────────────────────────────────
const apiHost = computed(() => {
  try {
    const url = new URL(api.defaults.baseURL as string)
    return url.hostname === 'localhost' || url.hostname === '127.0.0.1'
      ? `localhost:${url.port || 80}`
      : url.hostname
  } catch {
    return api.defaults.baseURL as string
  }
})

function focusPassword() {
  passwordRef.value?.focus()
}

async function handleLogin() {
  if (!email.value || !password.value) {
    error.value = 'Please enter your email and password.'
    return
  }
  error.value   = ''
  loading.value = true
  try {
    const data = await auth.login(email.value.trim(), password.value)
    await _handle2FA(data)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}

async function _handle2FA(data: any) {
  if (!data) { await router.replace(auth.homeRoute); return }

  if (data.two_fa_required && data.two_fa_token) {
    await router.replace({ name: '2fa-challenge', query: { token: data.two_fa_token } })
    return
  }
  if (data.two_fa_enroll_required && data.two_fa_token) {
    const query: Record<string, string> = { token: data.two_fa_token, required: '1' }
    if (data.two_fa_hard_blocked) query.blocked = '1'
    await router.replace({ name: '2fa-enroll', query })
    return
  }
  if (data.two_fa_suggest_setup) {
    // Owner role optional-2FA prompt — tokens already set, can skip (DEC-018)
    await router.replace({ name: '2fa-enroll', query: { optional: '1' } })
    return
  }
  await router.replace(auth.homeRoute)
}

async function handleReset() {
  if (!resetEmail.value.trim()) {
    resetError.value = 'Please enter your email.'
    return
  }
  resetError.value   = ''
  resetLoading.value = true
  try {
    await api.post('/auth/password-reset/', { email: resetEmail.value.trim() })
    resetSent.value = true
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string; email?: string[] } } }
    resetError.value = axiosErr.response?.data?.detail
      || axiosErr.response?.data?.email?.[0]
      || 'Failed to send reset link. Please try again.'
  } finally {
    resetLoading.value = false
  }
}

onMounted(async () => {
  if (!googleConfigured || !googleBtnContainer.value) return
  const credentialPromise = waitForCredential()
  await renderGoogleButton(googleBtnContainer.value)
  credentialPromise.then(async (credential) => {
    error.value   = ''
    loading.value = true
    try {
      const data = await auth.loginWithGoogle(credential)
      await _handle2FA(data)
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

/* ── Hero ── */
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

.logo-dot { color: #FF3D7F; }

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

/* ── Sheet ── */
.login-sheet {
  flex: 1;
  background: $surface;
  border-radius: 28px 28px 0 0;
  margin-top: -32px;
  padding: 32px 20px 16px;
  box-shadow: 0 -6px 32px rgba(0,0,0,0.10);
}

/* ── iOS list section ── */
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

  & + .list-row { border-top: 0.5px solid rgba(0,0,0,0.08); }
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
  min-width: 44px;
  min-height: 44px;
}

/* ── Messages ── */
.error-msg {
  font-size: 13px;
  color: $negative;
  text-align: center;
  margin: 0 0 12px;
  padding: 0 8px;
}

.success-msg {
  font-size: 13px;
  color: $positive;
  text-align: center;
  margin: 0 0 12px;
}

.reset-hint {
  font-size: 14px;
  color: var(--klikk-text-secondary);
  text-align: center;
  margin: 0 0 20px;
}

/* ── Primary button ── */
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

/* ── Text link button ── */
.btn-link {
  display: block;
  width: 100%;
  margin-top: 12px;
  text-align: center;
  font-size: 14px;
  color: var(--klikk-text-secondary);
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
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

/* ── Backend server badge ── */
.server-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 11px;
  color: var(--klikk-text-faint);
  font-family: 'SF Mono', 'Fira Code', monospace;
  padding: 10px 0 calc(12px + env(safe-area-inset-bottom, 0px));
  letter-spacing: 0.02em;
}

.server-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: $positive;
  flex-shrink: 0;
}
</style>
