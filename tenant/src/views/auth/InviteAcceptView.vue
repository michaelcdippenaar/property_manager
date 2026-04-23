<template>
  <div class="h-dvh flex flex-col bg-surface overflow-y-auto">
    <!-- Header -->
    <div class="bg-navy px-6 pt-16 pb-10 flex flex-col items-center" style="padding-top: calc(4rem + env(safe-area-inset-top))">
      <div class="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-4">
        <span class="text-white text-3xl font-bold">K</span>
      </div>
      <h1 class="text-white text-2xl font-bold">You're invited to Klikk</h1>
      <p class="text-white/60 text-sm mt-1">Create your tenant account</p>
    </div>

    <!-- Loading state -->
    <div v-if="state === 'loading'" class="flex-1 flex items-center justify-center">
      <Loader2 :size="28" class="text-navy animate-spin" />
    </div>

    <!-- Error: invalid / unknown token (404-style) -->
    <div v-else-if="state === 'invalid'" class="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
      <div class="w-16 h-16 rounded-full bg-danger-50 flex items-center justify-center">
        <XCircle :size="32" class="text-danger-600" />
      </div>
      <h2 class="text-lg font-semibold text-gray-900">Invalid invitation link</h2>
      <p class="text-sm text-gray-500 max-w-xs">
        This invitation link doesn't exist. Please check the link in your email or ask your agent to resend the invitation.
      </p>
    </div>

    <!-- Error: cancelled invite -->
    <div v-else-if="state === 'cancelled'" class="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
      <div class="w-16 h-16 rounded-full bg-warning-50 flex items-center justify-center">
        <AlertCircle :size="32" class="text-warning-600" />
      </div>
      <h2 class="text-lg font-semibold text-gray-900">Invitation cancelled</h2>
      <p class="text-sm text-gray-500 max-w-xs">
        This invitation was cancelled by {{ cancelledBy }}. Please contact your agent to request a new invitation.
      </p>
    </div>

    <!-- Error: already used -->
    <div v-else-if="state === 'used'" class="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
      <div class="w-16 h-16 rounded-full bg-navy/10 flex items-center justify-center">
        <CheckCircle :size="32" class="text-navy" />
      </div>
      <h2 class="text-lg font-semibold text-gray-900">Already accepted</h2>
      <p class="text-sm text-gray-500 max-w-xs">
        This invitation has already been used. Sign in to access your tenant portal.
      </p>
      <button
        class="mt-2 px-6 py-3 bg-navy text-white font-semibold rounded-2xl text-sm ripple touchable"
        @click="router.replace({ name: 'login' })"
      >
        Go to Sign In
      </button>
    </div>

    <!-- Success: invite accepted, now logged in -->
    <div v-else-if="state === 'success'" class="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
      <div class="w-16 h-16 rounded-full bg-success-50 flex items-center justify-center">
        <CheckCircle :size="32" class="text-success-600" />
      </div>
      <h2 class="text-lg font-semibold text-gray-900">Welcome to Klikk!</h2>
      <p class="text-sm text-gray-500">Setting up your account…</p>
      <Loader2 :size="20" class="text-navy animate-spin" />
    </div>

    <!-- Form: fill in name + password -->
    <template v-else-if="state === 'form'">
      <div class="flex-1 px-5 pt-8 pb-8">
        <!-- Email (read-only) -->
        <div class="list-section mb-4">
          <div class="list-row">
            <span class="text-sm text-gray-500 w-24 flex-shrink-0">Email</span>
            <span class="flex-1 text-sm text-gray-400 truncate">{{ invite.email }}</span>
          </div>
        </div>

        <!-- Name + password fields -->
        <div class="list-section">
          <div class="list-row">
            <span class="text-sm text-gray-500 w-24 flex-shrink-0">First name</span>
            <input
              v-model="firstName"
              type="text"
              placeholder="Jane"
              autocomplete="given-name"
              class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
              @keyup.enter="focusLastName"
            />
          </div>
          <div class="list-row">
            <span class="text-sm text-gray-500 w-24 flex-shrink-0">Last name</span>
            <input
              ref="lastNameRef"
              v-model="lastName"
              type="text"
              placeholder="Smith"
              autocomplete="family-name"
              class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
              @keyup.enter="focusPassword"
            />
          </div>
          <div class="list-row">
            <span class="text-sm text-gray-500 w-24 flex-shrink-0">Password</span>
            <input
              ref="passwordRef"
              v-model="password"
              type="password"
              placeholder="Min. 8 characters"
              autocomplete="new-password"
              class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
              @keyup.enter="focusConfirm"
            />
          </div>
          <div class="list-row">
            <span class="text-sm text-gray-500 w-24 flex-shrink-0">Confirm</span>
            <input
              ref="confirmRef"
              v-model="confirmPassword"
              type="password"
              placeholder="Repeat password"
              autocomplete="new-password"
              class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
              @keyup.enter="handleSubmit"
            />
          </div>
        </div>

        <!-- Error -->
        <p v-if="errorMsg" class="text-danger-600 text-sm text-center my-4 px-2">{{ errorMsg }}</p>

        <!-- Submit -->
        <button
          class="mt-6 w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base ripple touchable active:scale-[0.98]"
          :disabled="submitting"
          @click="handleSubmit"
        >
          <span v-if="!submitting">Create Account</span>
          <Loader2 v-else :size="20" class="animate-spin mx-auto" />
        </button>
      </div>

      <!-- Footer -->
      <div class="pb-10 text-center safe-bottom">
        <p class="text-xs text-gray-400">Klikk Tenant Portal &copy; {{ new Date().getFullYear() }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { Loader2, XCircle, AlertCircle, CheckCircle } from 'lucide-vue-next'
import api from '../../api'

type ViewState = 'loading' | 'form' | 'invalid' | 'cancelled' | 'used' | 'success'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const token = route.params.token as string

const state = ref<ViewState>('loading')
const invite = ref<{ email: string; role: string }>({ email: '', role: '' })
const cancelledBy = ref('your agent')

// Form fields
const firstName = ref('')
const lastName = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMsg = ref('')

// Refs for focus chaining
const lastNameRef = ref<HTMLInputElement | null>(null)
const passwordRef = ref<HTMLInputElement | null>(null)
const confirmRef = ref<HTMLInputElement | null>(null)

function focusLastName() { lastNameRef.value?.focus() }
function focusPassword() { passwordRef.value?.focus() }
function focusConfirm() { confirmRef.value?.focus() }

onMounted(async () => {
  if (!token) {
    state.value = 'invalid'
    return
  }

  try {
    const { data } = await api.get('/auth/accept-invite/', { params: { token } })
    invite.value = { email: data.email, role: data.role }
    state.value = 'form'
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? ''
    const status = e?.response?.status

    if (status === 410 && detail === 'invite_cancelled') {
      cancelledBy.value = e.response.data?.invited_by ?? 'your agent'
      state.value = 'cancelled'
    } else if (detail?.includes('already been used') || detail?.includes('already exists')) {
      state.value = 'used'
    } else {
      // 400 "Invalid invite link." or anything else → 404-style
      state.value = 'invalid'
    }
  }
})

async function handleSubmit() {
  errorMsg.value = ''

  if (!firstName.value.trim() || !lastName.value.trim()) {
    errorMsg.value = 'Please enter your first and last name.'
    return
  }
  if (!password.value) {
    errorMsg.value = 'Please enter a password.'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMsg.value = 'Passwords do not match.'
    return
  }
  if (password.value.length < 8) {
    errorMsg.value = 'Password must be at least 8 characters.'
    return
  }

  submitting.value = true
  try {
    const { data } = await api.post('/auth/accept-invite/', {
      token,
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      password: password.value,
    })

    // Log the user in immediately using the tokens from the response
    auth._setTokens(data)
    state.value = 'success'

    // Brief success display then navigate
    setTimeout(() => {
      if (data.two_fa_enroll_required && data.two_fa_token) {
        const query: Record<string, string> = { token: data.two_fa_token, required: '1' }
        if (data.two_fa_hard_blocked) query.blocked = '1'
        router.replace({ name: '2fa-enroll', query })
      } else {
        router.replace({ name: 'welcome' })
      }
    }, 1200)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (Array.isArray(detail)) {
      errorMsg.value = detail.join(' ')
    } else {
      errorMsg.value = detail || 'Something went wrong. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>
