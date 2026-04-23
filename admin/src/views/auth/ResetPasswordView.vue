<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Set a new password</p>
      </div>

      <div class="card p-8">
        <template v-if="!success">
          <form @submit.prevent="handleReset" class="space-y-4">
            <div>
              <label for="reset-password" class="label">New password</label>
              <input id="reset-password" v-model="password" type="password" class="input" placeholder="Min 8 characters" minlength="8" required autocomplete="new-password" data-clarity-mask="True" />
            </div>
            <div>
              <label for="reset-confirm-password" class="label">Confirm password</label>
              <input id="reset-confirm-password" v-model="confirm" type="password" class="input" placeholder="Repeat password" required autocomplete="new-password" data-clarity-mask="True" />
            </div>
            <div v-if="error" role="alert" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
              <AlertCircle :size="15" aria-hidden="true" />
              {{ error }}
            </div>
            <button type="submit" class="btn-primary w-full justify-center py-2.5" :disabled="loading">
              <Loader2 v-if="loading" :size="15" class="animate-spin" />
              {{ loading ? 'Resetting...' : 'Reset password' }}
            </button>
          </form>
        </template>
        <template v-else>
          <div class="text-center space-y-3">
            <CheckCircle :size="40" class="mx-auto text-success-600" />
            <p class="text-gray-700">Password has been reset.</p>
            <router-link to="/login" class="btn-primary inline-flex justify-center w-full py-2.5">
              Sign in
            </router-link>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import { AlertCircle, Loader2, CheckCircle } from 'lucide-vue-next'

const route = useRoute()
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

async function handleReset() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  loading.value = true
  try {
    await api.post('/auth/password-reset/confirm/', {
      uid: route.query.uid,
      token: route.query.token,
      new_password: password.value,
    })
    success.value = true
  } catch (e: any) {
    const detail = e.response?.data?.detail
    error.value = Array.isArray(detail) ? detail.join(' ') : (detail || 'Invalid or expired reset link.')
  } finally {
    loading.value = false
  }
}
</script>
