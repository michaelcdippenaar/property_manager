<template>
  <div class="card px-5 py-4">
    <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Supplier Invoice</h3>

    <!-- Empty state -->
    <p v-if="!invoice && !loading" class="text-xs text-gray-400">
      No invoice submitted yet.
    </p>

    <!-- Loading -->
    <div v-else-if="loading" class="space-y-2 animate-pulse">
      <div class="h-3 bg-gray-100 rounded w-1/3"></div>
      <div class="h-3 bg-gray-100 rounded w-1/2"></div>
    </div>

    <!-- Invoice detail -->
    <template v-else-if="invoice">
      <!-- Status + amount row -->
      <div class="flex items-center justify-between mb-3">
        <span :class="statusBadge(invoice.status)" class="text-sm font-medium">
          {{ invoice.status_label || invoice.status }}
        </span>
        <span class="text-sm font-semibold text-gray-900">
          R{{ Number(invoice.total_amount).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
        </span>
      </div>

      <!-- PDF download -->
      <div v-if="invoice.invoice_file" class="mb-3">
        <a
          :href="invoice.invoice_file"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 text-xs text-navy hover:underline"
        >
          <FileText :size="13" />
          Download Invoice PDF
        </a>
      </div>

      <!-- Notes -->
      <p v-if="invoice.notes" class="text-xs text-gray-500 mb-3">{{ invoice.notes }}</p>

      <!-- Rejection reason (read-only) -->
      <div v-if="invoice.rejection_reason" class="mb-3 p-2.5 rounded-md bg-danger-50 border border-danger-100">
        <p class="text-xs text-danger-700">
          <span class="font-medium">Rejection reason:</span> {{ invoice.rejection_reason }}
        </p>
      </div>

      <!-- Paid reference (read-only) -->
      <div v-if="invoice.paid_reference" class="mb-3 p-2.5 rounded-md bg-success-50 border border-success-100">
        <p class="text-xs text-success-700">
          <span class="font-medium">EFT reference:</span> {{ invoice.paid_reference }}
        </p>
      </div>

      <!-- Action buttons for pending invoice -->
      <div v-if="invoice.status === 'pending'" class="flex flex-col gap-2 mt-2">
        <!-- Approve -->
        <button
          class="btn-success btn-sm w-full"
          :disabled="acting"
          @click="handleApprove"
        >
          <Check :size="13" />
          Approve Invoice
        </button>

        <!-- Reject toggle -->
        <button
          class="btn-danger btn-sm w-full"
          :disabled="acting"
          @click="rejectOpen = !rejectOpen"
        >
          <X :size="13" />
          Reject Invoice
        </button>

        <!-- Reject form -->
        <div v-if="rejectOpen" class="space-y-2 mt-1">
          <textarea
            v-model="rejectReason"
            rows="2"
            class="input text-sm w-full"
            placeholder="Rejection reason (required)"
          ></textarea>
          <button
            class="btn-danger btn-sm w-full"
            :disabled="acting || !rejectReason.trim()"
            @click="handleReject"
          >
            <Loader2 v-if="acting" :size="13" class="animate-spin" />
            Confirm Rejection
          </button>
        </div>
      </div>

      <!-- Action buttons for approved invoice -->
      <div v-if="invoice.status === 'approved'" class="flex flex-col gap-2 mt-2">
        <button
          class="btn-primary btn-sm w-full"
          :disabled="acting"
          @click="paidOpen = !paidOpen"
        >
          <CreditCard :size="13" />
          Mark as Paid
        </button>

        <div v-if="paidOpen" class="space-y-2 mt-1">
          <input
            v-model="eftReference"
            type="text"
            class="input text-sm w-full"
            placeholder="EFT reference (optional)"
          />
          <button
            class="btn-primary btn-sm w-full"
            :disabled="acting"
            @click="handleMarkPaid"
          >
            <Loader2 v-if="acting" :size="13" class="animate-spin" />
            Confirm Payment
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { FileText, Check, X, CreditCard, Loader2 } from 'lucide-vue-next'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const props = defineProps<{ requestId: number }>()
const emit = defineEmits<{ (e: 'activityUpdated'): void }>()

const toast = useToast()

const loading = ref(false)
const acting = ref(false)
const invoice = ref<any | null>(null)

const rejectOpen = ref(false)
const rejectReason = ref('')
const paidOpen = ref(false)
const eftReference = ref('')

async function loadInvoice() {
  loading.value = true
  try {
    const { data } = await api.get(`/maintenance/${props.requestId}/invoice/`)
    invoice.value = data
  } catch (err: any) {
    // 404 means no invoice yet — that's fine
    if (err?.response?.status !== 404) {
      toast.error('Failed to load invoice')
    }
    invoice.value = null
  } finally {
    loading.value = false
  }
}

async function postAction(payload: Record<string, string>) {
  acting.value = true
  try {
    await api.post(`/maintenance/${props.requestId}/invoice/`, payload)
    await loadInvoice()
    emit('activityUpdated')
    return true
  } catch (err: any) {
    const detail = err?.response?.data?.detail || 'Action failed'
    toast.error(detail)
    return false
  } finally {
    acting.value = false
  }
}

async function handleApprove() {
  const ok = await postAction({ action: 'approve' })
  if (ok) toast.success('Invoice approved')
}

async function handleReject() {
  if (!rejectReason.value.trim()) return
  const ok = await postAction({ action: 'reject', reason: rejectReason.value.trim() })
  if (ok) {
    toast.success('Invoice rejected')
    rejectOpen.value = false
    rejectReason.value = ''
  }
}

async function handleMarkPaid() {
  const ok = await postAction({ action: 'paid', reference: eftReference.value.trim() })
  if (ok) {
    toast.success('Invoice marked as paid')
    paidOpen.value = false
    eftReference.value = ''
  }
}

function statusBadge(s: string) {
  return {
    pending: 'badge-amber',
    approved: 'badge-green',
    rejected: 'badge-red',
    paid: 'badge-blue',
  }[s] ?? 'badge-gray'
}

onMounted(loadInvoice)
watch(() => props.requestId, loadInvoice)
</script>
