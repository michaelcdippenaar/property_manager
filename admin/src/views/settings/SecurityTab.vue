<template>
  <div class="card p-5 space-y-5 max-w-lg">
    <h3 class="font-semibold text-gray-900">Two-Factor Authentication</h3>

    <p class="text-sm text-gray-500">
      Choose how you receive your second-factor code when signing in.
      Changes take effect on your next login.
    </p>

    <!-- 2FA method toggle -->
    <div class="space-y-3">
      <label
        class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
        :class="selected === 'totp'
          ? 'border-navy bg-navy/5'
          : 'border-gray-200 hover:border-gray-300'"
      >
        <input
          v-model="selected"
          type="radio"
          value="totp"
          class="mt-0.5 accent-navy"
        />
        <div>
          <p class="text-sm font-medium text-gray-900">Authenticator app (TOTP)</p>
          <p class="text-xs text-gray-500 mt-0.5">
            Use Google Authenticator, Authy, or any TOTP-compatible app.
          </p>
        </div>
      </label>

      <label
        class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
        :class="selected === 'email'
          ? 'border-navy bg-navy/5'
          : 'border-gray-200 hover:border-gray-300'"
      >
        <input
          v-model="selected"
          type="radio"
          value="email"
          class="mt-0.5 accent-navy"
        />
        <div>
          <p class="text-sm font-medium text-gray-900">Email OTP</p>
          <p class="text-xs text-gray-500 mt-0.5">
            Receive a 6-digit code by email each time you sign in.
          </p>
        </div>
      </label>
    </div>

    <div v-if="successMsg" class="flex items-center gap-2 text-sm text-success-600">
      <CheckCircle2 :size="15" />
      {{ successMsg }}
    </div>
    <div v-if="errorMsg" class="flex items-center gap-2 text-sm text-danger-600">
      <AlertCircle :size="15" />
      {{ errorMsg }}
    </div>

    <button
      class="btn-primary"
      :disabled="saving || selected === original"
      @click="save"
    >
      <Loader2 v-if="saving" :size="15" class="animate-spin" />
      Save preference
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-vue-next'
import api from '../../api'

const selected = ref<'totp' | 'email'>('totp')
const original = ref<'totp' | 'email'>('totp')
const saving = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me/')
    selected.value = data.two_fa_method ?? 'totp'
    original.value = selected.value
  } catch {
    // Silently ignore — user will see the default
  }
})

async function save() {
  saving.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    await api.patch('/auth/me/', { two_fa_method: selected.value })
    original.value = selected.value
    successMsg.value = '2FA method updated. Takes effect on your next sign-in.'
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || 'Failed to update preference.'
  } finally {
    saving.value = false
  }
}
</script>
