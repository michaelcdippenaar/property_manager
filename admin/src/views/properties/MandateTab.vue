<template>
  <div class="space-y-5">

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-6">
      <Loader2 :size="15" class="animate-spin" />
      Loading mandate…
    </div>

    <!-- ── Empty state ── -->
    <template v-else-if="!activeMandate">
      <div class="flex flex-col items-center justify-center py-16 text-center">
        <div class="w-14 h-14 rounded-2xl bg-navy/8 flex items-center justify-center mb-4">
          <FileSignature :size="28" class="text-navy/40" />
        </div>
        <h3 class="text-base font-semibold text-gray-800 mb-1">No mandate on file</h3>
        <p class="text-sm text-gray-400 max-w-sm mb-6">
          A signed rental mandate is required before you can list or manage this property.
          It formalises the agency relationship and commission terms with the owner.
        </p>
        <button class="btn-primary flex items-center gap-2" @click="showCreateModal = true">
          <Plus :size="15" />
          Create Mandate
        </button>
      </div>
    </template>

    <!-- ── Active mandate ── -->
    <template v-else>

      <!-- Mandate card -->
      <div class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <!-- Card header -->
        <div class="flex items-start justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <FileSignature :size="16" class="text-navy" />
              <span class="text-sm font-semibold text-gray-900">{{ mandateTypeLabel(activeMandate.mandate_type) }}</span>
              <span class="text-[11px] px-2 py-0.5 rounded-full font-medium" :class="exclusivityBadge(activeMandate.exclusivity)">
                {{ activeMandate.exclusivity === 'sole' ? 'Sole' : 'Open' }}
              </span>
            </div>
            <p class="text-xs text-gray-400">
              Commenced {{ fmtDate(activeMandate.start_date) }}
              <span v-if="activeMandate.end_date"> · expires {{ fmtDate(activeMandate.end_date) }}</span>
            </p>
          </div>

          <!-- Status badge -->
          <span class="text-[11px] font-semibold px-2.5 py-1 rounded-full" :class="statusBadgeClass(activeMandate.status)">
            {{ statusLabel(activeMandate.status) }}
          </span>
        </div>

        <!-- Card body -->
        <div class="px-5 py-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <p class="text-[11px] text-gray-400 mb-0.5">Commission</p>
            <p class="text-gray-800 font-medium">{{ commissionDisplay(activeMandate) }}</p>
          </div>
          <div>
            <p class="text-[11px] text-gray-400 mb-0.5">Notice period</p>
            <p class="text-gray-800">{{ activeMandate.notice_period_days }} days</p>
          </div>
          <div v-if="activeMandate.mandate_type === 'full_management'">
            <p class="text-[11px] text-gray-400 mb-0.5">Maintenance threshold</p>
            <p class="text-gray-800">R {{ Number(activeMandate.maintenance_threshold).toLocaleString('en-ZA', { minimumFractionDigits: 0 }) }}</p>
          </div>
          <div>
            <p class="text-[11px] text-gray-400 mb-0.5">Owner</p>
            <p class="text-gray-800">{{ activeMandate.owner_name || '—' }}</p>
            <p class="text-xs text-gray-400">{{ activeMandate.owner_email || '—' }}</p>
          </div>
        </div>

        <!-- Card actions -->
        <div class="px-5 py-3 border-t border-gray-100 flex items-center gap-3">
          <!-- Send for signing -->
          <button
            v-if="activeMandate.status === 'draft'"
            class="btn-primary text-xs flex items-center gap-1.5"
            :disabled="!activeMandate.owner_email || sending"
            :title="!activeMandate.owner_email ? 'Owner email is required — update the landlord record first' : ''"
            @click="sendForSigning"
          >
            <Loader2 v-if="sending" :size="12" class="animate-spin" />
            <Send v-else :size="12" />
            Send for Signing
          </button>

          <!-- Edit (draft only) -->
          <button
            v-if="activeMandate.status === 'draft'"
            class="btn-ghost text-xs flex items-center gap-1.5"
            @click="openEditModal"
          >
            <Pencil :size="12" />
            Edit
          </button>

          <!-- New mandate (if active/expired/cancelled) -->
          <button
            v-if="['active', 'expired', 'cancelled'].includes(activeMandate.status)"
            class="btn-ghost text-xs flex items-center gap-1.5"
            @click="showCreateModal = true"
          >
            <Plus :size="12" />
            New Mandate
          </button>
        </div>
      </div>

      <!-- Signing panel (shown once sent) -->
      <div v-if="activeMandate.submission_id" class="rounded-2xl border border-gray-200 bg-white px-5 py-4">
        <h4 class="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <PenTool :size="14" class="text-navy" />
          Signing Status
        </h4>
        <MandateSigningPanel
          :submission-id="activeMandate.submission_id"
          @signed="handleSigned"
        />
      </div>

    </template>

    <!-- ────────────────────────────────── -->
    <!-- Create / Edit modal               -->
    <!-- ────────────────────────────────── -->
    <BaseModal
      :open="showCreateModal"
      :title="editingMandate ? 'Edit Mandate' : 'Create Rental Mandate'"
      size="lg"
      @close="closeModal"
    >
      <form class="space-y-5" @submit.prevent="saveMandate">

        <!-- Mandate type -->
        <div>
          <label class="label mb-2">Mandate type</label>
          <div class="space-y-2">
            <label
              v-for="opt in MANDATE_TYPES"
              :key="opt.value"
              class="flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors"
              :class="form.mandate_type === opt.value ? 'border-navy bg-navy/5' : 'border-gray-200 hover:border-gray-300'"
            >
              <input
                type="radio"
                :value="opt.value"
                v-model="form.mandate_type"
                class="mt-0.5 accent-navy"
                @change="onMandateTypeChange"
              />
              <div>
                <span class="text-sm font-medium text-gray-800">{{ opt.label }}</span>
                <p class="text-xs text-gray-400 mt-0.5">{{ opt.description }}</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Exclusivity + Commission -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Exclusivity</label>
            <select v-model="form.exclusivity" class="input">
              <option value="sole">Sole Mandate</option>
              <option value="open">Open Mandate</option>
            </select>
          </div>
          <div>
            <label class="label">Commission {{ form.commission_period === 'once_off' ? "(months' rent)" : '(%)' }}</label>
            <input v-model.number="form.commission_rate" type="number" step="0.01" min="0" class="input" />
          </div>
        </div>

        <!-- Dates -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Start date <span class="text-red-400">*</span></label>
            <input v-model="form.start_date" type="date" class="input" required />
          </div>
          <div>
            <label class="label">End date <span class="text-gray-300">(optional)</span></label>
            <input v-model="form.end_date" type="date" class="input" />
          </div>
        </div>

        <!-- Notice period + Maintenance threshold -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Notice period (days)</label>
            <input v-model.number="form.notice_period_days" type="number" min="0" class="input" />
          </div>
          <div v-if="form.mandate_type === 'full_management'">
            <label class="label">Maintenance threshold (R)</label>
            <input v-model.number="form.maintenance_threshold" type="number" step="0.01" min="0" class="input" />
          </div>
        </div>

        <!-- Owner info (read-only confirmation) -->
        <div v-if="ownerInfo.name || ownerInfo.email" class="rounded-xl bg-gray-50 px-4 py-3">
          <p class="text-[11px] text-gray-400 mb-1">Owner contact (from landlord record)</p>
          <p class="text-sm font-medium text-gray-800">{{ ownerInfo.name }}</p>
          <p class="text-xs text-gray-500">{{ ownerInfo.email || '⚠️ No email — add it to the landlord record before sending' }}</p>
        </div>

        <!-- Notes -->
        <div>
          <label class="label">Notes <span class="text-gray-300">(internal)</span></label>
          <textarea v-model="form.notes" rows="2" class="input" />
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3 pt-1">
          <button type="button" class="btn-ghost" @click="closeModal">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="saving">
            <Loader2 v-if="saving" :size="14" class="animate-spin mr-1" />
            {{ editingMandate ? 'Save Changes' : 'Create Mandate' }}
          </button>
        </div>

      </form>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  FileSignature, Loader2, Plus, Send, Pencil, PenTool,
} from 'lucide-vue-next'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import BaseModal from '../../components/BaseModal.vue'
import MandateSigningPanel from './MandateSigningPanel.vue'
import { useMandatesStore } from '../../stores/mandates'

