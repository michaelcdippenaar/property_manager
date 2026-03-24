<template>
  <div class="space-y-5">
    <h1 class="text-lg font-semibold text-gray-900">Maintenance Requests</h1>

    <!-- Filter pills -->
    <div class="flex gap-2 flex-wrap">
      <button
        v-for="f in filters"
        :key="f.value"
        @click="activeFilter = f.value; loadRequests()"
        class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
        :class="activeFilter === f.value
          ? 'bg-navy text-white'
          : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card p-5 space-y-3 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-1/3"></div>
        <div class="h-4 bg-gray-100 rounded w-2/3"></div>
        <div class="h-3 bg-gray-100 rounded w-full"></div>
      </div>
    </div>

    <!-- Request cards -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="req in requests" :key="req.id" class="card p-5 space-y-3">
        <div class="flex items-start justify-between gap-2">
          <span :class="priorityBadge(req.priority)">{{ req.priority }}</span>
          <select
            :value="req.status"
            @change="updateStatus(req, ($event.target as HTMLSelectElement).value)"
            class="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 bg-white outline-none focus:ring-1 focus:ring-navy/30 cursor-pointer"
          >
            <option v-for="s in statusOptions" :key="s" :value="s">{{ s.replace('_', ' ') }}</option>
          </select>
        </div>
        <div class="font-medium text-gray-900 text-sm">{{ req.title }}</div>
        <p class="text-xs text-gray-500 leading-relaxed line-clamp-2">{{ req.description }}</p>

        <!-- Supplier assignment -->
        <div class="pt-2 border-t border-gray-100">
          <div v-if="req.supplier_name" class="flex items-center justify-between">
            <div class="flex items-center gap-1.5 text-xs text-gray-600">
              <Truck :size="11" />
              {{ req.supplier_name }}
            </div>
          </div>
          <div v-else class="flex items-center gap-2">
            <select
              :value="req.supplier ?? ''"
              @change="assignSupplier(req, ($event.target as HTMLSelectElement).value)"
              class="flex-1 text-xs border border-gray-200 rounded-lg px-2 py-1.5 text-gray-600 bg-white outline-none focus:ring-1 focus:ring-navy/30 cursor-pointer"
            >
              <option value="">Assign supplier…</option>
              <option v-for="s in suppliers" :key="s.id" :value="s.id">
                {{ s.display_name || s.name }}
              </option>
            </select>
          </div>
        </div>

        <!-- Get Quotes / Dispatch -->
        <div class="pt-2 border-t border-gray-100 flex items-center justify-between">
          <div class="flex items-center gap-1.5 text-xs text-gray-400">
            <Clock :size="11" />
            {{ formatDate(req.created_at) }}
          </div>
          <button
            v-if="req.status === 'open' || req.status === 'in_progress'"
            @click="getQuotes(req)"
            class="text-xs text-navy hover:underline flex items-center gap-1"
            :disabled="dispatching === req.id"
          >
            <Send :size="11" />
            {{ dispatching === req.id ? 'Loading…' : 'Get Quotes' }}
          </button>
        </div>
      </div>

      <div v-if="!requests.length" class="col-span-full text-center text-gray-400 py-16">
        No maintenance requests for this filter
      </div>
    </div>

    <!-- Dispatch dialog — shows ranked suppliers and lets agent select & send -->
    <Teleport to="body">
      <div v-if="dispatchDialog" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="dispatchDialog = false" />
        <div class="relative card w-full max-w-2xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h2 class="font-semibold text-gray-900">Get Quotes — {{ dispatchRequest?.title }}</h2>
              <p class="text-xs text-gray-500 mt-0.5">Select suppliers to send quote requests to</p>
            </div>
            <button @click="dispatchDialog = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <!-- Supplier ranking -->
          <div class="space-y-2">
            <div v-for="(s, idx) in suggestions" :key="s.supplier_id"
              class="flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer"
              :class="selectedSupplierIds.has(s.supplier_id)
                ? 'border-navy bg-navy/5'
                : 'border-gray-200 hover:border-gray-300'"
              @click="toggleSupplierSelection(s.supplier_id)"
            >
              <input type="checkbox" :checked="selectedSupplierIds.has(s.supplier_id)"
                class="rounded" @click.stop="toggleSupplierSelection(s.supplier_id)" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900 text-sm">{{ s.supplier_name }}</span>
                  <span class="text-xs text-gray-400">{{ s.supplier_city }}</span>
                  <span v-if="idx === 0" class="badge-green text-[10px]">Best match</span>
                </div>
                <div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span v-if="s.reasons?.proximity?.distance_km" class="flex items-center gap-1">
                    <MapPin :size="10" /> {{ s.reasons.proximity.distance_km }}km
                  </span>
                  <span v-for="t in s.trades?.slice(0, 3)" :key="t"
                    class="px-1 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px]">
                    {{ t }}
                  </span>
                </div>
              </div>
              <div class="text-right">
                <div class="text-sm font-mono font-medium text-navy">{{ s.score }}</div>
                <div class="text-[10px] text-gray-400">score</div>
              </div>
            </div>
          </div>

          <div v-if="!suggestions.length" class="text-center text-gray-400 py-8">
            No active suppliers found
          </div>

          <!-- Notes -->
          <div>
            <label class="label">Notes to suppliers (optional)</label>
            <textarea v-model="dispatchNotes" class="input" rows="2" placeholder="Access instructions, urgency details…"></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="dispatchDialog = false">Cancel</button>
            <button class="btn-primary" :disabled="!selectedSupplierIds.size || sending"
              @click="sendDispatch">
              <Loader2 v-if="sending" :size="14" class="animate-spin" />
              <Send v-else :size="14" />
              Send to {{ selectedSupplierIds.size }} supplier(s)
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { Clock, Truck, Send, X, Loader2, MapPin } from 'lucide-vue-next'

