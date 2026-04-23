<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Create your account</p>
      </div>

      <div class="card p-8">

        <!-- ── Step 1: Account type ── -->
        <div v-if="step === 1" class="space-y-4">
          <p class="text-sm font-medium text-gray-700 text-center">How will you use Klikk?</p>

          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              class="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center"
              :class="form.account_type === 'agency'
                ? 'border-navy bg-navy/5 text-navy'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'"
              @click="form.account_type = 'agency'"
            >
              <Building2 :size="24" />
              <span class="text-sm font-semibold">Estate Agency</span>
              <span class="text-micro text-gray-400 leading-tight">I manage properties for clients</span>
            </button>

            <button
              type="button"
              class="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center"
              :class="form.account_type === 'individual'
                ? 'border-navy bg-navy/5 text-navy'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'"
              @click="form.account_type = 'individual'"
            >
              <Home :size="24" />
              <span class="text-sm font-semibold">Property Owner</span>
              <span class="text-micro text-gray-400 leading-tight">I manage my own rental properties</span>
            </button>
          </div>

          <button
            type="button"
            class="btn-primary w-full justify-center py-2.5"
            :disabled="!form.account_type"
            @click="step = 2"
          >
            Continue
          </button>
        </div>

        <!-- ── Step 2: Details ── -->
        <form v-else @submit.prevent="handleRegister" class="space-y-3">

          <!-- Back link -->
          <button
            type="button"
            class="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mb-1"
            @click="step = 1"
          >
            <ChevronLeft :size="14" />
            Back
          </button>

          <!-- Agency name (agency only) -->
          <div v-if="form.account_type === 'agency'">
            <label for="reg-agency-name" class="label">Agency name</label>
            <input id="reg-agency-name" v-model="form.agency_name" type="text" class="input" placeholder="e.g. Pam Golding Properties" required autocomplete="organization" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="reg-first-name" class="label">First name</label>
              <input id="reg-first-name" v-model="form.first_name" type="text" class="input" placeholder="John" required autocomplete="given-name" />
            </div>
            <div>
              <label for="reg-last-name" class="label">Last name</label>
              <input id="reg-last-name" v-model="form.last_name" type="text" class="input" placeholder="Doe" required autocomplete="family-name" />
            </div>
          </div>

          <div>
            <label for="reg-email" class="label">Email</label>
            <input id="reg-email" v-model="form.email" type="email" class="input" placeholder="you@klikk.co.za" required autocomplete="email" />
          </div>

          <div>
            <label for="reg-phone" class="label">Phone <span class="text-gray-400 font-normal">(optional)</span></label>
            <input id="reg-phone" v-model="form.phone" type="tel" class="input" placeholder="082 123 4567" autocomplete="tel" />
          </div>

          <div>
            <label for="reg-password" class="label">Password</label>
            <div class="relative">
              <input
                id="reg-password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="input pr-10"
                placeholder="••••••••"
                minlength="8"
                required
                autocomplete="new-password"
                data-clarity-mask="True"
              />
              <button
                type="button"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus-visible:outline-2 focus-visible:outline-navy focus-visible:outline-offset-1 rounded"
              >
                <Eye v-if="!showPassword" :size="16" aria-hidden="true" />
                <EyeOff v-else :size="16" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div>
            <label for="reg-confirm-password" class="label">Confirm password</label>
            <input
              id="reg-confirm-password"
              v-model="confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              class="input"
              placeholder="••••••••"
              required
              autocomplete="new-password"
            />
          </div>

          <!-- ToS acceptance -->
          <div class="flex items-start gap-2.5 pt-1">
            <input
              id="tos-accept"
              v-model="tosAccepted"
              type="checkbox"
              class="mt-0.5 h-4 w-4 rounded border-gray-300 text-navy accent-navy cursor-pointer flex-shrink-0"
              required
            />
            <label for="tos-accept" class="text-xs text-gray-500 leading-relaxed cursor-pointer">
              I have read and agree to Klikk's
              <a href="https://klikk.co.za/legal/terms" target="_blank" class="text-navy underline hover:text-pink-brand">Terms of Service</a>
              and
              <a href="https://klikk.co.za/legal/privacy" target="_blank" class="text-navy underline hover:text-pink-brand">Privacy Policy</a>.
            </label>
          </div>

          <div v-if="error" role="alert" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" aria-hidden="true" />
            {{ error }}
          </div>

          <button
            type="submit"
            class="btn-primary w-full justify-center py-2.5 mt-2"
            :disabled="loading || !tosAccepted"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Creating account...' : 'Create account' }}
          </button>

        </form>

        <!-- Google Sign Up (rendered natively by GSI to avoid popup blockers) -->
        <template v-if="step === 2 && google.isConfigured">
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
import { Eye, EyeOff, AlertCircle, Loader2, Building2, Home, ChevronLeft } from 'lucide-vue-next'
import api from '../../api'

const router = useRouter()
const auth = useAuthStore()
const google = useGoogleAuth()

const step = ref(1)

const form = reactive({
  account_type: '' as 'agency' | 'individual' | '',
  agency_name: '',
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  password: '',
})
const confirmPassword = ref('')
const showPassword = ref(false)
const tosAccepted = ref(false)
const loading = ref(false)
const error = ref('')
const googleButtonRef = ref<HTMLElement | null>(null)

// Current legal document IDs — fetched once on mount so we can pass them
// to the register endpoint for server-side POPIA s11 consent recording.
const tosDocumentId = ref<number | null>(null)
const privacyDocumentId = ref<number | null>(null)

onMounted(async () => {
  // Pre-fetch current legal document IDs for POPIA s11 consent recording.
  // Failure is non-blocking — registration will still work; consent just won't
  // include document IDs (backend handles missing IDs gracefully).
  try {
    const { data } = await api.get('/legal/documents/current/')
    for (const doc of data) {
      if (doc.doc_type === 'tos') tosDocumentId.value = doc.id
      if (doc.doc_type === 'privacy') privacyDocumentId.value = doc.id
    }
  } catch {
    // Non-fatal — proceed without IDs
  }

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
    await auth.register({
      email: form.email,
      password: form.password,
      first_name: form.first_name,
      last_name: form.last_name,
      phone: form.phone || undefined,
      account_type: form.account_type || 'individual',
      agency_name: form.account_type === 'agency' ? form.agency_name : undefined,
      // POPIA s11 — pass current document IDs so the backend can persist
      // UserConsent rows server-side with the correct IP + user-agent.
      tos_document_id: tosDocumentId.value,
      privacy_document_id: privacyDocumentId.value,
    })
    // After registration + auto-login, redirect to dashboard
    router.push(auth.homeRoute)
  } catch (e: any) {
    const data = e.response?.data
    if (data) {
      const msg = typeof data === 'string' ? data
        : data.detail || data.email?.[0] || data.password?.[0] || data.agency_name?.[0] || Object.values(data).flat().join(' ')
      error.value = msg || 'Registration failed.'
    } else {
      error.value = 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>
