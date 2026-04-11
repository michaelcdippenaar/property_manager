<template>
  <div class="login-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark"><span>K</span></div>
      <h1 class="login-title">Welcome back</h1>
      <p class="login-sub">Sign in to your tenant account</p>
    </div>

    <!-- Form sheet -->
    <div class="login-sheet">

      <!-- Toggle: Email / Phone -->
      <div class="mode-toggle q-mb-md">
        <button
          class="toggle-btn"
          :class="{ 'toggle-btn--active': mode === 'email' }"
          @click="mode = 'email'"
        >Email</button>
        <button
          class="toggle-btn"
          :class="{ 'toggle-btn--active': mode === 'phone' }"
          @click="mode = 'phone'"
        >Phone</button>
      </div>

      <!-- ── Email / Password ─────────────────────────────────── -->
      <template v-if="mode === 'email'">
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
            <button class="eye-btn" @click="showPassword = !showPassword" type="button">
              <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" size="18px" color="grey-5" />
            </button>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="btn-primary" :disabled="loading" @click="handleEmailLogin">
          <q-spinner-dots v-if="loading" color="white" size="20px" />
          <span v-else>Sign In</span>
        </button>
      </template>

      <!-- ── Phone / OTP ──────────────────────────────────────── -->
      <template v-else>
        <template v-if="!otpSent">
          <div class="list-section">
            <div class="list-row">
              <span class="row-label">Phone</span>
              <input
                v-model="phone"
                type="tel"
                placeholder="+27 82 123 4567"
                autocomplete="tel"
                class="row-input"
                @keyup.enter="handleRequestOtp"
              />
            </div>
          </div>

          <p v-if="error" class="error-msg">{{ error }}</p>

          <button class="btn-primary" :disabled="loading" @click="handleRequestOtp">
            <q-spinner-dots v-if="loading" color="white" size="20px" />
            <span v-else>Send OTP</span>
          </button>
        </template>

        <template v-else>
          <div class="list-section">
            <div class="list-row">
              <span class="row-label">OTP</span>
              <input
                v-model="otpCode"
                type="text"
                inputmode="numeric"
                maxlength="6"
                placeholder="123456"
                autocomplete="one-time-code"
                class="row-input"
                @keyup.enter="handleVerifyOtp"
              />
            </div>
          </div>

          <p class="otp-info">Code sent to {{ phone }}</p>
          <p v-if="error" class="error-msg">{{ error }}</p>

          <button class="btn-primary" :disabled="loading" @click="handleVerifyOtp">
            <q-spinner-dots v-if="loading" color="white" size="20px" />
            <span v-else>Verify & Sign In</span>
          </button>

          <button class="btn-link" @click="otpSent = false; otpCode = ''; error = ''">
            Use different number
          </button>
        </template>
      </template>

    </div>

    <p class="footer-text">Klikk Property Management &copy; {{ currentYear }}</p>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth   = useAuthStore()

const mode         = ref<'email' | 'phone'>('email')
const email        = ref('')
const password     = ref('')
const showPassword = ref(false)
const phone        = ref('')
const otpCode      = ref('')
const otpSent      = ref(false)
const loading      = ref(false)
const error        = ref('')
const passwordRef  = ref<HTMLInputElement | null>(null)

const currentYear = computed(() => new Date().getFullYear())

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
    await router.replace('/dashboard')
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}

async function handleRequestOtp() {
  if (!phone.value.trim()) {
    error.value = 'Please enter your phone number.'
    return
  }
  error.value   = ''
  loading.value = true
  try {
    await auth.requestOtp(phone.value.trim())
    otpSent.value = true
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Failed to send OTP. Please try again.'
  } finally {
    loading.value = false
  }
}

async function handleVerifyOtp() {
  if (!otpCode.value.trim()) {
    error.value = 'Please enter the OTP code.'
    return
  }
  error.value   = ''
  loading.value = true
  try {
    await auth.verifyOtp(phone.value.trim(), otpCode.value.trim())
    await router.replace('/dashboard')
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value = axiosErr.response?.data?.detail || 'Invalid OTP. Please try again.'
  } finally {
    loading.value = false
  }
}
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

.login-sheet {
  flex: 1;
  padding: 28px 16px 24px;
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
  color: #6b7280;
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

.error-msg {
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  margin: 0 0 12px;
  padding: 0 8px;
}

.otp-info {
  font-size: 13px;
  color: #6b7280;
  text-align: center;
  margin: 0 0 12px;
}

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

.footer-text {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  padding: 16px 0 calc(16px + env(safe-area-inset-bottom, 0px));
  margin: 0;
}
</style>
