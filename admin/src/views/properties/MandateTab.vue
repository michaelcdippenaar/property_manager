<template>
  <div class="space-y-5">

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-6">
      <Loader2 :size="15" class="animate-spin" />
      Loading mandate…
    </div>

    <!-- ── Empty state ── -->
    <EmptyState
      v-else-if="!activeMandate"
      title="No mandate on file"
      description="A signed rental mandate is required before you can list or manage this property. It formalises the agency relationship and commission terms with the owner."
      :icon="FileSignature"
    >
      <div class="flex items-center gap-2">
        <button class="btn-primary" @click="showCreateModal = true">
          <Plus :size="15" /> Create Mandate
        </button>
        <button class="btn-ghost" :disabled="parsing" @click="triggerUpload">
          <Loader2 v-if="parsing" :size="15" class="animate-spin" />
          <Upload v-else :size="15" />
          {{ parsing ? 'Reading mandate…' : 'Upload existing mandate' }}
        </button>
        <input
          ref="uploadInput"
          type="file"
          accept="application/pdf"
          class="hidden"
          @change="onUploadSelected"
        />
      </div>
    </EmptyState>

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
              <span class="text-micro px-2 py-0.5 rounded-full font-medium" :class="exclusivityBadge(activeMandate.exclusivity)">
                {{ activeMandate.exclusivity === 'sole' ? 'Sole' : 'Open' }}
              </span>
            </div>
            <p class="text-xs text-gray-400">
              Commenced {{ fmtDate(activeMandate.start_date) }}
              <span v-if="activeMandate.end_date"> · expires {{ fmtDate(activeMandate.end_date) }}</span>
            </p>
          </div>

          <!-- Status badge -->
          <span class="text-micro font-semibold px-2.5 py-1 rounded-full" :class="statusBadgeClass(activeMandate.status)">
            {{ statusLabel(activeMandate.status) }}
          </span>
        </div>

        <!-- Card body -->
        <div class="px-5 py-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <p class="text-micro text-gray-400 mb-0.5">Commission</p>
            <p class="text-gray-800 font-medium">{{ commissionDisplay(activeMandate) }}</p>
          </div>
          <div>
            <p class="text-micro text-gray-400 mb-0.5">Notice period</p>
            <p class="text-gray-800">{{ activeMandate.notice_period_days }} days</p>
          </div>
          <div v-if="activeMandate.mandate_type === 'full_management'">
            <p class="text-micro text-gray-400 mb-0.5">Maintenance threshold</p>
            <p class="text-gray-800">R {{ Number(activeMandate.maintenance_threshold).toLocaleString('en-ZA', { minimumFractionDigits: 0 }) }}</p>
          </div>
          <div>
            <p class="text-micro text-gray-400 mb-0.5">Owner</p>
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

          <!-- Terminate (active only) -->
          <button
            v-if="activeMandate.status === 'active'"
            class="btn-ghost text-xs flex items-center gap-1.5 text-danger-600 hover:bg-danger-50"
            :disabled="terminating"
            @click="openTerminateModal"
          >
            <Loader2 v-if="terminating" :size="12" class="animate-spin" />
            <XCircle v-else :size="12" />
            Terminate
          </button>

          <!-- Renew (active / expired / terminated) -->
          <button
            v-if="['active', 'expired', 'terminated'].includes(activeMandate.status)"
            class="btn-ghost text-xs flex items-center gap-1.5"
            :disabled="renewing"
            @click="renewMandate"
          >
            <Loader2 v-if="renewing" :size="12" class="animate-spin" />
            <RefreshCw v-else :size="12" />
            Renew
          </button>

          <!-- New mandate (if active/expired/cancelled/terminated) -->
          <button
            v-if="['active', 'expired', 'cancelled', 'terminated'].includes(activeMandate.status)"
            class="btn-ghost text-xs flex items-center gap-1.5"
            @click="showCreateModal = true"
          >
            <Plus :size="12" />
            New Mandate
          </button>

          <!-- Upload existing mandate (always available) -->
          <button
            class="btn-ghost text-xs flex items-center gap-1.5"
            :disabled="parsing"
            @click="triggerUpload"
          >
            <Loader2 v-if="parsing" :size="12" class="animate-spin" />
            <Upload v-else :size="12" />
            {{ parsing ? 'Reading…' : 'Upload mandate PDF' }}
          </button>
          <input
            ref="uploadInput"
            type="file"
            accept="application/pdf"
            class="hidden"
            @change="onUploadSelected"
          />
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
    <!-- Terminate modal                   -->
    <!-- ────────────────────────────────── -->
    <BaseModal
      :open="showTerminateModal"
      title="Terminate Mandate"
      size="md"
      @close="showTerminateModal = false; terminateReason = ''; terminateOverride = false"
    >
      <div class="space-y-4">
        <p class="text-sm text-gray-600">
          Terminating the mandate ends the agency relationship for this property.
          <span class="font-medium">
            Notice period: {{ activeMandate?.notice_period_days ?? 60 }} days.
          </span>
        </p>

        <div
          v-if="hasActiveLease"
          class="rounded-xl border border-warning-200 bg-warning-50 px-4 py-3 text-xs text-warning-800 flex items-start gap-2"
        >
          <AlertTriangle :size="14" class="mt-0.5 shrink-0 text-warning-600" />
          <div>
            <p class="font-medium">Active lease on this property</p>
            <p>Terminating while tenants are in occupation may create legal exposure under the RHA.
               Tick the override below to proceed anyway.</p>
          </div>
        </div>

        <div>
          <label class="label">Written reason / notice <span class="text-danger-400">*</span></label>
          <textarea
            v-model="terminateReason"
            rows="3"
            placeholder="e.g. Owner has sold the property and will manage it directly."
            class="input"
          />
        </div>

        <label v-if="hasActiveLease" class="flex items-start gap-2 cursor-pointer">
          <input v-model="terminateOverride" type="checkbox" class="mt-0.5 accent-navy" />
          <span class="text-xs text-gray-700">
            I understand the risk — terminate despite an active lease.
          </span>
        </label>

        <div class="flex justify-end gap-3 pt-1">
          <button
            type="button"
            class="btn-ghost"
            @click="showTerminateModal = false; terminateReason = ''; terminateOverride = false"
          >
            Cancel
          </button>
          <button
            class="btn-danger text-sm flex items-center gap-1.5"
            :disabled="!terminateReason.trim() || (hasActiveLease && !terminateOverride) || terminating"
            @click="confirmTerminate"
          >
            <Loader2 v-if="terminating" :size="13" class="animate-spin" />
            <XCircle v-else :size="13" />
            Terminate Mandate
          </button>
        </div>
      </div>
    </BaseModal>

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

        <!-- Pre-fill banner (shown when modal opened from upload) -->
        <div
          v-if="prefillBanner"
          class="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-xs text-gray-700 flex items-start gap-2"
        >
          <FileSignature :size="14" class="text-accent mt-0.5 shrink-0" />
          <div class="space-y-1">
            <p class="font-medium text-gray-800">Pre-filled from uploaded mandate.</p>
            <p>Review every field before saving. Missing fields are highlighted below.</p>
            <p v-if="prefillMissing.length" class="text-micro text-warning-700">
              Could not extract: {{ prefillMissing.join(', ') }}
            </p>
          </div>
        </div>

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
            <label class="label">Start date <span class="text-danger-400">*</span></label>
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
          <p class="text-micro text-gray-400 mb-1">Owner contact (from landlord record)</p>
          <p class="text-sm font-medium text-gray-800">{{ ownerInfo.name }}</p>
          <p class="text-xs text-gray-500">{{ ownerInfo.email || '⚠️ No email — add it to the landlord record before sending' }}</p>
        </div>

        <!-- Notes -->
        <div>
          <label class="label">Notes <span class="text-gray-300">(internal)</span></label>
          <textarea v-model="form.notes" rows="2" class="input" />
        </div>

        <!-- Already-signed checkbox (only for upload-initiated flows) -->
        <label
          v-if="uploadedFile"
          class="flex items-start gap-2 rounded-xl bg-gray-50 px-4 py-3 cursor-pointer"
        >
          <input v-model="markAsSigned" type="checkbox" class="mt-0.5 accent-navy" />
          <div class="text-xs">
            <p class="font-medium text-gray-800">This mandate is already signed</p>
            <p class="text-gray-500">
              Mark as Active and attach the uploaded PDF as the signed document (skips the e-signing flow).
            </p>
          </div>
        </label>

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
  FileSignature, Loader2, Plus, Send, Pencil, PenTool, Upload,
  XCircle, RefreshCw, AlertTriangle,
} from 'lucide-vue-next'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import BaseModal from '../../components/BaseModal.vue'
import EmptyState from '../../components/EmptyState.vue'
import MandateSigningPanel from './MandateSigningPanel.vue'
import { useMandatesStore } from '../../stores/mandates'

