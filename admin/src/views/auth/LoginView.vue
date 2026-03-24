<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Admin Portal</p>
      </div>

      <div class="card p-8">
        <form @submit.prevent="handleLogin" class="space-y-4">

          <div>
            <label class="label">Email</label>
            <input
              v-model="email"
              type="email"
              class="input"
              placeholder="you@klikk.co.za"
              required
            />
          </div>

          <div>
            <label class="label">Password</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-10"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <Eye v-if="!showPassword" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div v-if="error" class="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <button
            type="submit"
            class="btn-primary w-full justify-center py-2.5 mt-2"
            :disabled="loading"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>

        </form>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    router.push('/')
  } catch {
    error.value = 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>