const loading = ref(true)
const activeFilter = ref('all')
const requests = ref<any[]>([])
const suppliers = ref<any[]>([])
const statusOptions = ['open', 'in_progress', 'resolved', 'closed']

// Dispatch state
const dispatching = ref<number | null>(null)
const dispatchDialog = ref(false)
const dispatchRequest = ref<any | null>(null)
const dispatchId = ref<number | null>(null)
const suggestions = ref<any[]>([])
const selectedSupplierIds = ref(new Set<number>())
const dispatchNotes = ref('')
const sending = ref(false)

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
]

onMounted(async () => {
  await Promise.all([loadRequests(), loadSuppliers()])
})

async function loadSuppliers() {
  try {
    const { data } = await api.get('/maintenance/suppliers/', { params: { is_active: true } })
    suppliers.value = data.results ?? data
  } catch { /* ignore */ }
}

async function loadRequests() {
  loading.value = true
  try {
    const params = activeFilter.value !== 'all' ? { status: activeFilter.value } : {}
    const { data } = await api.get('/maintenance/', { params })
    requests.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function updateStatus(req: any, newStatus: string) {
  await api.patch(`/maintenance/${req.id}/`, { status: newStatus })
  req.status = newStatus
}

async function assignSupplier(req: any, supplierId: string) {
  const value = supplierId ? Number(supplierId) : null
  await api.patch(`/maintenance/${req.id}/`, { supplier: value })
  req.supplier = value
  const sup = suppliers.value.find((s: any) => s.id === value)
  req.supplier_name = sup ? (sup.display_name || sup.name) : null
}

async function getQuotes(req: any) {
  dispatching.value = req.id
  try {
    const { data } = await api.post(`/maintenance/${req.id}/dispatch/`)
    dispatchRequest.value = req
    dispatchId.value = data.dispatch?.id
    suggestions.value = data.suggestions || []
    // Auto-select top 3
    selectedSupplierIds.value = new Set(
      suggestions.value.slice(0, 3).map((s: any) => s.supplier_id)
    )
    dispatchNotes.value = ''
    dispatchDialog.value = true
  } finally {
    dispatching.value = null
  }
}

function toggleSupplierSelection(id: number) {
  if (selectedSupplierIds.value.has(id)) selectedSupplierIds.value.delete(id)
  else selectedSupplierIds.value.add(id)
}

async function sendDispatch() {
  if (!dispatchRequest.value || !selectedSupplierIds.value.size) return
  sending.value = true
  try {
    await api.post(`/maintenance/${dispatchRequest.value.id}/dispatch/send/`, {
      supplier_ids: Array.from(selectedSupplierIds.value),
      notes: dispatchNotes.value,
    })
    dispatchDialog.value = false
    await loadRequests()
  } finally {
    sending.value = false
  }
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
