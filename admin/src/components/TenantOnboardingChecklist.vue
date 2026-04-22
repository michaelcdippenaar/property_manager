<template>
  <div class="space-y-4">

    <!-- Progress bar -->
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-xs font-semibold uppercase tracking-wide text-navy">Onboarding progress</span>
        <span class="text-sm font-bold" :class="onboarding.progress === 100 ? 'text-success-600' : 'text-gray-700'">
          {{ onboarding.progress }}%
        </span>
      </div>
      <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-500"
          :class="onboarding.progress === 100 ? 'bg-success-500' : 'bg-navy'"
          :style="{ width: `${onboarding.progress}%` }"
        />
      </div>
      <p v-if="onboarding.progress === 100" class="text-xs text-success-600 mt-1 font-medium">
        All steps complete — lease is active.
      </p>
    </div>

    <!-- Checklist items -->
    <div class="space-y-2">

      <!-- Welcome pack -->
      <OnboardingItem
        label="Welcome pack sent"
        description="House rules, emergency contacts sheet, and unit information document."
        :done="onboarding.welcome_pack_sent"
        :done-at="onboarding.welcome_pack_sent_at"
        :loading="ticking === 'welcome_pack_sent'"
        cta-label="Mark as sent"
        @tick="tick('welcome_pack_sent')"
      />

      <!-- Deposit received -->
      <OnboardingItem
        label="Deposit received"
        :description="depositDescription"
        :done="onboarding.deposit_received"
        :done-at="onboarding.deposit_received_at"
        :loading="ticking === 'deposit_received'"
        cta-label="Mark deposit received"
        @tick="openDepositModal"
      />

      <!-- First rent scheduled -->
      <OnboardingItem
        label="First rent scheduled"
        description="Debit order or manual payment confirmed for first month's rent."
        :done="onboarding.first_rent_scheduled"
        :done-at="onboarding.first_rent_scheduled_at"
        :loading="ticking === 'first_rent_scheduled'"
        cta-label="Confirm first rent"
        @tick="tick('first_rent_scheduled')"
      />

      <!-- Keys handed over -->
      <OnboardingItem
        label="Keys / access handed over"
        description="Physical keys, remote, gate code, or PIN provided to tenant."
        :done="onboarding.keys_handed_over"
        :done-at="onboarding.keys_handed_over_at"
        :loading="ticking === 'keys_handed_over'"
        cta-label="Confirm handover"
        @tick="tick('keys_handed_over')"
      />

      <!-- Emergency contacts -->
      <OnboardingItem
        label="Emergency contacts captured"
        description="Next-of-kin / emergency contact saved on the tenant record."
        :done="onboarding.emergency_contacts_captured"
        :done-at="onboarding.emergency_contacts_captured_at"
        :loading="ticking === 'emergency_contacts_captured'"
        :cta-label="tenantProfilePath ? 'Update tenant' : 'Mark captured'"
        @tick="tenantProfilePath ? goToTenantProfile() : tick('emergency_contacts_captured')"
      />

      <!-- v2 deferred items -->
      <div class="border border-dashed border-gray-200 rounded-xl p-3 space-y-2 mt-2">
        <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">v2 — deferred items</p>

        <OnboardingItem
          label="Incoming inspection booked"
          description="Move-in condition inspection scheduled. (Deferred to v2)"
          :done="onboarding.incoming_inspection_booked"
          :done-at="onboarding.incoming_inspection_booked_at"
          :loading="ticking === 'incoming_inspection_booked'"
          cta-label="Mark booked"
          deferred
          @tick="tick('incoming_inspection_booked')"
        />

        <OnboardingItem
          label="Deposit banked (trust account)"
          description="Deposit transferred to trust account per RHA s5. (Deferred to v2)"
          :done="onboarding.deposit_banked_trust"
          :done-at="onboarding.deposit_banked_trust_at"
          :loading="ticking === 'deposit_banked_trust'"
          cta-label="Mark banked"
          deferred
          @tick="tick('deposit_banked_trust')"
        />
      </div>
    </div>

    <!-- Deposit modal -->
    <BaseModal :open="showDepositModal" title="Mark deposit received" @close="showDepositModal = false">
      <div class="space-y-4 p-1">
        <p class="text-sm text-gray-600">
          Expected deposit per lease: <span class="font-semibold">{{ formatCurrency(leaseDeposit) }}</span>
        </p>
        <div>
          <label class="label">Actual amount received (ZAR)</label>
          <input
            v-model.number="depositAmountInput"
            type="number"
            class="input"
            min="0"
            step="0.01"
            placeholder="e.g. 12000"
          />
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost btn-sm" @click="showDepositModal = false">Cancel</button>
          <button
            class="btn-primary btn-sm"
            :disabled="!depositAmountInput || depositAmountInput <= 0 || ticking === 'deposit_received'"
            @click="confirmDeposit"
          >
            <Loader2 v-if="ticking === 'deposit_received'" :size="14" class="animate-spin" />
            Confirm deposit
          </button>
        </div>
      </div>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'
