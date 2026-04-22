<template>
  <div class="flex flex-col h-full bg-surface overflow-hidden" name="WelcomeView">
    <div class="scroll-page px-5 pt-8 pb-safe-bottom space-y-6">

      <!-- Hero -->
      <div class="text-center space-y-2 pt-4">
        <div class="w-16 h-16 rounded-2xl bg-navy/10 flex items-center justify-center mx-auto">
          <Home :size="28" class="text-navy" />
        </div>
        <h1 class="text-2xl font-bold text-gray-900">Welcome to your new home!</h1>
        <p class="text-sm text-gray-500 max-w-xs mx-auto">
          {{ auth.user?.full_name?.split(' ')[0] ?? 'Hi there' }}, your lease has been signed.
          Your agent is working through the checklist below to get you fully onboarded.
        </p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="space-y-3 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-14 bg-white rounded-2xl" />
      </div>

      <!-- Checklist -->
      <div v-else-if="onboarding" class="space-y-3">

        <!-- Progress -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-semibold uppercase tracking-wide text-gray-500">Setup progress</span>
            <span class="text-sm font-bold" :class="onboarding.progress === 100 ? 'text-success-600' : 'text-gray-700'">
              {{ onboarding.progress }}%
            </span>
          </div>
          <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="onboarding.progress === 100 ? 'bg-success-500' : 'bg-navy'"
              :style="{ width: `${onboarding.progress}%` }"
            />
          </div>
        </div>

        <!-- Items -->
        <div class="list-section">
          <TenantOnboardingItem
            icon="mail"
            label="Welcome pack"
            :done="onboarding.welcome_pack_sent"
            description="House rules and unit information sent to you."
          />
          <TenantOnboardingItem
            icon="banknote"
            label="Deposit received"
            :done="onboarding.deposit_received"
            :description="onboarding.deposit_received
              ? `R ${formatAmount(onboarding.deposit_amount)} confirmed.`
              : 'Your security deposit is being processed.'"
          />
          <TenantOnboardingItem
            icon="calendar"
            label="First rent scheduled"
            :done="onboarding.first_rent_scheduled"
            description="First month's rent payment confirmed."
          />
          <TenantOnboardingItem
            icon="key"
            label="Keys handed over"
            :done="onboarding.keys_handed_over"
            description="Physical keys and access codes provided."
          />
          <TenantOnboardingItem
            icon="phone"
            label="Emergency contacts"
            :done="onboarding.emergency_contacts_captured"
            description="Your emergency contact details on file."
          />
        </div>

        <!-- All done CTA -->
        <div
          v-if="onboarding.is_complete"
          class="list-section bg-success-50 border border-success-100 rounded-2xl p-4 text-center"
        >
          <CheckCircle2 :size="28" class="text-success-500 mx-auto mb-2" />
          <p class="text-sm font-bold text-success-700">You're all set!</p>
          <p class="text-xs text-success-600 mt-0.5">All onboarding steps are complete.</p>
          <button class="btn-primary btn-sm mt-3 mx-auto" @click="goHome">
            Go to dashboard
          </button>
        </div>

        <!-- Not done yet nudge -->
        <div v-else class="text-center py-2">
          <p class="text-xs text-gray-400">
            Your agent is completing these steps. You'll see updates here as they're ticked off.
          </p>
          <button class="mt-3 text-sm font-medium text-navy hover:underline" @click="goHome">
            Continue to dashboard
          </button>
        </div>

      </div>

      <!-- No onboarding yet -->
      <div v-else class="text-center py-8">
        <p class="text-sm text-gray-500">Your agent will begin the onboarding process shortly.</p>
        <button class="mt-4 text-sm font-medium text-navy hover:underline" @click="goHome">
          Go to dashboard
        </button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Home, CheckCircle2 } from 'lucide-vue-next'
import TenantOnboardingItem from '../../components/TenantOnboardingItem.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const onboarding = ref<any | null>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/tenant/onboarding/')
    const list = data.results ?? data
    onboarding.value = list.length > 0 ? list[0] : null
  } catch {
    // Silent — tenant may not have onboarding yet
  } finally {
    loading.value = false
  }
})

async function goHome(): Promise<void> {
  // Stamp seen_welcome_at server-side so the flag survives new tabs and restarts.
  // Fire-and-forget: navigate immediately; the store update propagates on response.
  api.post('/auth/welcome/').then(({ data }) => {
    auth.user = { ...auth.user!, ...data }
  }).catch(() => {
    // Non-fatal — worst case the user sees the screen once more next login.
  })
  router.replace({ name: 'home' })
}

function formatAmount(val: string | number | null): string {
  if (!val) return '0'
  return Number(val).toLocaleString('en-ZA', { minimumFractionDigits: 0 })
}
</script>
