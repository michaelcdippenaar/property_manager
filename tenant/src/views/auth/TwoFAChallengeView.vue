<template>
  <div class="h-dvh flex flex-col bg-surface overflow-y-auto">
    <!-- Header -->
    <div class="bg-navy px-6 pt-16 pb-10 flex flex-col items-center" style="padding-top: calc(4rem + env(safe-area-inset-top))">
      <div class="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-4">
        <ShieldCheck :size="28" class="text-white" />
      </div>
      <h1 class="text-white text-2xl font-bold">Verification</h1>
      <p class="text-white/60 text-sm mt-1">Enter your authenticator code</p>
    </div>

    <!-- Form -->
    <div class="flex-1 px-5 pt-8 pb-8">

      <!-- TOTP form -->
      <div v-if="!showRecovery">
        <div class="list-section mb-4">
          <div class="list-row">
            <span class="text-sm text-gray-500 w-20 flex-shrink-0">Code</span>
            <input
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              placeholder="000000"
              autocomplete="one-time-code"
              class="flex-1 text-center text-xl font-mono tracking-widest text-gray-900 outline-none bg-transparent"
              @input="onCodeInput"
            />
          </div>
        </div>

        <p v-if="error" class="text-danger-600 text-sm text-center mb-4 px-2">{{ error }}</p>

        <button
          class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base ripple"
          :disabled="loading || totpCode.length !== 6"
          @click="handleVerify"
        >
          <span v-if="!loading">Verify</span>
          <Loader2 v-else :size="20" class="animate-spin mx-auto" />
        </button>

        <button class="w-full py-3 text-sm text-gray-500 mt-2" @click="showRecovery = true">
          Use a recovery code instead
        </button>
      </div>

      <!-- Recovery code form -->
      <div v-else>
        <p class="text-sm text-gray-600 mb-4 text-center">Enter one of your saved recovery codes (XXXX-XXXX-XXXX).</p>

        <div class="list-section mb-4">
          <div class="list-row">
            <span class="text-sm text-gray-500 w-20 flex-shrink-0">Code</span>
            <input
              v-model="recoveryCode"
              type="text"
              placeholder="XXXX-XXXX-XXXX"
              autocomplete="off"
              class="flex-1 text-sm font-mono uppercase text-gray-900 outline-none bg-transparent"
            />
          </div>
        </div>

        <p v-if="error" class="text-danger-600 text-sm text-center mb-4 px-2">{{ error }}</p>

        <button
          class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base"
          :disabled="loading || !recoveryCode.trim()"
          @click="handleRecovery"
        >
          <span v-if="!loading">Use recovery code</span>
          <Loader2 v-else :size="20" class="animate-spin mx-auto" />
        </button>

        <button class="w-full py-3 text-sm text-gray-500 mt-2" @click="showRecovery = false; error = ''">
          Back to authenticator code
        </button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { ShieldCheck, Loader2 } from 'lucide-vue-next'
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
  if (!twoFaToken.value) router.replace({ name: 'login' })
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
    auth._setTokens(data)
    router.replace({ name: 'home' })
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
    router.replace({ name: 'home' })
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid recovery code.'
    recoveryCode.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.list-section {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0,0,0,0.07);
}
.list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  min-height: 52px;
  background: white;
}
</style>
