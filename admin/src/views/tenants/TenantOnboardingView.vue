<template>
  <div class="space-y-6">

    <!-- Loading -->
    <div v-if="loading" class="space-y-3 animate-pulse">
      <div class="h-8 bg-gray-100 rounded-xl w-1/3" />
      <div class="h-48 bg-gray-100 rounded-xl" />
    </div>

    <!-- No active lease / no onboarding record -->
    <div v-else-if="!onboarding" class="card p-10 text-center">
      <div class="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
        <ClipboardList :size="24" class="text-gray-400" />
      </div>
      <p class="text-sm font-medium text-gray-600">No onboarding record yet</p>
      <p class="text-xs text-gray-400 mt-1">
        An onboarding checklist is created automatically when a lease becomes active.
      </p>
      <button
        v-if="latestLeaseId"
        class="btn-primary btn-sm mt-4 mx-auto"
        :disabled="creating"
        @click="createOnboarding"
      >
        <Loader2 v-if="creating" :size="14" class="animate-spin" />
        Create checklist for latest lease
      </button>
    </div>

    <!-- Checklist card -->
    <div v-else class="card p-5 space-y-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-0.5 flex items-center gap-1.5">
            <ClipboardList :size="13" /> Onboarding checklist
          </div>
          <p class="text-xs text-gray-400">
            Lease
            <RouterLink
              v-if="onboarding.lease_id"
              :to="{ name: 'leases' }"
              class="text-navy hover:underline font-medium"
            >
              {{ onboarding.lease_number }}
            </RouterLink>
            &middot; {{ onboarding.tenant_name }}
          </p>
        </div>
        <span
          class="flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full"
          :class="onboarding.is_complete ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-500'"
        >
          {{ onboarding.is_complete ? 'Complete' : `${onboarding.progress}% done` }}
        </span>
      </div>

      <TenantOnboardingChecklist
        :onboarding="onboarding"
        :lease-deposit="leaseDeposit"
        :tenant-profile-path="tenantProfilePath"
        @updated="onboarding = $event"
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { ClipboardList, Loader2 } from 'lucide-vue-next'
import TenantOnboardingChecklist from '../../components/TenantOnboardingChecklist.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'

// ── Props ──────────────────────────────────────────────────────────────────────
const props = defineProps<{
  /** Person ID of the tenant */
  personId: number
  /** Latest lease ID (used to create onboarding if missing) */
  latestLeaseId?: number | null
  leaseDeposit?: number | string | null
  tenantProfilePath?: string
}>()

// ── State ──────────────────────────────────────────────────────────────────────
const toast = useToast()
const loading = ref(true)
const creating = ref(false)
const onboarding = ref<any | null>(null)

// ── Load ───────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadOnboarding()
})

async function loadOnboarding(): Promise<void> {
  loading.value = true
  try {
    if (!props.latestLeaseId) {
      onboarding.value = null
      return
    }
    const { data } = await api.get('/tenant/onboarding/', {
      params: { lease: props.latestLeaseId },
    })
    const list = data.results ?? data
    onboarding.value = list.length > 0 ? list[0] : null
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load onboarding'))
  } finally {
    loading.value = false
  }
}

// ── Create onboarding manually ─────────────────────────────────────────────────
async function createOnboarding(): Promise<void> {
  if (!props.latestLeaseId) return
  creating.value = true
  try {
    const { data } = await api.post('/tenant/onboarding/', {
      lease_id: props.latestLeaseId,
    })
    onboarding.value = data
    toast.success('Onboarding checklist created')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to create onboarding'))
  } finally {
    creating.value = false
  }
}
</script>
