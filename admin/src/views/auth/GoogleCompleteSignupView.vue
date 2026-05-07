<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Finish your Klikk signup</p>
      </div>

      <div class="card p-8">
        <div v-if="!hasCredential" class="text-sm text-gray-600 text-center space-y-3">
          <p>We couldn't find your Google sign-in details — please try again.</p>
          <router-link to="/login" class="text-navy underline">Back to login</router-link>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="space-y-4">
          <div class="text-sm text-gray-600">
            We don't have a Klikk account for <strong class="text-navy">{{ email }}</strong> yet.
            How will you use Klikk?
          </div>

          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              class="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center"
              :class="accountType === 'agency'
                ? 'border-navy bg-navy/5 text-navy'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'"
              @click="accountType = 'agency'"
            >
              <Building2 :size="22" />
              <span class="text-sm font-semibold">Estate Agency</span>
              <span class="text-micro text-gray-400 leading-tight">I manage properties for clients</span>
            </button>

            <button
              type="button"
              class="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center"
              :class="accountType === 'individual'
                ? 'border-navy bg-navy/5 text-navy'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'"
              @click="accountType = 'individual'"
            >
              <Home :size="22" />
              <span class="text-sm font-semibold">Property Owner</span>
              <span class="text-micro text-gray-400 leading-tight">I manage my own rentals</span>
            </button>
          </div>

          <div v-if="accountType === 'agency'">
            <label class="label">Agency name</label>
            <input v-model="agencyName" type="text" class="input" placeholder="e.g. Pam Golding Properties" required />
          </div>

          <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <button
            type="submit"
            class="btn-primary w-full justify-center py-2.5"
            :disabled="loading || !canSubmit"
          >
            <Loader2 v-if="loading" :size="15" class="animate-spin" />
            {{ loading ? 'Creating account...' : 'Continue' }}
          </button>

          <p class="text-center text-xs text-gray-400">
            <router-link to="/login" class="hover:text-navy">Use a different email</router-link>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import { AlertCircle, Building2, Home, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

const accountType = ref<'agency' | 'individual'>('agency')
const agencyName = ref('')
const loading = ref(false)
const error = ref('')

const credential = ref('')
const email = ref('')

const hasCredential = computed(() => credential.value.length > 0)
const canSubmit = computed(() => {
  if (accountType.value === 'agency') return agencyName.value.trim().length > 0
  return true
})

onMounted(() => {
  credential.value = sessionStorage.getItem('google_pending_credential') || ''
  email.value = sessionStorage.getItem('google_pending_email') || ''
})

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/google/complete-signup/', {
      google_credential: credential.value,
      account_type: accountType.value,
      agency_name: accountType.value === 'agency' ? agencyName.value.trim() : '',
    })
    if (data.access && data.refresh) {
      auth._setTokens(data)
      sessionStorage.removeItem('google_pending_credential')
      sessionStorage.removeItem('google_pending_email')
      // Router guard will route to /onboarding because the new agency
      // has onboarding_completed_at = null.
      await auth.fetchMe()
      router.push('/')
    } else {
      error.value = 'Unexpected response from server.'
    }
  } catch (e: any) {
    error.value = e?.response?.data?.error || e?.message || 'Could not complete signup.'
  } finally {
    loading.value = false
  }
}
</script>
