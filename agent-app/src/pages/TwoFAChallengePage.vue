<template>
  <div class="login-page">

    <!-- Navy hero -->
    <div class="login-hero">
      <div class="logo-mark">
        <span class="logo-wordmark">Klikk<span class="logo-dot">.</span></span>
        <span class="role-pill">2FA</span>
      </div>
      <h1 class="login-title">Verification required</h1>
      <p class="login-sub">Enter your authenticator code to continue</p>
    </div>

    <!-- TOTP code form -->
    <div v-if="!showRecovery" class="login-sheet">

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
            @input="onCodeInput"
          />
        </div>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button class="btn-primary" :disabled="loading || totpCode.length !== 6" @click="handleVerify">
        <q-spinner-dots v-if="loading" color="white" size="20px" />
        <span v-else>Verify</span>
      </button>

      <button class="btn-link" @click="showRecovery = true">Use a recovery code instead</button>
    </div>

    <!-- Recovery code form -->
    <div v-else class="login-sheet">

      <p class="reset-hint">Enter one of your saved recovery codes (XXXX-XXXX-XXXX).</p>

      <div class="list-section">
        <div class="list-row">
          <span class="row-label">Code</span>
          <input
            v-model="recoveryCode"
            type="text"
            placeholder="XXXX-XXXX-XXXX"
            autocomplete="off"
            class="row-input font-mono uppercase"
          />
        </div>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button class="btn-primary" :disabled="loading || !recoveryCode.trim()" @click="handleRecovery">
        <q-spinner-dots v-if="loading" color="white" size="20px" />
        <span v-else>Use recovery code</span>
      </button>

      <button class="btn-link" @click="showRecovery = false; error = ''">Back to authenticator</button>
    </div>

    <div class="server-badge">
      <span class="server-dot" />
      {{ apiHost }}
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
const totpCode = ref('')
const recoveryCode = ref('')
const showRecovery = ref(false)
const loading = ref(false)
const error = ref('')

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

onMounted(() => {
  if (!twoFaToken.value) router.replace('/login')
})

function onCodeInput() {
  if (totpCode.value.length === 6) handleVerify()
}

async function handleVerify() {
  if (totpCode.value.length !== 6) return
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/2fa/verify/', {
      two_fa_token: twoFaToken.value,
      totp_code: totpCode.value,
    })
    auth.setTokensFromTwoFA(data)
    await router.replace(auth.homeRoute)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid code. Please try again.'
    totpCode.value = ''
  } finally {
    loading.value = false
  }
}

async function handleRecovery() {
  if (!recoveryCode.value.trim()) return
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/2fa/recovery/', {
      two_fa_token: twoFaToken.value,
      recovery_code: recoveryCode.value.trim(),
    })
    auth.setTokensFromTwoFA(data)
    await router.replace(auth.homeRoute)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid recovery code.'
    recoveryCode.value = ''
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

.login-sheet {
  flex: 1;
  background: $surface;
  border-radius: 28px 28px 0 0;
  margin-top: -32px;
  padding: 32px 20px 16px;
  box-shadow: 0 -6px 32px rgba(0,0,0,0.10);
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

.error-msg {
  font-size: 13px;
  color: $negative;
  text-align: center;
  margin: 0 0 12px;
  padding: 0 8px;
}

.reset-hint {
  font-size: 14px;
  color: var(--klikk-text-secondary);
  text-align: center;
  margin: 0 0 20px;
}

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
  transition: background-color 0.15s, opacity 0.15s;

  &:disabled { opacity: 0.6; cursor: not-allowed; }
}

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

.server-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 11px;
  color: var(--klikk-text-faint);
  font-family: 'SF Mono', 'Fira Code', monospace;
  padding: 10px 0 calc(12px + env(safe-area-inset-bottom, 0px));
}

.server-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: $positive;
  flex-shrink: 0;
}
</style>
