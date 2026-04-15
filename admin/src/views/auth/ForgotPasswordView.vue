<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Reset your password</p>
      </div>

      <div class="card p-8">
        <template v-if="!sent">
          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div>
              <label class="label">Email</label>
              <input v-model="email" type="email" class="input" placeholder="you@klikk.co.za" required />
            </div>
            <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
              <AlertCircle :size="15" />
              {{ error }}
            </div>
            <button type="submit" class="btn-primary w-full justify-center py-2.5" :disabled="loading">
              <Loader2 v-if="loading" :size="15" class="animate-spin" />
              {{ loading ? 'Sending...' : 'Send reset link' }}
            </button>
          </form>
        </template>
        <template v-else>
          <div class="text-center space-y-3">
            <Mail :size="40" class="mx-auto text-navy" />
            <p class="text-gray-700">Check your email for a reset link.</p>
            <p class="text-sm text-gray-500">If you don't see it, check your spam folder.</p>
          </div>
        </template>
      </div>

      <p class="text-center text-sm text-gray-500 mt-4">
        <router-link to="/login" class="text-navy font-medium hover:underline">Back to sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '../../api'
import { AlertCircle, Loader2, Mail } from 'lucide-vue-next'

const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    await api.post('/auth/password-reset/', { email: email.value })
    sent.value = true
  } catch {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
