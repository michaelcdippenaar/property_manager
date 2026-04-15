<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Admin Portal</p>
      </div>

      <div v-if="registered" class="mb-4 p-3 bg-success-50 border border-success-100 rounded-lg text-success-700 text-sm text-center">
        Account created successfully. Sign in to continue.
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

          <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <div class="flex items-center justify-end">
            <router-link to="/forgot-password" class="text-sm text-navy hover:underline">Forgot password?</router-link>
          </div>

          <button
            type="submit"
            class="btn-primary w-full justify-center py-2.5 mt-2"
            :disabled="loading"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Signing in...' : 'Sign in' }}
          </button>

        </form>

        <!-- Google Sign In (rendered natively by GSI to avoid popup blockers) -->
        <template v-if="google.isConfigured">
          <div class="flex items-center gap-3 my-4">
            <div class="flex-1 h-px bg-gray-200"></div>
            <span class="text-xs text-gray-400">or</span>
            <div class="flex-1 h-px bg-gray-200"></div>
          </div>

          <div ref="googleButtonRef" class="flex justify-center"></div>
        </template>
      </div>

      <p class="text-center text-sm text-gray-500 mt-4">
        Don't have an account?
        <router-link to="/register" class="text-navy font-medium hover:underline">Sign up</router-link>
      </p>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useGoogleAuth } from '../../composables/useGoogleAuth'
import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const google = useGoogleAuth()

const registered = computed(() => route.query.registered === '1')
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const googleButtonRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  if (google.isConfigured && googleButtonRef.value) {
    // Set up credential listener before rendering button
    google.waitForCredential().then(async (credential) => {
      error.value = ''
      try {
        await auth.googleAuth(credential)
        router.push(auth.homeRoute)
      } catch (e: any) {
        if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error' || !e?.response) {
          error.value = 'Cannot connect to server. Please check your internet connection and try again.'
        } else {
          error.value = e.response?.data?.error || e.message || 'Google sign-in failed.'
        }
      }
    }).catch((e) => {
      if (e.message !== 'Google sign-in timed out.') {
        error.value = e.message
      }
    })

    await google.renderGoogleButton(googleButtonRef.value)
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    router.push(auth.homeRoute)
  } catch (e: any) {
    if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error' || !e?.response) {
      error.value = 'Cannot connect to server. Please check your internet connection and try again.'
    } else if (e?.response?.status === 401) {
      error.value = 'Invalid email or password.'
    } else {
      error.value =
        e?.response?.data?.detail ||
        e?.response?.data?.non_field_errors?.[0] ||
        'Sign-in failed.'
    }
  } finally {
    loading.value = false
  }
}
</script>
