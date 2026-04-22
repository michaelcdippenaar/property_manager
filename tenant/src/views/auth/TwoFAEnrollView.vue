<template>
  <div class="h-dvh flex flex-col bg-surface overflow-y-auto">
    <!-- Header -->
    <div class="bg-navy px-6 pt-16 pb-10 flex flex-col items-center" style="padding-top: calc(4rem + env(safe-area-inset-top))">
      <div class="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-4">
        <ShieldCheck :size="28" class="text-white" />
      </div>
      <h1 class="text-white text-2xl font-bold">Set up 2FA</h1>
      <p class="text-white/60 text-sm mt-1">Add an extra layer of security</p>
    </div>

    <div class="flex-1 px-5 pt-8 pb-8">

      <!-- Step 1: QR code -->
      <div v-if="step === 1">
        <p class="text-sm text-gray-600 text-center mb-5">Scan this code with your authenticator app (Google Authenticator, Authy, etc.)</p>

        <div v-if="loadingSetup" class="flex justify-center py-8">
          <Loader2 :size="28" class="animate-spin text-navy" />
        </div>

        <div v-else-if="setupData" class="flex flex-col items-center gap-4 mb-6">
          <img
            v-if="setupData.qr_code_png_base64"
            :src="`data:image/png;base64,${setupData.qr_code_png_base64}`"
            alt="TOTP QR code"
            class="w-44 h-44 rounded-2xl border border-gray-200 p-2"
          />
          <details class="w-full">
            <summary class="text-xs text-gray-400 text-center cursor-pointer">Can't scan? Enter key manually</summary>
            <p class="text-xs font-mono text-center bg-gray-50 rounded-xl p-3 mt-2 break-all select-all text-gray-700">{{ setupData.secret }}</p>
          </details>
        </div>

        <p v-if="setupError" class="text-danger-600 text-sm text-center mb-4">{{ setupError }}</p>

        <button
          class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base"
          :disabled="!setupData"
          @click="step = 2"
        >
          I've added the account
        </button>
      </div>

      <!-- Step 2: Verify -->
      <div v-else-if="step === 2">
        <p class="text-sm text-gray-600 text-center mb-5">Enter the 6-digit code from your authenticator app to confirm it's working.</p>

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
            />
          </div>
        </div>

        <p v-if="verifyError" class="text-danger-600 text-sm text-center mb-4">{{ verifyError }}</p>

        <button
          class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base mb-3"
          :disabled="verifyLoading || totpCode.length !== 6"
          @click="handleConfirm"
        >
          <span v-if="!verifyLoading">Activate 2FA</span>
          <Loader2 v-else :size="20" class="animate-spin mx-auto" />
        </button>

        <button class="w-full py-2 text-sm text-gray-400" @click="step = 1">Back</button>
      </div>

      <!-- Step 3: Recovery codes -->
      <div v-else-if="step === 3">
        <p class="text-sm text-gray-700 font-semibold mb-1">Save your recovery codes</p>
        <p class="text-xs text-gray-500 mb-4">Each code can only be used once. Store them somewhere safe.</p>

        <div class="grid grid-cols-2 gap-2 mb-4">
          <div v-for="code in recoveryCodes" :key="code" class="font-mono text-xs bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-center select-all text-gray-700">{{ code }}</div>
        </div>

        <div class="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-xs text-amber-700 mb-5">
          These codes will not be shown again. Save them before continuing.
        </div>

        <button class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base" @click="finish">
          I've saved my codes
        </button>
      </div>

    </div>

    <!-- Skip footer (optional 2FA for tenants) -->
    <div v-if="!isRequired && step < 3" class="pb-6 text-center safe-bottom">
      <button class="text-xs text-gray-400" @click="skip">Skip — I'll set this up later</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { ShieldCheck, Loader2 } from 'lucide-vue-next'
import api from '../../api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isRequired = computed(() => route.query.required === '1')

const step = ref(1)
const loadingSetup = ref(false)
const setupError = ref('')
const setupData = ref<{ secret: string; qr_code_png_base64?: string } | null>(null)

const totpCode = ref('')
const verifyLoading = ref(false)
const verifyError = ref('')

const recoveryCodes = ref<string[]>([])

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

function finish() {
  router.replace({ name: 'home' })
}

function skip() {
  router.replace({ name: 'home' })
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