const props = defineProps<{ propertyId: number }>()
const { showToast } = useToast()
const mandatesStore = useMandatesStore()

// ── State ────────────────────────────────── //
const loading             = ref(false)
const saving              = ref(false)
const sending             = ref(false)
const parsing             = ref(false)
const terminating         = ref(false)
const renewing            = ref(false)
const showCreateModal     = ref(false)
const showTerminateModal  = ref(false)
const terminateReason     = ref('')
const terminateOverride   = ref(false)
const mandates            = ref<any[]>([])
const editingMandate      = ref<any>(null)

// Upload-and-extract state
const uploadInput    = ref<HTMLInputElement | null>(null)
const uploadedFile   = ref<File | null>(null)
const prefillBanner  = ref(false)
const prefillMissing = ref<string[]>([])
const markAsSigned   = ref(false)

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

// Whether this property has an active lease (used for termination guard).
// We derive this from the mandate's signing_progress if available; in a real
// implementation this could be fetched separately.
const hasActiveLease = computed(() => {
  // The mandate API does not directly expose lease status. We load it on demand
  // when the terminate modal opens. For now expose as a ref so we can populate it.
  return _hasActiveLease.value
})
const _hasActiveLease = ref(false)

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
  // Clear upload/pre-fill state so the next "Create" opens clean.
  uploadedFile.value   = null
  prefillBanner.value  = false
  prefillMissing.value = []
  markAsSigned.value   = false
}

