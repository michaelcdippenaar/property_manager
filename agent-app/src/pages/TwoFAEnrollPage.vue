<template>
  <div class="enroll-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark">
        <span class="logo-wordmark">Klikk<span class="logo-dot">.</span></span>
        <span class="role-pill">SECURITY</span>
      </div>
      <h1 class="login-title">Set up 2FA</h1>
      <p class="login-sub">Protect your account with an authenticator app</p>
    </div>

    <div class="enroll-sheet">

      <!-- Hard-blocked notice -->
      <div v-if="isBlocked" class="notice notice-danger">
        2FA is required for your account. You must enroll before accessing Klikk.
      </div>

      <!-- Optional 2FA prompt (owner role, DEC-018) -->
      <div v-else-if="isOptional" class="notice notice-info">
        Two-factor authentication is optional for your role but strongly recommended. You can skip this for now and set it up later from your profile.
      </div>

      <!-- Step 1: QR code -->
      <div v-if="step === 1">
        <p class="step-hint">Open your authenticator app and scan this QR code.</p>

        <div v-if="loadingSetup" class="loading-wrap">
          <q-spinner-dots color="primary" size="32px" />
        </div>

        <div v-else-if="setupData" class="qr-wrap">
          <img
            v-if="setupData.qr_code_png_base64"
            :src="`data:image/png;base64,${setupData.qr_code_png_base64}`"
            alt="TOTP QR Code"
            class="qr-img"
          />
          <p class="manual-hint">Can't scan? Enter this key manually:</p>
          <p class="secret-text">{{ setupData.secret }}</p>
        </div>

        <p v-if="setupError" class="error-msg">{{ setupError }}</p>

        <button class="btn-primary" @click="step = 2" :disabled="!setupData">
          I've added the account
        </button>
      </div>

      <!-- Step 2: Verify code -->
      <div v-else-if="step === 2">
        <p class="step-hint">Enter the 6-digit code shown in your authenticator app.</p>

        <div class="list-section">
          <div class="list-row">
            <span class="row-label">Code</span>
            <input
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              placeholder="000000"
              autocomplete="one-time-code"
              class="row-input text-center tracking-widest font-mono text-lg"
            />
          </div>
        </div>

        <p v-if="verifyError" class="error-msg">{{ verifyError }}</p>

        <button class="btn-primary" :disabled="verifyLoading || totpCode.length !== 6" @click="handleConfirm">
          <q-spinner-dots v-if="verifyLoading" color="white" size="20px" />
          <span v-else>Activate 2FA</span>
        </button>

        <button class="btn-link" @click="step = 1">Back</button>
      </div>

      <!-- Step 3: Recovery codes -->
      <div v-else-if="step === 3">
        <p class="step-hint">Save these recovery codes. Each can only be used once.</p>

        <div class="recovery-grid">
          <div v-for="code in recoveryCodes" :key="code" class="recovery-code">{{ code }}</div>
        </div>

        <button class="btn-secondary" @click="copyAll">
          {{ copied ? 'Copied!' : 'Copy all codes' }}
        </button>

        <div class="warning-box">
          These codes will not be shown again. Save them before continuing.
        </div>

        <button class="btn-primary" @click="finish">I've saved my codes</button>
      </div>

      <!-- Skip: optional flow (owner, DEC-018) or grace-period required-role -->
      <button
        v-if="(isOptional || (isRequired && !isBlocked)) && step < 3"
        class="btn-link"
        :disabled="skipLoading"
        @click="skip"
      >
        {{ skipLoading ? 'Skipping...' : 'Skip for now' }}
      </button>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../boot/axios'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const twoFaToken = ref((route.query.token as string) || '')
const isRequired = computed(() => route.query.required === '1')
const isBlocked = computed(() => route.query.blocked === '1')
/** Owner optional-2FA flow (DEC-018): tokens already issued, user can skip. */
const isOptional = computed(() => route.query.optional === '1')

const step = ref(1)
const loadingSetup = ref(false)
const setupError = ref('')
const setupData = ref<{ secret: string; qr_code_png_base64?: string } | null>(null)

const totpCode = ref('')
const verifyLoading = ref(false)
const verifyError = ref('')

const recoveryCodes = ref<string[]>([])
const copied = ref(false)
const skipLoading = ref(false)

onMounted(async () => {
  await loadSetup()
})

async function loadSetup() {
  loadingSetup.value = true
  setupError.value = ''
  try {
    const { data } = await api.post('/auth/2fa/setup/')
    setupData.value = data
  } catch (e: any) {
    setupError.value = e.response?.data?.detail || 'Failed to load 2FA setup.'
  } finally {
    loadingSetup.value = false
  }
}

