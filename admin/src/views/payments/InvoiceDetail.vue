<template>
  <div class="space-y-5">
    <PageHeader
      :title="invoice ? `Invoice #${invoice.id}` : 'Invoice'"
      :subtitle="invoice ? `${invoice.period_start} – ${invoice.period_end}` : ''"
      :crumbs="[
        { label: 'Dashboard', to: '/' },
        { label: 'Payments', to: '/payments' },
        { label: invoice ? `Invoice #${invoice.id}` : '…' },
      ]"
    >
      <template #actions>
        <span
          v-if="invoice"
          class="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-full"
          :class="statusClass(invoice.status)"
        >
          {{ statusLabel(invoice.status) }}
        </span>
      </template>
    </PageHeader>

    <LoadingState v-if="loading" variant="form" />
    <ErrorState v-else-if="loadError" :on-retry="load" />

    <template v-else-if="invoice">

      <!-- Credit banner -->
      <div
        v-if="invoice.tenant_in_credit"
        class="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800"
      >
        <TrendingUp :size="16" class="flex-shrink-0 text-blue-500" />
        <span>
          Tenant in credit — <strong>{{ formatZar(Math.abs(invoice.balance_remaining)) }}</strong>
          will carry forward to the next invoice cycle.
        </span>
      </div>

      <!-- Summary cards -->
      <div class="grid grid-cols-3 gap-3">
        <div class="card p-4">
          <div class="text-micro text-gray-500 mb-1">Amount Due</div>
          <div class="text-xl font-bold text-navy tabular-nums">{{ formatZar(invoice.amount_due) }}</div>
        </div>
        <div class="card p-4">
          <div class="text-micro text-gray-500 mb-1">Amount Paid</div>
          <div class="text-xl font-bold tabular-nums" :class="invoice.amount_paid > 0 ? 'text-green-600' : 'text-gray-400'">
            {{ formatZar(invoice.amount_paid) }}
          </div>
        </div>
        <div class="card p-4">
          <div class="text-micro text-gray-500 mb-1">Balance Remaining</div>
          <div
            class="text-xl font-bold tabular-nums"
            :class="invoice.balance_remaining > 0 ? 'text-red-600' : invoice.balance_remaining < 0 ? 'text-blue-600' : 'text-green-600'"
          >
            {{ invoice.balance_remaining > 0 ? formatZar(invoice.balance_remaining) : invoice.balance_remaining < 0 ? `−${formatZar(Math.abs(invoice.balance_remaining))} credit` : 'Nil' }}
          </div>
        </div>
      </div>

      <!-- Payments list -->
      <div class="card overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 class="text-sm font-semibold text-gray-800">Payments</h3>
          <button class="btn-ghost btn-xs" @click="showAddPayment = true">
            <Plus :size="13" /> Record Payment
          </button>
        </div>

        <EmptyState
          v-if="!invoice.payments?.length"
          title="No payments yet"
          description="Record a payment or assign an unmatched deposit."
          :icon="Banknote"
          compact
        />

        <table v-else class="min-w-full divide-y divide-gray-100">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2.5 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Date</th>
              <th class="px-4 py-2.5 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Payer</th>
              <th class="px-4 py-2.5 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Source</th>
              <th class="px-4 py-2.5 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Reference</th>
              <th class="px-4 py-2.5 text-right text-micro font-semibold text-gray-500 uppercase tracking-wider">Amount</th>
              <th class="px-4 py-2.5 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-4 py-2.5 text-right text-micro font-semibold text-gray-500 uppercase tracking-wider"></th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
            <tr
              v-for="pmt in invoice.payments"
              :key="pmt.id"
              class="hover:bg-gray-50 transition-colors"
              :class="pmt.status === 'reversed' ? 'opacity-50' : ''"
            >
              <td class="px-4 py-3 text-sm text-gray-700 tabular-nums whitespace-nowrap">{{ pmt.payment_date }}</td>
              <td class="px-4 py-3 text-sm text-gray-900 max-w-[10rem] truncate">{{ pmt.payer_name || '—' }}</td>
              <td class="px-4 py-3">
                <span class="text-micro px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium capitalize">
                  {{ pmt.source }}
                </span>
              </td>
              <td class="px-4 py-3 font-mono text-xs text-gray-500 max-w-[10rem] truncate">{{ pmt.reference || '—' }}</td>
              <td class="px-4 py-3 text-sm font-semibold text-right tabular-nums text-navy whitespace-nowrap">
                {{ formatZar(pmt.amount) }}
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center text-micro font-semibold px-1.5 py-0.5 rounded-full" :class="statusClass(pmt.status)">
                  {{ statusLabel(pmt.status) }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="pmt.status === 'cleared'"
                  class="btn-ghost btn-xs text-red-600 hover:bg-red-50"
                  @click="openReverse(pmt)"
                >
                  Reverse
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Audit log -->
      <div class="card overflow-hidden">
        <div class="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
          <History :size="15" class="text-gray-400" />
          <h3 class="text-sm font-semibold text-gray-800">Audit Trail</h3>
        </div>
        <EmptyState v-if="!auditLogs.length" title="No events yet" compact :icon="History" />
        <ul v-else class="divide-y divide-gray-100">
          <li v-for="log in auditLogs" :key="log.id" class="flex items-start gap-3 px-4 py-3">
            <div class="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Clock :size="13" class="text-gray-400" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-800 capitalize">{{ eventLabel(log.event) }}</span>
                <span v-if="log.from_status || log.to_status" class="text-micro text-gray-500">
                  {{ log.from_status || '—' }} → {{ log.to_status || '—' }}
                </span>
              </div>
              <div class="text-xs text-gray-400 mt-0.5">
                {{ formatDatetime(log.created_at) }}
                <span v-if="log.actor_email" class="ml-1 text-gray-500">· {{ log.actor_email }}</span>
              </div>
              <div v-if="log.detail && Object.keys(log.detail).length" class="mt-1 font-mono text-micro text-gray-500 bg-gray-50 rounded px-2 py-1 whitespace-pre-wrap">
                {{ JSON.stringify(log.detail, null, 2) }}
              </div>
            </div>
          </li>
        </ul>
      </div>
    </template>

    <!-- Record Payment Modal -->
    <BaseModal :open="showAddPayment" @close="showAddPayment = false" title="Record Payment">
      <div class="space-y-4 p-4">
        <div>
          <label class="form-label">Amount (ZAR) <span class="text-red-500">*</span></label>
          <input v-model="pmtForm.amount" type="number" step="0.01" min="0.01" class="form-input" placeholder="e.g. 10000.00" />
        </div>
        <div>
          <label class="form-label">Payment Date <span class="text-red-500">*</span></label>
          <input v-model="pmtForm.payment_date" type="date" class="form-input" />
        </div>
        <div>
          <label class="form-label">Source</label>
          <select v-model="pmtForm.source" class="form-input">
            <option value="tenant">Tenant</option>
            <option value="guarantor">Guarantor</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label class="form-label">Payer Name</label>
          <input v-model="pmtForm.payer_name" type="text" class="form-input" placeholder="Name on bank statement" />
        </div>
        <div>
          <label class="form-label">Bank Reference</label>
          <input v-model="pmtForm.reference" type="text" class="form-input" placeholder="EFT reference" />
        </div>
        <div class="flex justify-end gap-2 pt-1">
          <button class="btn-ghost" @click="showAddPayment = false">Cancel</button>
          <button class="btn-primary" :disabled="!pmtForm.amount || !pmtForm.payment_date || savingPayment" @click="submitPayment">
            <Loader2 v-if="savingPayment" :size="14" class="animate-spin" />
            Record Payment
          </button>
        </div>
      </div>
    </BaseModal>

    <!-- Reverse Payment Modal -->
    <BaseModal :open="!!reversing" @close="reversing = null" title="Reverse Payment">
      <div class="space-y-4 p-4">
        <p class="text-sm text-gray-600">
          Reversing <strong>{{ formatZar(reversing?.amount) }}</strong> from
          {{ reversing?.payer_name || reversing?.reference }}. This will mark the payment as
          bounced and recompute the invoice balance.
        </p>
        <div>
          <label class="form-label">Reason <span class="text-red-500">*</span></label>
          <textarea v-model="reversalReason" class="form-input" rows="2" placeholder="e.g. Insufficient funds, payment recalled" />
        </div>
        <div class="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle :size="13" class="flex-shrink-0" />
          The tenant and agent will be notified of this reversal.
        </div>
        <div class="flex justify-end gap-2 pt-1">
          <button class="btn-ghost" @click="reversing = null">Cancel</button>
          <button class="btn-primary bg-red-600 hover:bg-red-700" :disabled="!reversalReason.trim() || savingReversal" @click="submitReversal">
            <Loader2 v-if="savingReversal" :size="14" class="animate-spin" />
            Confirm Reversal
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Banknote, History, Clock, TrendingUp, AlertTriangle, Loader2 } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'
import EmptyState from '../../components/EmptyState.vue'
import BaseModal from '../../components/BaseModal.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'

