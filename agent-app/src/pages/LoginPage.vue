<template>
  <div class="login-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark"><span>K</span></div>
      <h1 class="login-title">Welcome back</h1>
      <p class="login-sub">Sign in to your agent account</p>
    </div>

    <!-- Form sheet -->
    <div class="login-sheet">

      <!-- iOS-style input card -->
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
          <button class="eye-btn" @click="showPassword = !showPassword" type="button">
            <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" size="18px" color="grey-5" />
          </button>
        </div>
      </div>

      <!-- Error -->
      <p v-if="error" class="error-msg">{{ error }}</p>

      <!-- Sign in button -->
      <button
        class="btn-primary"
        :disabled="loading"
        @click="handleLogin"
      >
        <q-spinner-dots v-if="loading" color="white" size="20px" />
        <span v-else>Sign In</span>
      </button>

      <!-- Divider -->
      <div v-if="googleConfigured" class="divider">
        <span>or continue with</span>
      </div>

      <!-- Google -->
      <div v-if="googleConfigured" ref="googleBtnContainer" class="google-wrap" />

    </div>

    <p class="footer-text">Klikk Property Management &copy; {{ new Date().getFullYear() }}</p>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGoogleAuth } from '../composables/useGoogleAuth'

const router = useRouter()
const auth   = useAuthStore()
const { renderGoogleButton, waitForCredential, isConfigured: googleConfigured } = useGoogleAuth()

const email              = ref('')
const password           = ref('')
const showPassword       = ref(false)
const loading            = ref(false)
const error              = ref('')
const passwordRef        = ref<HTMLInputElement | null>(null)
const googleBtnContainer = ref<HTMLElement | null>(null)

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
    await auth.login(email.value.trim(), password.value)
    await router.replace(auth.homeRoute)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
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
      await auth.loginWithGoogle(credential)
      await router.replace(auth.homeRoute)
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
$navy: $primary;   // use global SCSS token from quasar.variables.scss

.login-page {
  min-height: 100dvh;   // dvh prevents layout jump on iOS Safari
  display: flex;
  flex-direction: column;
  background: $surface;
  font-family: -apple-system, 'SF Pro Text', 'Inter', sans-serif;
}

/* ── Hero ── */
.login-hero {
  background: linear-gradient(160deg, $navy 0%, #1A1B44 100%);
  padding: calc(56px + env(safe-area-inset-top, 0px)) 24px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-mark {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: rgba(255,255,255,0.12);
  border: 1.5px solid rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;

  span {
    font-size: 36px;
    font-weight: 800;
    color: white;
    line-height: 1;
  }
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: white;
  margin: 0 0 4px;
}

.login-sub {
  font-size: 14px;
  color: rgba(255,255,255,0.55);
  margin: 0;
}

/* ── Sheet ── */
.login-sheet {
  flex: 1;
  padding: 28px 16px 24px;
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

  & + .list-row {
    border-top: 0.5px solid rgba(0,0,0,0.08);
  }
}

.row-label {
  font-size: 15px;
  color: #6b7280;
  width: 72px;
  flex-shrink: 0;
}

.row-input {
  flex: 1;
  font-size: 15px;
  color: #111827;
  border: none;
  outline: none;
  background: transparent;
  padding: 14px 0;

  &::placeholder { color: #c0c0c8; }
}

.eye-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

/* ── Error ── */
.error-msg {
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  margin: 0 0 12px;
  padding: 0 8px;
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
  border-radius: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s;
  letter-spacing: 0.01em;

  &:active { opacity: 0.85; transform: scale(0.99); }
  &:disabled { opacity: 0.6; cursor: not-allowed; }
}

/* ── Divider ── */
.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  color: #9ca3af;
  font-size: 13px;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 0.5px;
    background: rgba(0,0,0,0.1);
  }
}

/* ── Google button ── */
.google-wrap {
  display: flex;
  justify-content: center;
}

/* ── Footer ── */
.footer-text {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  padding: 16px 0 calc(16px + env(safe-area-inset-bottom, 0px));
  margin: 0;
}
</style>
