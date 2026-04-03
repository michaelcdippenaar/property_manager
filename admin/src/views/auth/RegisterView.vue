<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Create your account</p>
      </div>

      <div class="card p-8">

        <form @submit.prevent="handleRegister" class="space-y-3">

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">First name</label>
              <input v-model="form.first_name" type="text" class="input" placeholder="John" required />
            </div>
            <div>
              <label class="label">Last name</label>
              <input v-model="form.last_name" type="text" class="input" placeholder="Doe" required />
            </div>
          </div>

          <div>
            <label class="label">Email</label>
            <input v-model="form.email" type="email" class="input" placeholder="you@klikk.co.za" required />
          </div>

          <div>
            <label class="label">Phone <span class="text-gray-400 font-normal">(optional)</span></label>
            <input v-model="form.phone" type="tel" class="input" placeholder="082 123 4567" />
          </div>

          <div>
            <label class="label">Password</label>
            <div class="relative">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-10"
                placeholder="••••••••"
                minlength="8"
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

          <div>
            <label class="label">Confirm password</label>
            <input
              v-model="confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="••••••••"
              required
            />
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
            {{ loading ? 'Creating account...' : 'Create account' }}
          </button>

        </form>

        <!-- Google Sign Up (rendered natively by GSI to avoid popup blockers) -->
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
        Already have an account?
        <router-link to="/login" class="text-navy font-medium hover:underline">Sign in</router-link>
      </p>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useGoogleAuth } from '../../composables/useGoogleAuth'
import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const google = useGoogleAuth()

const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  password: '',
})
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const googleButtonRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  if (google.isConfigured && googleButtonRef.value) {
    google.waitForCredential().then(async (credential) => {
      error.value = ''
      try {
        await auth.googleAuth(credential)
        router.push(auth.homeRoute)
      } catch (e: any) {
        error.value = e.response?.data?.error || e.message || 'Google sign-in failed.'
      }
    }).catch((e) => {
      if (e.message !== 'Google sign-in timed out.') {
        error.value = e.message
      }
    })

    await google.renderGoogleButton(googleButtonRef.value)
  }
})

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

async function handleRegister() {
  error.value = ''

  if (!emailRegex.test(form.email)) {
    error.value = 'Please enter a valid email address.'
    return
  }

  if (form.password.length < 8) {
    error.value = 'Password must be at least 8 characters.'
    return
  }

  if (form.password !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }

  loading.value = true
  try {
    await auth.register(form)
    // After registration + auto-login, check if user has a valid admin SPA role
    if (auth.isAgent || auth.user?.role === 'admin') {
      router.push(auth.homeRoute)
    } else {
      // Non-admin users (tenant, owner, supplier) — redirect to login with success message
      // They may not have routes in this SPA, so show confirmation
      await auth.logout()
      router.push({ path: '/login', query: { registered: '1' } })
    }
  } catch (e: any) {
    const data = e.response?.data
    if (data) {
      const msg = typeof data === 'string' ? data
        : data.detail || data.email?.[0] || data.password?.[0] || Object.values(data).flat().join(' ')
      error.value = msg || 'Registration failed.'
    } else {
      error.value = 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>