// ── Upload + auto-extract ─────────────────── //
function triggerUpload() {
  uploadInput.value?.click()
}

async function onUploadSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''  // reset so re-selecting the same file still fires change
  if (!file) return

  parsing.value = true
  try {
    const result = await mandatesStore.parseDocument(props.propertyId, file)
    const e = result.extracted || {}

    // Merge extracted values onto the default form — preserve defaults for anything missing.
    const base = defaultForm()
    form.value = {
      ...base,
      mandate_type:          e.mandate_type          ?? base.mandate_type,
      exclusivity:           e.exclusivity           ?? base.exclusivity,
      commission_rate:       e.commission_rate       ?? base.commission_rate,
      commission_period:     e.commission_period     ?? base.commission_period,
      start_date:            e.start_date            ?? base.start_date,
      end_date:              e.end_date              ?? base.end_date,
      notice_period_days:    e.notice_period_days    ?? base.notice_period_days,
      maintenance_threshold: e.maintenance_threshold ?? base.maintenance_threshold,
      notes:                 e.notes                 ?? base.notes,
    }

    uploadedFile.value   = file
    prefillBanner.value  = true
    prefillMissing.value = result.missing || []
    markAsSigned.value   = Boolean(e.is_signed)
    editingMandate.value = null
    showCreateModal.value = true
    showToast('Mandate read — review the pre-filled fields below.', 'success')
  } catch (err) {
    showToast(extractApiError(err, 'Could not identify mandate fields in this document'), 'error')
  } finally {
    parsing.value = false
  }
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

    // Upload-and-already-signed flow: mark as active and attach the PDF.
    if (!editingMandate.value && uploadedFile.value && markAsSigned.value) {
      payload.status = 'active'
    }

    if (editingMandate.value) {
      await mandatesStore.update(editingMandate.value.id, props.propertyId, payload)
      showToast('Mandate updated', 'success')
    } else {
      const created = await mandatesStore.create(payload)
      // If the user uploaded a pre-signed PDF, attach it to signed_document on the newly-created mandate.
      if (uploadedFile.value && created?.id) {
        const fd = new FormData()
        fd.append('signed_document', uploadedFile.value)
        if (markAsSigned.value) fd.append('status', 'active')
        try {
          await api.patch(`/properties/mandates/${created.id}/`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          await mandatesStore.fetchByProperty(props.propertyId, { force: true })
        } catch (attachErr) {
          showToast(extractApiError(attachErr, 'Mandate created but PDF attach failed — retry from the card.'), 'error')
        }
      }
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

// ── Terminate mandate ─────────────────────── //
async function openTerminateModal() {
  // Check for active leases before opening the modal
  try {
    const resp = await api.get(`/leases/?property=${props.propertyId}&status=active&page_size=1`)
    _hasActiveLease.value = (resp.data?.results?.length ?? 0) > 0 || (resp.data?.count ?? 0) > 0
  } catch {
    _hasActiveLease.value = false
  }
  showTerminateModal.value = true
}

async function confirmTerminate() {
  if (!activeMandate.value) return
  terminating.value = true
  try {
    const payload: any = { reason: terminateReason.value.trim() }
    if (terminateOverride.value) payload.override_active_lease = true
    await api.post(`/properties/mandates/${activeMandate.value.id}/terminate/`, payload)
    showToast('Mandate terminated', 'success')
    showTerminateModal.value = false
    terminateReason.value = ''
    terminateOverride.value = false
    await load()
  } catch (err) {
    showToast(extractApiError(err, 'Failed to terminate mandate'), 'error')
  } finally {
    terminating.value = false
  }
}

// ── Renew mandate ─────────────────────────── //
async function renewMandate() {
  if (!activeMandate.value) return
  renewing.value = true
  try {
    const resp = await api.post(`/properties/mandates/${activeMandate.value.id}/renew/`, {})
    showToast('Mandate renewed — new draft created', 'success')
    await load()
    // Open the edit modal so the agent can review & adjust the cloned terms
    const renewed = mandates.value.find((m: any) => m.id === resp.data.id)
    if (renewed) {
      editingMandate.value = renewed
      form.value = {
        mandate_type:          renewed.mandate_type,
        exclusivity:           renewed.exclusivity,
        commission_rate:       Number(renewed.commission_rate),
        commission_period:     renewed.commission_period,
        start_date:            renewed.start_date ?? '',
        end_date:              renewed.end_date ?? '',
        notice_period_days:    renewed.notice_period_days,
        maintenance_threshold: Number(renewed.maintenance_threshold),
        notes:                 renewed.notes ?? '',
      }
      showCreateModal.value = true
    }
  } catch (err) {
    showToast(extractApiError(err, 'Failed to renew mandate'), 'error')
  } finally {
    renewing.value = false
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
    terminated: 'Terminated',
  }
  return labels[s] ?? s
}

function statusBadgeClass(s: string) {
  const map: Record<string, string> = {
    draft:            'bg-gray-100 text-gray-500',
    sent:             'bg-info-50 text-info-700',
    partially_signed: 'bg-warning-50 text-warning-700',
    active:           'bg-success-50 text-success-700',
    expired:          'bg-danger-50 text-danger-600',
    cancelled:        'bg-danger-50 text-danger-600',
    terminated:       'bg-danger-50 text-danger-600',
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
