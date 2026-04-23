<template>
  <div class="space-y-5 max-w-4xl">
    <!-- Summary cards -->
    <div v-if="summary" class="grid grid-cols-2 gap-4">
      <div class="card p-5">
        <div class="text-xs text-gray-400 uppercase tracking-wide mb-1">Outstanding Balance</div>
        <div class="text-3xl font-bold text-amber-600">
          R{{ Number(summary.outstanding_amount).toLocaleString('en-ZA') }}
        </div>
        <div class="text-xs text-gray-400 mt-1">Pending approval or awaiting EFT</div>
      </div>
      <div class="card p-5">
        <div class="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Paid</div>
        <div class="text-3xl font-bold text-success-600">
          R{{ Number(summary.paid_amount).toLocaleString('en-ZA') }}
        </div>
        <div class="text-xs text-gray-400 mt-1">Lifetime payments received</div>
      </div>
    </div>

    <!-- Invoice list -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-medium text-gray-700">Invoice History</h2>
      </div>

      <div v-if="loading" class="p-5 space-y-3">
        <div v-for="i in 3" :key="i" class="animate-pulse flex gap-3 items-center">
          <div class="h-4 bg-gray-100 rounded flex-1"></div>
          <div class="h-4 bg-gray-100 rounded w-24"></div>
        </div>
      </div>

      <div v-else-if="invoices.length" class="divide-y divide-gray-100">
        <div v-for="inv in invoices" :key="inv.id"
          class="px-5 py-4 flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-medium text-sm text-gray-900">{{ inv.job_title || 'Job #' + inv.id }}</span>
              <span :class="invoiceStatusClass(inv.status)" class="text-micro px-2 py-0.5 rounded-full font-medium">
                {{ inv.status_label }}
              </span>
            </div>
            <div class="text-xs text-gray-400 mt-1">
              Submitted {{ formatDate(inv.submitted_at) }}
              <span v-if="inv.paid_at"> · Paid {{ formatDate(inv.paid_at) }}</span>
            </div>
            <div v-if="inv.rejection_reason" class="mt-1.5 text-xs text-danger-600 bg-danger-50 px-2 py-1 rounded">
              Rejected: {{ inv.rejection_reason }}
            </div>
            <div v-if="inv.paid_reference" class="mt-1 text-xs text-gray-500">
              Ref: {{ inv.paid_reference }}
            </div>
          </div>
          <div class="shrink-0 text-right">
            <div class="text-base font-semibold text-gray-900">R{{ Number(inv.total_amount).toLocaleString('en-ZA') }}</div>
            <a v-if="inv.invoice_file" :href="inv.invoice_file" target="_blank"
              class="text-xs text-navy hover:underline flex items-center gap-1 justify-end mt-1">
              <FileText :size="12" /> View PDF
            </a>
          </div>
        </div>
      </div>

      <div v-else class="p-8 text-center text-gray-400 text-sm">
        No invoices yet. Submit an invoice once a job is awarded to you.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { FileText } from 'lucide-vue-next'

const loading = ref(true)
const invoices = ref<any[]>([])
const summary = ref<{ outstanding_amount: string; paid_amount: string } | null>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/maintenance/supplier/payments/')
    invoices.value = data.invoices
    summary.value = { outstanding_amount: data.outstanding_amount, paid_amount: data.paid_amount }
  } finally {
    loading.value = false
  }
})

function invoiceStatusClass(s: string) {
  return {
    pending: 'bg-blue-100 text-blue-700',
    approved: 'bg-amber-100 text-amber-700',
    rejected: 'bg-red-100 text-red-700',
    paid: 'bg-success-100 text-success-700',
  }[s] ?? 'bg-gray-100 text-gray-600'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