const props = defineProps<{ propertyId: number }>()
const { showToast } = useToast()
const mandatesStore = useMandatesStore()

// ── State ────────────────────────────────── //
const loading         = ref(false)
const saving          = ref(false)
const sending         = ref(false)
const showCreateModal = ref(false)
const mandates        = ref<any[]>([])
const editingMandate  = ref<any>(null)

const MANDATE_TYPES = [
  { value: 'full_management', label: 'Full Management', description: '10% monthly commission — agent handles all letting, rent, maintenance & admin', defaultRate: 10, period: 'monthly' },
  { value: 'letting_only',    label: 'Letting Only',    description: '1 month placement fee — agent finds tenant only, owner manages thereafter', defaultRate: 1, period: 'once_off' },
  { value: 'rent_collection', label: 'Rent Collection Only', description: '5% monthly commission — agent collects rent & disburses to owner', defaultRate: 5, period: 'monthly' },
  { value: 'finders_fee',     label: 'Finders Fee',     description: 'Once-off fee — agent sources tenant only', defaultRate: 1, period: 'once_off' },
]

const defaultForm = () => ({
  mandate_type:          'full_management',
  exclusivity:           'sole',
  commission_rate:       10,
  commission_period:     'monthly',
  start_date:            new Date().toISOString().slice(0, 10),
  end_date:              '',
  notice_period_days:    60,
  maintenance_threshold: 2000,
  notes:                 '',
})

