<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-md">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Set up two-factor authentication</p>
      </div>

      <!-- Hard-blocked banner -->
      <div v-if="isBlocked" class="mb-4 p-4 bg-danger-50 border border-danger-200 rounded-xl text-danger-700 text-sm flex items-start gap-3">
        <ShieldAlert :size="18" class="flex-shrink-0 mt-0.5" />
        <div>
          <p class="font-semibold">2FA required to continue</p>
          <p class="text-xs mt-1">Your grace period has ended. You must set up two-factor authentication before you can access Klikk.</p>
        </div>
      </div>

      <!-- Optional 2FA prompt (owner role, DEC-018) -->
      <div v-else-if="isOptional" class="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-blue-800 text-sm flex items-start gap-3">
        <ShieldCheck :size="18" class="flex-shrink-0 mt-0.5" />
        <div>
          <p class="font-semibold">Secure your account with 2FA</p>
          <p class="text-xs mt-1">Two-factor authentication is optional for your role but strongly recommended. You can skip this for now and set it up later from your profile.</p>
        </div>
      </div>

      <!-- Grace period nudge -->
      <div v-else-if="isRequired" class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm flex items-start gap-3">
        <ShieldCheck :size="18" class="flex-shrink-0 mt-0.5" />
        <div>
          <p class="font-semibold">2FA enrollment recommended</p>
          <p class="text-xs mt-1">Your account role requires 2FA. You can skip for now but will be required to enroll within your grace period.</p>
        </div>
      </div>

      <!-- Steps -->
      <div class="card p-6 space-y-6">

        <!-- Step 1: QR -->
        <div v-if="step === 1">
          <h2 class="text-base font-semibold text-gray-800 mb-3">Step 1 — Scan QR code</h2>
          <p class="text-sm text-gray-500 mb-4">Open your authenticator app (Google Authenticator, Authy, 1Password, etc.) and scan the code below.</p>

          <div v-if="loadingSetup" class="flex justify-center py-8">
            <Loader2 :size="28" class="animate-spin text-navy" />
          </div>

          <div v-else-if="setupData" class="space-y-4">
            <div class="flex justify-center">
              <img
                v-if="setupData.qr_code_png_base64"
                :src="`data:image/png;base64,${setupData.qr_code_png_base64}`"
                alt="TOTP QR Code"
                class="w-48 h-48 rounded-lg border border-gray-200 p-2"
              />
            </div>

            <details class="text-xs">
              <summary class="text-gray-400 cursor-pointer hover:text-gray-600">Can't scan? Enter manually</summary>
              <div class="mt-2 p-3 bg-gray-50 rounded-lg font-mono text-gray-700 break-all select-all text-center">
                {{ setupData.secret }}
              </div>
            </details>

            <button
              type="button"
              class="btn-primary w-full justify-center py-2.5"
              @click="step = 2"
            >
              I've added the account
              <ChevronRight :size="15" />
            </button>
          </div>

          <div v-if="setupError" class="mt-3 p-3 bg-danger-50 rounded-lg text-danger-700 text-sm flex items-center gap-2">
            <AlertCircle :size="15" />
            {{ setupError }}
          </div>
        </div>

        <!-- Step 2: Verify code -->
        <div v-else-if="step === 2">
          <h2 class="text-base font-semibold text-gray-800 mb-3">Step 2 — Verify your app</h2>
          <p class="text-sm text-gray-500 mb-4">Enter the 6-digit code shown in your authenticator app to confirm it's working.</p>

          <div class="space-y-4">
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
              />
            </div>

            <div v-if="verifyError" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
              <AlertCircle :size="15" />
              {{ verifyError }}
            </div>

            <button
              type="button"
              class="btn-primary w-full justify-center py-2.5"
              :disabled="verifyLoading || totpCode.length !== 6"
              @click="handleConfirm"
            >
              <Loader2 v-if="verifyLoading" :size="15" class="animate-spin" />
              {{ verifyLoading ? 'Verifying...' : 'Confirm and activate 2FA' }}
            </button>

            <button type="button" class="w-full text-center text-sm text-gray-400 hover:text-gray-600" @click="step = 1">
              Back
            </button>
          </div>
        </div>

        <!-- Step 3: Recovery codes -->
        <div v-else-if="step === 3">
          <h2 class="text-base font-semibold text-gray-800 mb-1">Step 3 — Save your recovery codes</h2>
          <p class="text-sm text-gray-500 mb-4">
            Store these codes somewhere safe (password manager, printed copy). Each code can only be used once. If you lose your phone, these are your only way back in.
          </p>

          <div class="grid grid-cols-2 gap-2 mb-4">
            <div
              v-for="code in recoveryCodes"
              :key="code"
              class="font-mono text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-center select-all text-gray-700"
            >
              {{ code }}
            </div>
          </div>

          <button
            type="button"
            class="w-full flex items-center justify-center gap-2 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 mb-4"
            @click="copyAll"
          >
            <Copy :size="14" />
            {{ copied ? 'Copied!' : 'Copy all codes' }}
          </button>

          <div class="flex items-start gap-2 mb-4 p-3 bg-amber-50 border border-amber-100 rounded-lg text-amber-700 text-xs">
            <AlertCircle :size="14" class="flex-shrink-0 mt-0.5" />
            These codes will not be shown again. Make sure you have saved them before continuing.
          </div>

          <button
            type="button"
            class="btn-primary w-full justify-center py-2.5"
            @click="finishEnrollment"
          >
            I've saved my codes — Continue
          </button>
        </div>

      </div>

      <!-- Skip link: optional flow (owner, DEC-018) or grace-period required-role -->
      <div v-if="(isOptional || (isRequired && !isBlocked)) && step < 3" class="text-center mt-4">
        <button
          type="button"
          class="text-xs text-gray-400 hover:text-gray-600"
          :disabled="skipLoading"
          @click="skipEnrollment"
        >
          {{ skipLoading ? 'Skipping...' : 'Skip for now (you\'ll be reminded later)' }}
        </button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { AlertCircle, Loader2, ShieldCheck, ShieldAlert, ChevronRight, Copy } from 'lucide-vue-next'
import api from '../../api'

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
const setupData = ref<{ secret: string; otpauth_uri: string; qr_code_png_base64?: string } | null>(null)

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
    setupError.value = e.response?.data?.detail || 'Failed to load 2FA setup. Please try again.'
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
    verifyError.value = e.response?.data?.detail || 'Invalid code. Please try again.'
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

function finishEnrollment() {
  auth.suggestTwoFASetup = false
  router.replace(auth.homeRoute)
}

async function skipEnrollment() {
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
