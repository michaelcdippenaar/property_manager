<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Two-factor authentication</p>
      </div>

      <div class="card p-8">

        <!-- TOTP code entry -->
        <div v-if="!showRecovery" class="space-y-4">
          <div class="flex items-center gap-3 p-3 bg-navy/5 rounded-lg mb-2">
            <ShieldCheck :size="20" class="text-navy flex-shrink-0" />
            <p class="text-sm text-gray-600">Enter the 6-digit code from your authenticator app.</p>
          </div>

          <div>
            <label class="label">Authentication code</label>
            <input
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              class="input text-center text-xl tracking-[0.4em] font-mono"
              placeholder="000000"
              autocomplete="one-time-code"
              @input="onCodeInput"
            />
          </div>

          <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <button
            type="button"
            class="btn-primary w-full justify-center py-2.5"
            :disabled="loading || totpCode.length !== 6"
            @click="handleVerify"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Verifying...' : 'Verify' }}
          </button>

          <button
            type="button"
            class="w-full text-center text-sm text-gray-500 hover:text-navy mt-2"
            @click="showRecovery = true"
          >
            Use a recovery code instead
          </button>
        </div>

        <!-- Recovery code entry -->
        <div v-else class="space-y-4">
          <div class="flex items-center gap-3 p-3 bg-amber-50 border border-amber-100 rounded-lg mb-2">
            <KeyRound :size="20" class="text-amber-600 flex-shrink-0" />
            <p class="text-sm text-amber-800">Enter one of your saved recovery codes (XXXX-XXXX-XXXX format).</p>
          </div>

          <div>
            <label class="label">Recovery code</label>
            <input
              v-model="recoveryCode"
              type="text"
              class="input font-mono uppercase"
              placeholder="XXXX-XXXX-XXXX"
              autocomplete="off"
            />
          </div>

          <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <button
            type="button"
            class="btn-primary w-full justify-center py-2.5"
            :disabled="loading || !recoveryCode.trim()"
            @click="handleRecovery"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Verifying...' : 'Use recovery code' }}
          </button>

          <button
            type="button"
            class="w-full text-center text-sm text-gray-500 hover:text-navy mt-2"
            @click="showRecovery = false"
          >
            Back to authenticator code
          </button>
        </div>

        <!-- 2FA Reset link -->
        <div class="mt-4 pt-4 border-t border-gray-100 text-center">
          <router-link to="/2fa-reset" class="text-xs text-gray-400 hover:text-gray-600">
            Lost access to your authenticator? Reset 2FA
          </router-link>
        </div>
      </div>

      <button
        type="button"
        class="w-full text-center text-xs text-gray-400 hover:text-gray-500 mt-4"
        @click="goBack"
      >
        Back to sign in
      </button>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { AlertCircle, Loader2, ShieldCheck, KeyRound } from 'lucide-vue-next'
import api from '../../api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const twoFaToken = ref((route.query.token as string) || '')
const totpCode = ref('')
const recoveryCode = ref('')
const showRecovery = ref(false)
const loading = ref(false)
const error = ref('')

onMounted(() => {
  if (!twoFaToken.value) {
    router.replace({ name: 'login' })
  }
})

function onCodeInput() {
  // Auto-submit when 6 digits entered
  if (totpCode.value.length === 6) {
    handleVerify()
  }
}

async function handleVerify() {
  if (!totpCode.value || totpCode.value.length !== 6) return
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/2fa/verify/', {
      two_fa_token: twoFaToken.value,
      totp_code: totpCode.value,
    })
    auth._setTokens(data)
    router.replace(auth.homeRoute)
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
    auth._setTokens(data)
    router.replace(auth.homeRoute)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid recovery code.'
    recoveryCode.value = ''
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.replace({ name: 'login' })
}
</script>
