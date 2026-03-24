<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <div class="flex gap-2">
        <button
          v-for="f in statusFilters"
          :key="f.value"
          @click="activeFilter = f.value; loadSuppliers()"
          class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
          :class="activeFilter === f.value
            ? 'bg-navy text-white'
            : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'"
        >
          {{ f.label }}
        </button>
      </div>
      <button class="btn-primary" @click="openCreate">
        <Plus :size="15" /> Add Supplier
      </button>
    </div>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <div class="relative max-w-xs">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input v-model="search" class="input pl-8" placeholder="Search suppliers…" />
        </div>
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Supplier</th>
            <th>Trades</th>
            <th>Phone</th>
            <th>City</th>
            <th>Active Jobs</th>
            <th>Rating</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in filteredSuppliers"
            :key="s.id"
            class="cursor-pointer hover:bg-gray-50"
            @click="openDetail(s)"
          >
            <td>
              <div class="font-medium text-gray-900">{{ s.company_name || s.name }}</div>
              <div v-if="s.company_name" class="text-xs text-gray-400 mt-0.5">{{ s.name }}</div>
            </td>
            <td>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="t in s.trades"
                  :key="t.id"
                  class="inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700"
                >
                  {{ t.label }}
                </span>
                <span v-if="!s.trades?.length" class="text-xs text-gray-400">—</span>
              </div>
            </td>
            <td class="text-gray-600">{{ s.phone }}</td>
            <td class="text-gray-600">{{ s.city || '—' }}</td>
            <td>
              <span v-if="s.active_jobs_count" class="badge-amber">{{ s.active_jobs_count }}</span>
              <span v-else class="text-xs text-gray-400">0</span>
            </td>
            <td>
              <div v-if="s.rating" class="flex items-center gap-1">
                <Star :size="12" class="text-amber-400 fill-amber-400" />
                <span class="text-sm text-gray-700">{{ s.rating }}</span>
              </div>
              <span v-else class="text-xs text-gray-400">—</span>
            </td>
            <td>
              <span :class="s.is_active ? 'badge-green' : 'badge-gray'">
                {{ s.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
              <button
                @click.stop="openEdit(s)"
                class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              >
                <Pencil :size="14" />
              </button>
            </td>
          </tr>
          <tr v-if="!filteredSuppliers.length">
            <td colspan="8" class="text-center text-gray-400 py-10">No suppliers found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create / Edit Dialog -->
    <Teleport to="body">
      <div v-if="dialog" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="dialog = false" />
        <div class="relative card w-full max-w-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-2">
            <h2 class="font-semibold text-gray-900">{{ editing ? 'Edit Supplier' : 'Add Supplier' }}</h2>
            <button @click="dialog = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <!-- Core info -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Contact person *</label>
              <input v-model="form.name" class="input" placeholder="John Smith" required />
            </div>
            <div>
              <label class="label">Company name</label>
              <input v-model="form.company_name" class="input" placeholder="Smith Plumbing" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Phone *</label>
              <input v-model="form.phone" class="input" placeholder="082 123 4567" required />
            </div>
            <div>
              <label class="label">Email</label>
              <input v-model="form.email" class="input" type="email" placeholder="john@example.com" />
            </div>
          </div>

          <!-- Trades -->
          <div>
            <label class="label">Trades</label>
            <div class="flex flex-wrap gap-2 mt-1">
              <button
                v-for="t in tradeOptions"
                :key="t.value"
                type="button"
                @click="toggleTrade(t.value)"
                class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors border"
                :class="form.trade_codes.includes(t.value)
                  ? 'bg-navy text-white border-navy'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'"
              >
                {{ t.label }}
              </button>
            </div>
          </div>

          <!-- Address -->
          <div class="border-t border-gray-100 pt-4">
            <h3 class="text-sm font-medium text-gray-700 mb-3">Address</h3>
            <div>
              <label class="label">Street address</label>
              <input v-model="form.address" class="input" placeholder="123 Main Road, Parow" />
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label class="label">City</label>
                <input v-model="form.city" class="input" placeholder="Cape Town" />
              </div>
              <div>
                <label class="label">Province</label>
                <input v-model="form.province" class="input" placeholder="Western Cape" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label class="label">Service radius (km)</label>
                <input v-model.number="form.service_radius_km" class="input" type="number" placeholder="50" />
              </div>
              <div></div>
            </div>

            <!-- Google Maps address lookup -->
            <div class="mt-3">
              <button
                type="button"
                @click="geocodeAddress"
                :disabled="!form.address || geocoding"
                class="text-xs text-navy hover:underline disabled:opacity-40 disabled:no-underline flex items-center gap-1"
              >
                <MapPin :size="12" />
                {{ geocoding ? 'Looking up…' : 'Look up on Google Maps' }}
              </button>
              <div v-if="form.latitude && form.longitude" class="mt-2 text-xs text-gray-500">
                Coordinates: {{ form.latitude }}, {{ form.longitude }}
              </div>
            </div>
          </div>

          <!-- Compliance -->
          <div class="border-t border-gray-100 pt-4">
            <h3 class="text-sm font-medium text-gray-700 mb-3">Compliance</h3>
            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="label">BEE Level</label>
                <input v-model="form.bee_level" class="input" placeholder="Level 1" />
              </div>
              <div>
                <label class="label">CIDB Grading</label>
                <input v-model="form.cidb_grading" class="input" placeholder="3CE" />
              </div>
              <div>
                <label class="label">Insurance expiry</label>
                <input v-model="form.insurance_expiry" class="input" type="date" />
              </div>
            </div>
            <div class="mt-3">
              <label class="label">Insurance details</label>
              <textarea v-model="form.insurance_details" class="input" rows="2" placeholder="Policy number, provider…"></textarea>
            </div>
          </div>

          <!-- Banking -->
          <div class="border-t border-gray-100 pt-4">
            <h3 class="text-sm font-medium text-gray-700 mb-3">Banking</h3>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label">Bank name</label>
                <input v-model="form.bank_name" class="input" placeholder="FNB" />
              </div>
              <div>
                <label class="label">Account type</label>
                <select v-model="form.account_type" class="input">
                  <option value="">—</option>
                  <option value="cheque">Cheque</option>
                  <option value="savings">Savings</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label class="label">Account number</label>
                <input v-model="form.account_number" class="input" placeholder="62012345678" />
              </div>
              <div>
                <label class="label">Branch code</label>
                <input v-model="form.branch_code" class="input" placeholder="250655" />
              </div>
            </div>
          </div>

          <!-- Notes -->
          <div class="border-t border-gray-100 pt-4">
            <label class="label">Notes</label>
            <textarea v-model="form.notes" class="input" rows="3" placeholder="Additional notes…"></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="dialog = false">Cancel</button>
            <button class="btn-primary" :disabled="saving || !form.name || !form.phone" @click="saveSupplier">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              {{ editing ? 'Save Changes' : 'Create Supplier' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Detail slide-over -->
    <Teleport to="body">
      <div v-if="detailSupplier" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-black/30" @click="detailSupplier = null" />
        <div class="relative w-full max-w-lg bg-white shadow-xl overflow-y-auto">
          <div class="p-6 space-y-5">
            <div class="flex items-start justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-900">{{ detailSupplier.company_name || detailSupplier.name }}</h2>
                <p v-if="detailSupplier.company_name" class="text-sm text-gray-500">{{ detailSupplier.name }}</p>
              </div>
              <button @click="detailSupplier = null" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
            </div>

            <div class="flex flex-wrap gap-1.5">
              <span v-for="t in detailSupplier.trades" :key="t.id"
                class="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                {{ t.label }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-gray-400 text-xs">Phone</span>
                <p class="text-gray-800">{{ detailSupplier.phone }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Email</span>
                <p class="text-gray-800">{{ detailSupplier.email || '—' }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">City</span>
                <p class="text-gray-800">{{ detailSupplier.city || '—' }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Rating</span>
                <p class="text-gray-800 flex items-center gap-1">
                  <Star v-if="detailSupplier.rating" :size="12" class="text-amber-400 fill-amber-400" />
                  {{ detailSupplier.rating ?? '—' }}
                </p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">BEE Level</span>
                <p class="text-gray-800">{{ detailSupplier.bee_level || '—' }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">CIDB Grading</span>
                <p class="text-gray-800">{{ detailSupplier.cidb_grading || '—' }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Active Jobs</span>
                <p class="text-gray-800">{{ detailSupplier.active_jobs_count ?? 0 }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Status</span>
                <span :class="detailSupplier.is_active ? 'badge-green' : 'badge-gray'">
                  {{ detailSupplier.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
            </div>

            <div v-if="detailSupplier.notes" class="border-t border-gray-100 pt-4">
              <span class="text-gray-400 text-xs">Notes</span>
              <p class="text-sm text-gray-700 mt-1 whitespace-pre-line">{{ detailSupplier.notes }}</p>
            </div>

            <div class="flex gap-2 pt-4 border-t border-gray-100">
              <button class="btn-primary flex-1" @click="openEdit(detailSupplier); detailSupplier = null">
                <Pencil :size="14" /> Edit
              </button>
              <button class="btn-ghost text-red-600 hover:bg-red-50" @click="deleteSupplier(detailSupplier)">
                <Trash2 :size="14" /> Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { Plus, Search, X, Loader2, Pencil, Star, Trash2, MapPin } from 'lucide-vue-next'

const loading = ref(true)
const saving = ref(false)
const geocoding = ref(false)
const search = ref('')
const dialog = ref(false)
const editing = ref<number | null>(null)
const activeFilter = ref('all')
const suppliers = ref<any[]>([])
const detailSupplier = ref<any | null>(null)

const statusFilters = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
]

const tradeOptions = [
  { value: 'plumbing', label: 'Plumbing' },
  { value: 'electrical', label: 'Electrical' },
  { value: 'carpentry', label: 'Carpentry' },
  { value: 'painting', label: 'Painting' },
  { value: 'roofing', label: 'Roofing' },
  { value: 'hvac', label: 'HVAC' },
  { value: 'locksmith', label: 'Locksmith' },
  { value: 'pest_control', label: 'Pest Control' },
  { value: 'landscaping', label: 'Landscaping' },
  { value: 'appliance', label: 'Appliance Repair' },
  { value: 'general', label: 'General' },
  { value: 'security', label: 'Security' },
  { value: 'cleaning', label: 'Cleaning' },
  { value: 'other', label: 'Other' },
]

const emptyForm = () => ({
  name: '', company_name: '', phone: '', email: '',
  address: '', city: '', province: '',
  latitude: null as number | null, longitude: null as number | null,
  service_radius_km: null as number | null,
  bee_level: '', cidb_grading: '', insurance_expiry: '', insurance_details: '',
  bank_name: '', account_number: '', branch_code: '', account_type: '',
  notes: '', trade_codes: [] as string[],
})

const form = ref(emptyForm())

onMounted(() => loadSuppliers())

async function loadSuppliers() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (activeFilter.value === 'active') params.is_active = true
    if (activeFilter.value === 'inactive') params.is_active = false
    const { data } = await api.get('/maintenance/suppliers/', { params })
    suppliers.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

const filteredSuppliers = computed(() =>
  suppliers.value.filter(s => {
    const q = search.value.toLowerCase()
    return s.name.toLowerCase().includes(q) ||
      (s.company_name ?? '').toLowerCase().includes(q) ||
      (s.phone ?? '').includes(q)
  })
)

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  dialog.value = true
}

function openEdit(s: any) {
  editing.value = s.id
  form.value = {
    name: s.name, company_name: s.company_name ?? '', phone: s.phone, email: s.email ?? '',
    address: s.address ?? '', city: s.city ?? '', province: s.province ?? '',
    latitude: s.latitude, longitude: s.longitude,
    service_radius_km: s.service_radius_km,
    bee_level: s.bee_level ?? '', cidb_grading: s.cidb_grading ?? '',
    insurance_expiry: s.insurance_expiry ?? '', insurance_details: s.insurance_details ?? '',
    bank_name: s.bank_name ?? '', account_number: s.account_number ?? '',
    branch_code: s.branch_code ?? '', account_type: s.account_type ?? '',
    notes: s.notes ?? '',
    trade_codes: s.trades?.map((t: any) => t.trade) ?? [],
  }
  dialog.value = true
}

function openDetail(s: any) {
  detailSupplier.value = s
}

function toggleTrade(code: string) {
  const idx = form.value.trade_codes.indexOf(code)
  if (idx >= 0) form.value.trade_codes.splice(idx, 1)
  else form.value.trade_codes.push(code)
}

async function saveSupplier() {
  if (!form.value.name || !form.value.phone) return
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.insurance_expiry) (payload as any).insurance_expiry = null
    if (!payload.service_radius_km) (payload as any).service_radius_km = null

    if (editing.value) {
      await api.patch(`/maintenance/suppliers/${editing.value}/`, payload)
    } else {
      await api.post('/maintenance/suppliers/', payload)
    }
    dialog.value = false
    form.value = emptyForm()
    await loadSuppliers()
  } finally {
    saving.value = false
  }
}

async function deleteSupplier(s: any) {
  if (!confirm(`Delete ${s.company_name || s.name}? This cannot be undone.`)) return
  await api.delete(`/maintenance/suppliers/${s.id}/`)
  detailSupplier.value = null
  await loadSuppliers()
}

async function geocodeAddress() {
  if (!form.value.address) return
  geocoding.value = true
  try {
    const q = [form.value.address, form.value.city, form.value.province].filter(Boolean).join(', ')
    const resp = await fetch(
      `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(q)}&key=${import.meta.env.VITE_GOOGLE_MAPS_KEY || ''}`
    )
    const data = await resp.json()
    if (data.results?.[0]) {
      const loc = data.results[0].geometry.location
      form.value.latitude = loc.lat
      form.value.longitude = loc.lng
    }
  } finally {
    geocoding.value = false
  }
}
</script>
