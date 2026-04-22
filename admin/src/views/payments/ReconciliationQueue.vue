<template>
  <div class="space-y-5">
    <PageHeader
      title="Reconciliation Queue"
      subtitle="Unmatched payments that need to be assigned to a lease invoice."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Payments', to: '/payments' }, { label: 'Reconciliation Queue' }]"
    >
      <template #actions>
        <button class="btn-ghost" @click="load">
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
          Refresh
        </button>
      </template>
    </PageHeader>

    <!-- Summary strip -->
    <div class="grid grid-cols-3 gap-3">
      <div class="card p-4 flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
          <AlertTriangle :size="18" class="text-amber-500" />
        </div>
        <div>
          <div class="text-xl font-bold text-navy tabular-nums">{{ pendingCount }}</div>
          <div class="text-xs text-gray-500">Needs reconciliation</div>
        </div>
      </div>
      <div class="card p-4 flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
          <CheckCircle2 :size="18" class="text-green-500" />
        </div>
        <div>
          <div class="text-xl font-bold text-navy tabular-nums">{{ resolvedToday }}</div>
          <div class="text-xs text-gray-500">Resolved today</div>
        </div>
      </div>
      <div class="card p-4 flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-navy/5 flex items-center justify-center flex-shrink-0">
          <Banknote :size="18" class="text-navy/60" />
        </div>
        <div>
          <div class="text-xl font-bold text-navy tabular-nums">{{ formatZar(pendingTotal) }}</div>
          <div class="text-xs text-gray-500">Total pending (ZAR)</div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <LoadingState v-if="loading" variant="table" :rows="4" />

      <ErrorState v-else-if="loadError" :on-retry="load" />

      <EmptyState
        v-else-if="!items.length"
        title="Queue is clear"
        description="All deposits have been matched to invoices."
        :icon="CheckCircle2"
      />

      <table v-else class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Date</th>
            <th class="px-4 py-3 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Payer</th>
            <th class="px-4 py-3 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Reference</th>
            <th class="px-4 py-3 text-right text-micro font-semibold text-gray-500 uppercase tracking-wider">Amount (ZAR)</th>
            <th class="px-4 py-3 text-left text-micro font-semibold text-gray-500 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-right text-micro font-semibold text-gray-500 uppercase tracking-wider"></th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          <tr v-for="item in items" :key="item.id" class="hover:bg-gray-50 transition-colors">
            <td class="px-4 py-3 text-sm text-gray-700 tabular-nums whitespace-nowrap">{{ item.payment_date }}</td>
            <td class="px-4 py-3 text-sm text-gray-900 font-medium max-w-[12rem] truncate">
              {{ item.payer_name || '—' }}
            </td>
            <td class="px-4 py-3 font-mono text-xs text-gray-600 max-w-[12rem] truncate">
              {{ item.reference || '—' }}
            </td>
            <td class="px-4 py-3 text-sm font-semibold text-right tabular-nums text-navy">
              {{ formatZar(item.amount) }}
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1 text-micro font-semibold px-2 py-0.5 rounded-full"
                :class="statusClass(item.status)"
              >
                {{ statusLabel(item.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="item.status === 'pending'"
                class="btn-ghost btn-xs"
                @click="openAssign(item)"
              >
                Assign
              </button>
              <span v-else class="text-micro text-gray-400">Done</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Assign Modal -->
    <BaseModal v-if="assigning" :open="!!assigning" @close="assigning = null" title="Assign to Invoice">
      <div class="space-y-4 p-4">
        <p class="text-sm text-gray-600">
          Assign <span class="font-semibold text-navy">{{ formatZar(assigning.amount) }}</span>
          from <span class="font-medium">{{ assigning.payer_name || assigning.reference }}</span>
          to an existing invoice.
        </p>

        <!-- Invoice search -->
        <div>
          <label class="form-label">Search Invoice (lease number or tenant name)</label>
          <input
            v-model="invoiceSearch"
            type="text"
            class="form-input"
            placeholder="e.g. L-202601-0001"
            @input="searchInvoices"
          />
        </div>

        <div v-if="invoiceResults.length" class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-48 overflow-y-auto">
          <button
            v-for="inv in invoiceResults"
            :key="inv.id"
            class="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-gray-50 transition-colors text-sm"
            :class="selectedInvoice?.id === inv.id ? 'bg-navy/5' : ''"
            @click="selectedInvoice = inv"
          >
            <div>
              <div class="font-medium text-gray-900">{{ inv.lease_number }}</div>
              <div class="text-xs text-gray-500">{{ inv.period_start }} – {{ inv.period_end }}</div>
            </div>
            <div class="text-right">
              <div class="font-semibold text-navy tabular-nums">{{ formatZar(inv.amount_due) }}</div>
              <div class="text-xs" :class="statusClass(inv.status)">{{ statusLabel(inv.status) }}</div>
            </div>
          </button>
        </div>

        <div v-if="selectedInvoice" class="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-sm text-green-800">
          Selected: <strong>{{ selectedInvoice.lease_number }}</strong> — {{ formatZar(selectedInvoice.amount_due) }} due
        </div>

        <div class="flex items-center justify-end gap-2 pt-2">
          <button class="btn-ghost" @click="assigning = null">Cancel</button>
          <button
            class="btn-primary"
            :disabled="!selectedInvoice || saving"
            @click="confirmAssign"
          >
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            Assign Payment
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, AlertTriangle, CheckCircle2, Banknote, Loader2 } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'
import EmptyState from '../../components/EmptyState.vue'
import BaseModal from '../../components/BaseModal.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'

const { showToast } = useToast()

const loading = ref(false)
const loadError = ref(false)
const items = ref<any[]>([])
const assigning = ref<any | null>(null)
const invoiceSearch = ref('')
const invoiceResults = ref<any[]>([])
const selectedInvoice = ref<any | null>(null)
const saving = ref(false)

const pendingCount = computed(() => items.value.filter(i => i.status === 'pending').length)
const pendingTotal = computed(() =>
  items.value.filter(i => i.status === 'pending').reduce((s, i) => s + parseFloat(i.amount), 0)
)
const resolvedToday = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return items.value.filter(i => i.status === 'resolved' && i.resolved_at?.startsWith(today)).length
})