const form = ref(defaultForm())

// ── Computed ─────────────────────────────── //
const activeMandate = computed(() =>
  mandates.value.find(m => !['cancelled'].includes(m.status)) ?? mandates.value[0] ?? null
)

const ownerInfo = computed(() => ({
  name:  activeMandate.value?.owner_name  ?? '',
  email: activeMandate.value?.owner_email ?? '',
}))

// ── Data loading ─────────────────────────── //
async function load() {
  loading.value = true
  try {
    mandates.value = await mandatesStore.fetchByProperty(props.propertyId, { force: true })
  } catch (err) {
    showToast(extractApiError(err, 'Failed to load mandate'), 'error')
  } finally {
    loading.value = false
  }
}

// ── Modal helpers ────────────────────────── //
function openEditModal() {
  if (!activeMandate.value) return
  editingMandate.value = activeMandate.value
  form.value = {
    mandate_type:          activeMandate.value.mandate_type,
    exclusivity:           activeMandate.value.exclusivity,
    commission_rate:       Number(activeMandate.value.commission_rate),
    commission_period:     activeMandate.value.commission_period,
    start_date:            activeMandate.value.start_date ?? '',
    end_date:              activeMandate.value.end_date ?? '',
    notice_period_days:    activeMandate.value.notice_period_days,
    maintenance_threshold: Number(activeMandate.value.maintenance_threshold),
    notes:                 activeMandate.value.notes ?? '',
  }
  showCreateModal.value = true
}

function closeModal() {
  showCreateModal.value = false
  editingMandate.value  = null
  form.value = defaultForm()
}

function onMandateTypeChange() {
  const opt = MANDATE_TYPES.find(t => t.value === form.value.mandate_type)
  if (opt) {
    form.value.commission_rate   = opt.defaultRate
    form.value.commission_period = opt.period
  }
}

// ── Save mandate ─────────────────────────── //
async function saveMandate() {
  saving.value = true
  try {
    const payload: any = {
      property:              props.propertyId,
      mandate_type:          form.value.mandate_type,
      exclusivity:           form.value.exclusivity,
      commission_rate:       form.value.commission_rate,
      commission_period:     form.value.commission_period,
      start_date:            form.value.start_date,
      end_date:              form.value.end_date || null,
      notice_period_days:    form.value.notice_period_days,
      maintenance_threshold: form.value.maintenance_threshold,
      notes:                 form.value.notes,
    }

    if (editingMandate.value) {
      await mandatesStore.update(editingMandate.value.id, props.propertyId, payload)
      showToast('Mandate updated', 'success')
    } else {
      await mandatesStore.create(payload)
      showToast('Mandate created', 'success')
    }

    closeModal()
    await load()
  } catch (err) {
    showToast(extractApiError(err, 'Failed to save mandate'), 'error')
  } finally {
    saving.value = false
  }
}

// ── Send for signing ─────────────────────── //
async function sendForSigning() {
  if (!activeMandate.value) return
  sending.value = true
  try {
    await mandatesStore.sendForSigning(activeMandate.value.id, props.propertyId)
    showToast('Mandate sent for signing — owner will receive an email shortly', 'success')
    await load()
  } catch (err) {
    showToast(extractApiError(err, 'Failed to send mandate'), 'error')
  } finally {
    sending.value = false
  }
}

// ── After signing completes ── //
async function handleSigned() {
  await load()
}

// ── Display helpers ─────────────────────── //
function mandateTypeLabel(type: string) {
  return MANDATE_TYPES.find(t => t.value === type)?.label ?? type
}

function commissionDisplay(m: any) {
  const rate = Number(m.commission_rate)
  if (m.commission_period === 'once_off') {
    return `${rate} month${rate !== 1 ? 's' : ''} rent (once-off)`
  }
  return `${rate}% per month`
}

function fmtDate(d: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

function statusLabel(s: string) {
  const labels: Record<string, string> = {
    draft: 'Draft',
    sent: 'Sent for Signing',
    partially_signed: 'Partially Signed',
    active: 'Active',
    expired: 'Expired',
    cancelled: 'Cancelled',
  }
  return labels[s] ?? s
}

function statusBadgeClass(s: string) {
  const map: Record<string, string> = {
    draft:            'bg-gray-100 text-gray-500',
    sent:             'bg-blue-50 text-blue-700',
    partially_signed: 'bg-amber-50 text-amber-700',
    active:           'bg-green-50 text-green-700',
    expired:          'bg-red-50 text-red-600',
    cancelled:        'bg-red-50 text-red-600',
  }
  return map[s] ?? 'bg-gray-100 text-gray-500'
}

function exclusivityBadge(ex: string) {
  return ex === 'sole'
    ? 'bg-navy/8 text-navy'
    : 'bg-gray-100 text-gray-500'
}

onMounted(load)
</script>