async function handleConfirm() {
  if (totpCode.value.length !== 6) return
  verifyError.value = ''
  verifyLoading.value = true
  try {
    const { data } = await api.post('/auth/2fa/setup/confirm/', { totp_code: totpCode.value })
    recoveryCodes.value = data.recovery_codes || []
    step.value = 3
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || 'Invalid code.'
    totpCode.value = ''
  } finally {
    verifyLoading.value = false
  }
}

async function copyAll() {
  try {
    await navigator.clipboard.writeText(recoveryCodes.value.join('\n'))
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch { /* ignore */ }
}

function finish() {
  auth.suggestTwoFASetup = false
  router.replace(auth.homeRoute)
}

async function skip() {
  if (isOptional.value) {
    // Owner optional flow: call the skip endpoint to stamp skipped_2fa_setup_at (DEC-018)
    skipLoading.value = true
    try {
      await auth.skipTwoFASetup()
    } catch {
      // Non-fatal — proceed to dashboard anyway
      auth.suggestTwoFASetup = false
    } finally {
      skipLoading.value = false
    }
  }
  // For grace-period required-role users, tokens are already set — just navigate home
  router.replace(auth.homeRoute)
}
</script>

<style scoped lang="scss">
$navy: $primary;

.enroll-page {
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

.logo-mark { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 24px; }
.logo-wordmark { font-size: 44px; font-weight: 800; color: white; line-height: 1; letter-spacing: -0.03em; }
.logo-dot { color: #FF3D7F; }
.role-pill {
  display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 20px;
  background: rgba(255, 61, 127, 0.15); border: 1px solid rgba(255, 61, 127, 0.30);
  color: #FF3D7F; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; line-height: 1;
}
.login-title { font-size: 26px; font-weight: 700; color: white; margin: 0 0 6px; }
.login-sub { font-size: 14px; color: rgba(255,255,255,0.72); margin: 0; }

.enroll-sheet {
  flex: 1;
  background: $surface;
  border-radius: 28px 28px 0 0;
  margin-top: -32px;
  padding: 28px 20px calc(24px + env(safe-area-inset-bottom, 0px));
  box-shadow: 0 -6px 32px rgba(0,0,0,0.10);
  overflow-y: auto;
}

.notice {
  padding: 12px 16px; border-radius: 12px; font-size: 13px; margin-bottom: 16px;
  &.notice-danger { background: #FFF1F2; border: 1px solid #FECDD3; color: #BE123C; }
  &.notice-info   { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; }
}

.step-hint { font-size: 14px; color: var(--klikk-text-secondary); margin: 0 0 16px; }

.loading-wrap { display: flex; justify-content: center; padding: 32px 0; }

.qr-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; margin-bottom: 20px; }
.qr-img { width: 180px; height: 180px; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 8px; }
.manual-hint { font-size: 12px; color: var(--klikk-text-secondary); }
.secret-text { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; color: var(--klikk-text-primary); word-break: break-all; text-align: center; background: rgba(0,0,0,0.04); padding: 8px 12px; border-radius: 8px; }

.list-section { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.07); margin-bottom: 16px; }
.list-row { display: flex; align-items: center; gap: 12px; padding: 0 16px; min-height: 52px; background: white; }
.row-label { font-size: 15px; color: var(--klikk-text-secondary); width: 72px; flex-shrink: 0; }
.row-input { flex: 1; font-size: 15px; color: var(--klikk-text-primary); border: none; outline: none; background: transparent; padding: 14px 0; &::placeholder { color: var(--klikk-text-faint); } }

.error-msg { font-size: 13px; color: $negative; text-align: center; margin: 0 0 12px; }

.recovery-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
.recovery-code { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.06); border-radius: 8px; padding: 8px 6px; text-align: center; color: var(--klikk-text-primary); }

.warning-box { background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #92400E; margin: 12px 0; }

.btn-primary {
  width: 100%; padding: 16px; background: $navy; color: white; font-size: 16px; font-weight: 600;
  border: none; border-radius: var(--klikk-radius-btn); cursor: pointer; display: flex; align-items: center; justify-content: center;
  margin-bottom: 8px; &:disabled { opacity: 0.6; cursor: not-allowed; }
}
.btn-secondary {
  width: 100%; padding: 12px; background: white; color: $navy; font-size: 14px; font-weight: 500;
  border: 1px solid rgba(43,45,110,0.25); border-radius: var(--klikk-radius-btn); cursor: pointer; display: flex; align-items: center; justify-content: center; margin-bottom: 12px;
}
.btn-link {
  display: block; width: 100%; margin-top: 8px; text-align: center; font-size: 14px;
  color: var(--klikk-text-secondary); font-weight: 500; background: none; border: none; cursor: pointer; padding: 4px 0;
  &:disabled { opacity: 0.6; cursor: not-allowed; }
}
</style>