const route = useRoute()
const { showToast } = useToast()

const loading = ref(false)
const loadError = ref(false)
const invoice = ref<any | null>(null)
const auditLogs = ref<any[]>([])

const showAddPayment = ref(false)
const savingPayment = ref(false)
const pmtForm = reactive({
  amount: '',
  payment_date: new Date().toISOString().slice(0, 10),
  source: 'tenant',
  payer_name: '',
  reference: '',
})

const reversing = ref<any | null>(null)
const reversalReason = ref('')
const savingReversal = ref(false)

async function load() {
  loading.value = true
  loadError.value = false
  try {
    const [invRes, logRes] = await Promise.all([
      api.get(`/payments/invoices/${route.params.id}/`),
      api.get(`/payments/invoices/${route.params.id}/audit-log/`),
    ])
    invoice.value = invRes.data
    auditLogs.value = logRes.data.results ?? logRes.data
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function submitPayment() {
  savingPayment.value = true
  try {
    await api.post(`/payments/invoices/${route.params.id}/payments/`, {
      amount: pmtForm.amount,
      payment_date: pmtForm.payment_date,
      source: pmtForm.source,
      payer_name: pmtForm.payer_name,
      reference: pmtForm.reference,
    })
    showToast('Payment recorded and invoice reconciled.', 'success')
    showAddPayment.value = false
    Object.assign(pmtForm, { amount: '', payer_name: '', reference: '', source: 'tenant' })
    await load()
  } catch (err: any) {
    showToast(extractApiError(err) || 'Failed to record payment.', 'error')
  } finally {
    savingPayment.value = false
  }
}

function openReverse(pmt: any) {
  reversing.value = pmt
  reversalReason.value = ''
}

async function submitReversal() {
  if (!reversing.value) return
  savingReversal.value = true
  try {
    await api.post(`/payments/payments/${reversing.value.id}/reverse/`, {
      reason: reversalReason.value,
    })
    showToast('Payment reversed. Invoice balance updated.', 'success')
    reversing.value = null
    await load()
  } catch (err: any) {
    showToast(extractApiError(err) || 'Failed to reverse payment.', 'error')
  } finally {
    savingReversal.value = false
  }
}

function formatZar(value: number | string | null | undefined) {
  if (value == null) return 'R 0.00'
  const n = typeof value === 'string' ? parseFloat(value) : value
  return `R ${n.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function statusClass(status: string) {
  return ({
    unpaid: 'bg-red-100 text-red-700',
    partially_paid: 'bg-amber-100 text-amber-700',
    paid: 'bg-green-100 text-green-700',
    overpaid: 'bg-blue-100 text-blue-700',
    reversed: 'bg-gray-100 text-gray-600',
    cleared: 'bg-green-100 text-green-700',
  } as Record<string, string>)[status] ?? 'bg-gray-100 text-gray-600'
}

function statusLabel(status: string) {
  return ({
    unpaid: 'Unpaid',
    partially_paid: 'Partially Paid',
    paid: 'Paid',
    overpaid: 'Overpaid',
    reversed: 'Reversed',
    cleared: 'Cleared',
  } as Record<string, string>)[status] ?? status
}

function eventLabel(event: string) {
  return event.replace(/_/g, ' ')
}

function formatDatetime(dt: string) {
  if (!dt) return ''
  return new Date(dt).toLocaleString('en-ZA', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(load)
</script>