async function load() {
  loading.value = true
  loadError.value = false
  try {
    const res = await api.get('/payments/unmatched/')
    items.value = res.data.results ?? res.data
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function searchInvoices() {
  if (invoiceSearch.value.length < 2) { invoiceResults.value = []; return }
  try {
    const res = await api.get('/payments/invoices/', { params: { search: invoiceSearch.value } })
    invoiceResults.value = res.data.results ?? res.data
  } catch {
    invoiceResults.value = []
  }
}

function openAssign(item: any) {
  assigning.value = item
  invoiceSearch.value = ''
  invoiceResults.value = []
  selectedInvoice.value = null
}

async function confirmAssign() {
  if (!assigning.value || !selectedInvoice.value) return
  saving.value = true
  try {
    await api.post(`/payments/unmatched/${assigning.value.id}/assign/`, {
      invoice_id: selectedInvoice.value.id,
    })
    showToast('Payment assigned and invoice reconciled.', 'success')
    assigning.value = null
    await load()
  } catch (err: any) {
    showToast(extractApiError(err) || 'Failed to assign payment.', 'error')
  } finally {
    saving.value = false
  }
}

function formatZar(value: number | string) {
  const n = typeof value === 'string' ? parseFloat(value) : value
  return `R ${n.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function statusClass(status: string) {
  return {
    pending: 'bg-amber-100 text-amber-700',
    resolved: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    unpaid: 'bg-red-100 text-red-700',
    partially_paid: 'bg-amber-100 text-amber-700',
    paid: 'bg-green-100 text-green-700',
    overpaid: 'bg-blue-100 text-blue-700',
    reversed: 'bg-gray-100 text-gray-600',
  }[status] ?? 'bg-gray-100 text-gray-600'
}

function statusLabel(status: string) {
  return {
    pending: 'Needs reconciliation',
    resolved: 'Resolved',
    rejected: 'Rejected',
    unpaid: 'Unpaid',
    partially_paid: 'Partially paid',
    paid: 'Paid',
    overpaid: 'Overpaid',
    reversed: 'Reversed',
  }[status] ?? status
}

onMounted(load)
</script>
