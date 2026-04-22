<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Reset two-factor authentication</p>
      </div>

      <div class="card p-8">

        <!-- Request reset form -->
        <div v-if="!uid || !token">
          <p class="text-sm text-gray-600 mb-4">
            Enter your email address. We'll send you a link to reset your 2FA using a recovery code.
          </p>

          <div class="space-y-4">
            <div>
              <label class="label">Email</label>
              <input v-model="email" type="email" class="input" placeholder="you@klikk.co.za" required />
            </div>

            <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
              <AlertCircle :size="15" />
              {{ error }}
            </div>

            <div v-if="sent" class="p-3 bg-success-50 rounded-lg text-success-700 text-sm text-center">
              Reset link sent. Check your inbox.
            </div>

            <button
              type="button"
              class="btn-primary w-full justify-center py-2.5"
              :disabled="loading || sent"
              @click="handleRequest"
            >
              <Loader2 v-if="loading" :size="15" class="animate-spin" />
              {{ loading ? 'Sending...' : 'Send reset link' }}
            </button>
          </div>
        </div>

        <!-- Confirm reset form (arrived via email link) -->
        <div v-else>
          <p class="text-sm text-gray-600 mb-4">
            Enter one of your saved recovery codes to confirm the 2FA reset. After this you'll need to re-enroll.
          </p>

          <div class="space-y-4">
            <div>
              <label class="label">Recovery code</label>
              <input v-model="recoveryCode" type="text" class="input font-mono uppercase" placeholder="XXXX-XXXX-XXXX" autocomplete="off" />
            </div>

            <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
              <AlertCircle :size="15" />
              {{ error }}
            </div>

            <div v-if="resetDone" class="p-3 bg-success-50 rounded-lg text-success-700 text-sm text-center">
              2FA has been reset. Please sign in and re-enroll.
            </div>

            <button
              type="button"
              class="btn-primary w-full justify-center py-2.5"
              :disabled="loading || resetDone"
              @click="handleConfirm"
            >
              <Loader2 v-if="loading" :size="15" class="animate-spin" />
              {{ loading ? 'Resetting...' : 'Reset 2FA' }}
            </button>
          </div>
        </div>

        <router-link to="/login" class="block text-center text-sm text-gray-400 hover:text-gray-600 mt-4">
          Back to sign in
        </router-link>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertCircle, Loader2 } from 'lucide-vue-next'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const uid = computed(() => (route.query.uid as string) || '')
const token = computed(() => (route.query.token as string) || '')

const email = ref('')
const recoveryCode = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)
const resetDone = ref(false)

async function handleRequest() {
  if (!email.value.trim()) { error.value = 'Please enter your email.'; return }
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/2fa/reset/request/', { email: email.value.trim() })
    sent.value = true
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to send reset link. Try again.'
  } finally {
    loading.value = false
  }
}

async function handleConfirm() {
  if (!recoveryCode.value.trim()) { error.value = 'Please enter your recovery code.'; return }
  error.value = ''
  loading.value = true
  try {
    await api.post('/auth/2fa/reset/confirm/', {
      uid: uid.value,
      token: token.value,
      recovery_code: recoveryCode.value.trim(),
    })
    resetDone.value = true
    setTimeout(() => router.push('/login'), 2000)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid recovery code or expired link.'
  } finally {
    loading.value = false
  }
}
</script>
