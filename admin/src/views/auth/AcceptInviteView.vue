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

      <!-- Cancelled / expired invite -->
      <div v-else-if="inviteCancelled" class="card p-8 text-center space-y-4">
        <div class="w-14 h-14 rounded-full bg-warning-50 flex items-center justify-center mx-auto">
          <ClockAlert :size="26" class="text-warning-500" />
        </div>
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-gray-900">Invitation Expired</h2>
          <p class="text-sm text-gray-500 leading-relaxed">
            The invite from <strong class="text-gray-700">{{ cancelledBy }}</strong> is no longer valid.
          </p>
        </div>
        <p class="text-sm text-gray-400">Contact them to request a new invitation.</p>
        <router-link to="/login" class="inline-block mt-1 text-sm font-medium text-navy hover:underline">Go to sign in</router-link>
      </div>

      <!-- Invalid invite -->
      <div v-else-if="inviteError" class="card p-8 text-center space-y-3">
        <AlertCircle :size="24" class="mx-auto text-danger-500" />
        <p class="text-sm text-danger-600">{{ inviteError }}</p>
        <router-link to="/login" class="text-sm text-navy hover:underline">Go to sign in</router-link>
      </div>

      <!-- Invite form -->
      <div v-else class="card p-8">
        <div class="mb-4 p-3 bg-info-50 border border-info-100 rounded-lg text-info-700 text-sm">
          You've been invited to join Klikk as <strong class="capitalize">{{ invite.role }}</strong>.
        </div>

        <form @submit.prevent="handleAccept" class="space-y-3" novalidate>

          <div>
            <label for="invite-email" class="label">Email</label>
            <input
              type="email"
              id="invite-email"
              :value="invite.email"
              readonly
              tabindex="-1"
              class="input bg-gray-50 text-gray-700 cursor-default"
              aria-readonly="true"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="invite-first-name" class="label">First name</label>
              <input id="invite-first-name" v-model="form.first_name" type="text" class="input" :class="{ 'input-error': fieldErrors.first_name }" placeholder="John" autocomplete="given-name" />
              <p v-if="fieldErrors.first_name" class="input-error-msg">{{ fieldErrors.first_name }}</p>
            </div>
            <div>
              <label for="invite-last-name" class="label">Last name</label>
              <input id="invite-last-name" v-model="form.last_name" type="text" class="input" :class="{ 'input-error': fieldErrors.last_name }" placeholder="Doe" autocomplete="family-name" />
              <p v-if="fieldErrors.last_name" class="input-error-msg">{{ fieldErrors.last_name }}</p>
            </div>
          </div>

          <div>
            <label for="invite-password" class="label">Password</label>
            <div class="relative">
              <input
                id="invite-password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-10"
                :class="{ 'input-error': fieldErrors.password }"
                placeholder="Min. 8 characters"
                autocomplete="new-password"
                data-clarity-mask="true"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
              >
                <Eye v-if="!showPassword" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
            <p v-if="fieldErrors.password" class="input-error-msg">{{ fieldErrors.password }}</p>
          </div>

          <div>
            <label for="invite-confirm-password" class="label">Confirm password</label>
            <input
              id="invite-confirm-password"
              v-model="confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              :class="{ 'input-error': fieldErrors.confirmPassword }"
              placeholder="Re-enter password"
              autocomplete="new-password"
            />
            <p v-if="fieldErrors.confirmPassword" class="input-error-msg">{{ fieldErrors.confirmPassword }}</p>
          </div>

          <div v-if="error" role="alert" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" class="flex-shrink-0" aria-hidden="true" />
            <span>{{ error }}</span>
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
          <div v-if="googleReady" class="flex items-center gap-3 my-4">
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
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useGoogleAuth } from '../../composables/useGoogleAuth'
import api from '../../api'
import { Eye, EyeOff, AlertCircle, Loader2, ClockAlert } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const google = useGoogleAuth()

const token = (route.query.token as string) || ''
const loadingInvite = ref(true)
const inviteError = ref('')
const inviteCancelled = ref(false)
const cancelledBy = ref('')
const invite = reactive({ email: '', role: '' })

const form = reactive({ first_name: '', last_name: '', password: '' })
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const fieldErrors = reactive({ first_name: '', last_name: '', password: '', confirmPassword: '' })
const googleButtonRef = ref<HTMLElement | null>(null)
const googleReady = ref(false)

function clearFieldErrors() {
  fieldErrors.first_name = ''
  fieldErrors.last_name = ''
  fieldErrors.password = ''
  fieldErrors.confirmPassword = ''
}

function validateForm(): boolean {
  clearFieldErrors()
  let valid = true

  if (!form.first_name.trim()) {
    fieldErrors.first_name = 'First name is required.'
    valid = false
  }
  if (!form.last_name.trim()) {
    fieldErrors.last_name = 'Last name is required.'
    valid = false
  }
  if (!form.password) {
    fieldErrors.password = 'Password is required.'
    valid = false
  } else if (form.password.length < 8) {
    fieldErrors.password = 'Password must be at least 8 characters.'
    valid = false
  }
  if (!confirmPassword.value) {
    fieldErrors.confirmPassword = 'Please confirm your password.'
    valid = false
  } else if (form.password !== confirmPassword.value) {
    fieldErrors.confirmPassword = 'Passwords do not match.'
    valid = false
  }

  return valid
}

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
    const responseData = e.response?.data
    if (e.response?.status === 410 || responseData?.detail === 'invite_cancelled') {
      inviteCancelled.value = true
      cancelledBy.value = responseData?.invited_by || 'Klikk'
    } else {
      inviteError.value = responseData?.detail || 'Invalid or expired invite.'
    }
  } finally {
    loadingInvite.value = false
  }

  // Wait for Vue to render the form (v-else block) before accessing the Google button ref
  await nextTick()

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
        if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error' || !e?.response) {
          error.value = 'Cannot connect to server. Please check your internet connection and try again.'
        } else {
          error.value = e.response?.data?.detail || 'Failed to accept invite with Google.'
        }
      } finally {
        loading.value = false
      }
    }).catch((e) => {
      if (e.message !== 'Google sign-in timed out.') {
        error.value = e.message
      }
    })

    try {
      await google.renderGoogleButton(googleButtonRef.value)
      googleReady.value = true
    } catch {
      // Google button failed to load — hide the "or" divider
      googleReady.value = false
    }
  }
})

async function handleAccept() {
  error.value = ''

  if (!validateForm()) return

  loading.value = true
  try {
    const { data } = await api.post('/auth/accept-invite/', {
      token,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      password: form.password,
    })
    // Auto-login
    auth._setTokens(data)
    router.push(auth.homeRoute)
  } catch (e: any) {
    if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error' || !e?.response) {
      error.value = 'Cannot connect to server. Please check your internet connection and try again.'
    } else {
      const data = e.response?.data
      if (data) {
        // Django password validation returns { detail: ["msg1", "msg2"] }
        const detail = data.detail
        if (Array.isArray(detail)) {
          error.value = detail.join(' ')
        } else if (typeof detail === 'string') {
          error.value = detail
        } else if (typeof data === 'string') {
          error.value = data
        } else {
          error.value = Object.values(data).flat().join(' ')
        }
      } else {
        error.value = 'Failed to accept invite. Please try again.'
      }
    }
  } finally {
    loading.value = false
  }
}
</script>
