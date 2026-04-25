<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Two-factor authentication</p>
      </div>

      <div class="card p-8 space-y-4">

        <div class="flex items-center gap-3 p-3 bg-navy/5 rounded-lg">
          <Mail :size="20" class="text-navy flex-shrink-0" />
          <p class="text-sm text-gray-600">
            We sent a 6-digit code to your email address. Enter it below to sign in.
          </p>
        </div>

        <div>
          <label class="label">Verification code</label>
          <input
            v-model="code"
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
          :disabled="loading || code.length !== 6"
          @click="handleVerify"
        >
          <Loader2 v-if="loading" :size="15" class="animate-spin" />
          {{ loading ? 'Verifying...' : 'Verify' }}
        </button>

        <button
          type="button"
          class="w-full text-center text-sm text-gray-500 hover:text-navy"
          :disabled="resendLoading || resendCooldown > 0"
          @click="handleResend"
        >
          <Loader2 v-if="resendLoading" :size="13" class="animate-spin inline mr-1" />
          <span v-if="resendCooldown > 0">Resend in {{ resendCooldown }}s</span>
          <span v-else>Resend code</span>
        </button>

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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { AlertCircle, Loader2, Mail } from 'lucide-vue-next'
import api from '../../api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const twoFaToken = ref((route.query.token as string) || '')
const code = ref('')
const loading = ref(false)
const error = ref('')

const resendLoading = ref(false)
const resendCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (!twoFaToken.value) {
    router.replace({ name: 'login' })
    return
  }
  // Automatically send the OTP on mount so the user gets the code immediately.
  sendOtp()
})

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
})

function onCodeInput() {
  if (code.value.length === 6) {
    handleVerify()
  }
}

async function sendOtp() {
  resendLoading.value = true
  error.value = ''
  try {
    await api.post('/auth/2fa/email-send/', { two_fa_token: twoFaToken.value })
    startCooldown(60)
  } catch (e: any) {
    if (e.response?.status === 429) {
      error.value = 'Too many requests. Please wait before requesting a new code.'
      startCooldown(60)
    } else {
      error.value = e.response?.data?.detail || 'Failed to send OTP. Please try again.'
    }
  } finally {
    resendLoading.value = false
  }
}

async function handleResend() {
  if (resendCooldown.value > 0) return
  await sendOtp()
}

function startCooldown(seconds: number) {
  resendCooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    resendCooldown.value -= 1
    if (resendCooldown.value <= 0) {
      resendCooldown.value = 0
      if (cooldownTimer) clearInterval(cooldownTimer)
    }
  }, 1000)
}

async function handleVerify() {
  if (!code.value || code.value.length !== 6) return
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/2fa/email-verify/', {
      two_fa_token: twoFaToken.value,
      code: code.value,
    })
    auth._setTokens(data)
    router.replace(auth.homeRoute)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid code. Please try again.'
    code.value = ''
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.replace({ name: 'login' })
}
</script>
