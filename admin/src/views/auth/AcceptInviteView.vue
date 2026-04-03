<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Accept your invitation</p>
      </div>

      <!-- Loading invite details -->
      <div v-if="loadingInvite" class="card p-8 text-center">
        <Loader2 :size="20" class="animate-spin mx-auto text-gray-400" />
        <p class="text-sm text-gray-500 mt-2">Loading invite...</p>
      </div>

      <!-- Invalid invite -->
      <div v-else-if="inviteError" class="card p-8 text-center space-y-3">
        <AlertCircle :size="24" class="mx-auto text-red-500" />
        <p class="text-sm text-red-600">{{ inviteError }}</p>
        <router-link to="/login" class="text-sm text-navy hover:underline">Go to sign in</router-link>
      </div>

      <!-- Invite form -->
      <div v-else class="card p-8">
        <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
          You've been invited to join Klikk as <strong class="capitalize">{{ invite.role }}</strong>.
        </div>

        <form @submit.prevent="handleAccept" class="space-y-3">

          <div>
            <label class="label">Email</label>
            <p class="text-sm font-medium text-gray-700 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg">{{ invite.email }}</p>
          </div>

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

        <!-- Google Sign Up -->
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
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useGoogleAuth } from '../../composables/useGoogleAuth'
import api from '../../api'
import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const google = useGoogleAuth()

const token = (route.query.token as string) || ''
const loadingInvite = ref(true)
const inviteError = ref('')
const invite = reactive({ email: '', role: '' })

const form = reactive({ first_name: '', last_name: '', password: '' })
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const googleButtonRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  // Fetch invite details
  if (!token) {
    inviteError.value = 'No invite token provided.'
    loadingInvite.value = false
    return
  }
  try {
    const { data } = await api.get('/auth/accept-invite/', { params: { token } })
    invite.email = data.email
    invite.role = data.role
  } catch (e: any) {
    inviteError.value = e.response?.data?.detail || 'Invalid or expired invite.'
  } finally {
    loadingInvite.value = false
  }

  // Set up Google auth
  if (google.isConfigured && googleButtonRef.value) {
    google.waitForCredential().then(async (credential) => {
      error.value = ''
      loading.value = true
      try {
        const { data } = await api.post('/auth/accept-invite/', {
          token,
          google_credential: credential,
          first_name: form.first_name,
          last_name: form.last_name,
        })
        auth._setTokens(data)
        router.push(auth.homeRoute)
      } catch (e: any) {
        error.value = e.response?.data?.detail || 'Failed to accept invite with Google.'
      } finally {
        loading.value = false
      }
    }).catch((e) => {
      if (e.message !== 'Google sign-in timed out.') {
        error.value = e.message
      }
    })

    await google.renderGoogleButton(googleButtonRef.value)
  }
})

async function handleAccept() {
  error.value = ''

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
    const { data } = await api.post('/auth/accept-invite/', {
      token,
      first_name: form.first_name,
      last_name: form.last_name,
      password: form.password,
    })
    // Auto-login
    auth._setTokens(data)
    router.push(auth.homeRoute)
  } catch (e: any) {
    const data = e.response?.data
    if (data) {
      const msg = typeof data === 'string' ? data
        : data.detail || (Array.isArray(data) ? data.join(' ') : Object.values(data).flat().join(' '))
      error.value = msg || 'Failed to accept invite.'
    } else {
      error.value = 'Failed to accept invite. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>