import OnboardingItem from './OnboardingItem.vue'
import api from '../api'
import { useToast } from '../composables/useToast'
import { extractApiError } from '../utils/api-errors'

// ── Props ──────────────────────────────────────────────────────────────────────
interface OnboardingRecord {
  id: number
  lease_id: number
  lease_number: string
  tenant_name: string
  welcome_pack_sent: boolean
  welcome_pack_sent_at: string | null
  deposit_received: boolean
  deposit_received_at: string | null
  deposit_amount: string | null
  first_rent_scheduled: boolean
  first_rent_scheduled_at: string | null
  keys_handed_over: boolean
  keys_handed_over_at: string | null
  emergency_contacts_captured: boolean
  emergency_contacts_captured_at: string | null
  incoming_inspection_booked: boolean
  incoming_inspection_booked_at: string | null
  deposit_banked_trust: boolean
  deposit_banked_trust_at: string | null
  progress: number
  is_complete: boolean
  completed_at: string | null
  notes: string
}

const props = defineProps<{
  onboarding: OnboardingRecord
  leaseDeposit?: number | string | null
  /** Route path to the tenant detail page (for emergency contacts CTA) */
  tenantProfilePath?: string
}>()

const emit = defineEmits<{
  (e: 'updated', payload: OnboardingRecord): void
}>()

// ── Local state ────────────────────────────────────────────────────────────────
const toast = useToast()
const router = useRouter()
const ticking = ref<string | null>(null)
const showDepositModal = ref(false)
const depositAmountInput = ref<number | null>(null)

// ── Computed ───────────────────────────────────────────────────────────────────
const depositDescription = computed(() => {
  if (props.onboarding.deposit_amount) {
    return `Deposit of ${formatCurrency(props.onboarding.deposit_amount)} confirmed.`
  }
  return `Security deposit per lease: ${formatCurrency(props.leaseDeposit)}.`
})

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatCurrency(val: string | number | null | undefined): string {
  if (val == null || val === '') return '—'
  return `R ${Number(val).toLocaleString('en-ZA', { minimumFractionDigits: 0 })}`
}

function goToTenantProfile(): void {
  if (props.tenantProfilePath) router.push(props.tenantProfilePath)
}

function openDepositModal(): void {
  if (props.onboarding.deposit_received) return
  depositAmountInput.value = props.leaseDeposit ? Number(props.leaseDeposit) : null
  showDepositModal.value = true
}

// ── Mutations ──────────────────────────────────────────────────────────────────
async function tick(field: string): Promise<void> {
  if (ticking.value) return
  ticking.value = field
  try {
    const { data } = await api.patch(`/tenant/onboarding/${props.onboarding.id}/`, {
      [field]: true,
    })
    emit('updated', data)
    toast.success('Checklist updated')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to update checklist'))
  } finally {
    ticking.value = null
  }
}

async function confirmDeposit(): Promise<void> {
  if (!depositAmountInput.value || depositAmountInput.value <= 0) return
  ticking.value = 'deposit_received'
  try {
    const { data } = await api.patch(`/tenant/onboarding/${props.onboarding.id}/`, {
      deposit_received: true,
      deposit_amount: depositAmountInput.value,
    })
    showDepositModal.value = false
    emit('updated', data)
    toast.success(`Deposit of ${formatCurrency(depositAmountInput.value)} confirmed`)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to record deposit'))
  } finally {
    ticking.value = null
  }
}
</script>
