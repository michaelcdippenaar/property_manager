<template>
  <div class="space-y-5">
    <PageHeader
      title="Suppliers"
      subtitle="Manage your approved supplier network and trade specialisations."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Maintenance', to: '/maintenance' }, { label: 'Suppliers' }]"
    >
      <template #actions>
        <div class="flex items-center gap-2 flex-shrink-0">
          <label class="btn-ghost cursor-pointer text-sm">
            <Upload :size="14" /> Import Excel
            <input type="file" accept=".xlsx,.xls" class="hidden" @change="importExcel" />
          </label>
          <button class="btn-primary" @click="openCreate">
            <Plus :size="15" /> Add Supplier
          </button>
        </div>
      </template>
    </PageHeader>

    <FilterPills v-model="activeFilter" :options="tabOptions" @update:modelValue="loadSuppliers()" />

    <!-- Import results banner -->
    <div v-if="importResult" class="card p-4 flex items-center justify-between"
      :class="importResult.errors?.length ? 'bg-warning-50 border-warning-100' : 'bg-success-50 border-success-100'">
      <div class="text-sm">
        <span class="font-medium">{{ importResult.created }} supplier(s) imported.</span>
        <span v-if="importResult.errors?.length" class="text-warning-700 ml-2">
          {{ importResult.errors.length }} error(s): {{ importResult.errors.slice(0, 3).join('; ') }}
        </span>
      </div>
      <button @click="importResult = null" class="text-gray-400 hover:text-gray-600"><X :size="16" /></button>
    </div>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <SearchInput v-model="search" placeholder="Search suppliers…" />
      </div>

      <LoadingState v-if="loading" variant="table" :rows="5" double-row />

      <ErrorState
        v-else-if="loadError"
        :on-retry="loadSuppliers"
        :offline="isOffline"
      />

      <div v-else class="table-scroll"><table class="table-wrap">
        <thead>
          <tr>
            <th>Company</th>
            <th>Address</th>
            <th>Services</th>
            <th>Website</th>
            <th>Docs</th>
            <th>Bank</th>
            <th>Status</th>
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
              <div class="text-sm text-gray-700">{{ s.city || '—' }}</div>
              <div v-if="s.latitude && s.longitude" class="text-micro text-gray-400 mt-0.5 font-mono">
                {{ Number(s.latitude).toFixed(4) }}, {{ Number(s.longitude).toFixed(4) }}
              </div>
            </td>
            <td>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="t in s.trades"
                  :key="t.id"
                  class="inline-flex px-1.5 py-0.5 rounded text-micro font-medium bg-info-50 text-info-700"
                >
                  {{ t.label }}
                </span>
                <span v-if="!s.trades?.length" class="text-xs text-gray-400">—</span>
              </div>
            </td>
            <td>
              <a v-if="s.website" :href="s.website" target="_blank" @click.stop
                class="text-xs text-navy hover:underline truncate block max-w-[140px]">
                {{ s.website.replace(/^https?:\/\//, '').replace(/\/$/, '') }}
              </a>
              <span v-else class="text-xs text-gray-400">—</span>
            </td>
            <td>
              <span v-if="s.document_count" class="badge-blue">{{ s.document_count }}</span>
              <span v-else class="text-xs text-gray-400">0</span>
            </td>
            <td>
              <span v-if="s.has_bank_confirmation" class="badge-green text-micro">Confirmed</span>
              <span v-else class="badge-amber text-micro">Missing</span>
            </td>
            <td>
              <span :class="s.is_active ? 'badge-green' : 'badge-gray'">
                {{ s.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
          </tr>
          <tr v-if="!filteredSuppliers.length">
            <td colspan="7" class="text-center text-gray-400 py-10">No suppliers found</td>
          </tr>
        </tbody>
      </table></div>
    </div>

    <!-- Create / Edit Dialog -->
    <BaseModal :open="dialog" :title="editing ? 'Edit Supplier' : 'Add Supplier'" size="lg" @close="dialog = false">
          <div class="space-y-4">
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
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="label">Phone *</label>
              <input v-model="form.phone" class="input" placeholder="082 123 4567" required />
            </div>
            <div>
              <label class="label">Email</label>
              <input v-model="form.email" class="input" type="email" placeholder="john@example.com" />
            </div>
            <div>
              <label class="label">Website</label>
              <input v-model="form.website" class="input" type="url" placeholder="https://…" />
            </div>
          </div>

          <!-- Trades -->
          <div>
            <label class="label">Services</label>
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
            <AddressAutocomplete input-class="input" @select="onAddressSelect" />
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
            <span v-if="form.latitude && form.longitude" class="text-xs text-gray-400 font-mono mt-2 inline-block">
              {{ form.latitude }}, {{ form.longitude }}
            </span>
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

          <div class="border-t border-gray-100 pt-4">
            <label class="label">Notes</label>
            <textarea v-model="form.notes" class="input" rows="2" placeholder="Additional notes…"></textarea>
          </div>

          </div>

          <template #footer>
            <button class="btn-ghost" @click="dialog = false">Cancel</button>
            <button class="btn-primary" :disabled="saving || !form.name || !form.phone" @click="saveSupplier">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              {{ editing ? 'Save Changes' : 'Create Supplier' }}
            </button>
          </template>
    </BaseModal>

    <!-- Detail slide-over (right panel) -->
    <BaseDrawer :open="!!detail" title="Supplier Details" size="xl" @close="detail = null">
          <div class="p-6 space-y-5">
            <!-- Header -->
            <div class="flex items-start justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-900">{{ detail?.company_name || detail?.name }}</h2>
                <p v-if="detail?.company_name" class="text-sm text-gray-500">{{ detail.name }}</p>
                <div class="flex items-center gap-3 mt-2 text-sm text-gray-600">
                  <span v-if="detail?.phone">{{ detail.phone }}</span>
                  <span v-if="detail?.email">{{ detail.email }}</span>
                </div>
                <a v-if="detail?.website" :href="detail.website" target="_blank"
                  class="text-xs text-navy hover:underline mt-1 inline-block">
                  {{ detail.website }}
                </a>
              </div>
              <div class="flex items-center gap-2">
                <button @click="openEdit(detail); detail = null"
                  class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100">
                  <Pencil :size="14" />
                </button>
              </div>
            </div>

            <!-- Trades -->
            <div class="flex flex-wrap gap-1.5">
              <span v-for="t in detail?.trades" :key="t.id"
                class="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-info-50 text-info-700">
                {{ t.label }}
              </span>
            </div>

            <!-- Address + Map -->
            <div v-if="detail?.city || detail?.address" class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Address</h3>
              <p class="text-sm text-gray-700">{{ detail?.address }}</p>
              <p class="text-sm text-gray-500">{{ [detail?.city, detail?.province].filter(Boolean).join(', ') }}</p>
              <div v-if="detail?.latitude && detail?.longitude" class="mt-3 rounded-lg overflow-hidden border border-gray-200 h-40">
                <iframe
                  :src="`https://www.google.com/maps?q=${detail?.latitude},${detail?.longitude}&z=14&output=embed`"
                  class="w-full h-full border-0" loading="lazy"
                ></iframe>
              </div>
            </div>

            <!-- Documents -->
            <div class="border-t border-gray-100 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Documents</h3>
                <label class="text-xs text-navy hover:underline cursor-pointer flex items-center gap-1">
                  <Upload :size="12" /> Upload
                  <input type="file" class="hidden" @change="uploadDocument" />
                </label>
              </div>
              <div v-if="detailDocs.length" class="space-y-2">
                <div v-for="doc in detailDocs" :key="doc.id"
                  class="flex items-center justify-between p-2 rounded-lg bg-gray-50">
                  <div class="flex items-center gap-2">
                    <FileText :size="14" class="text-gray-400" />
                    <div>
                      <span class="text-xs font-medium text-gray-700">{{ doc.type_label }}</span>
                      <span v-if="doc.description" class="text-xs text-gray-400 ml-1">— {{ doc.description }}</span>
                    </div>
                  </div>
                  <div class="flex items-center gap-1">
                    <a :href="doc.file" target="_blank" class="p-1 text-gray-400 hover:text-navy"><ExternalLink :size="12" /></a>
                    <button @click="deleteDocument(doc)" class="p-1 text-gray-400 hover:text-danger-500"><Trash2 :size="12" /></button>
                  </div>
                </div>
              </div>
              <p v-else class="text-xs text-gray-400">No documents uploaded</p>

              <!-- Quick upload type selector -->
              <div v-if="showDocUpload" class="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
                <select v-model="docUploadType" class="input text-sm">
                  <option v-for="dt in docTypes" :key="dt.value" :value="dt.value">{{ dt.label }}</option>
                </select>
                <input v-model="docUploadDesc" class="input text-sm" placeholder="Description (optional)" />
              </div>
            </div>

            <!-- Bank Details -->
            <div class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Banking</h3>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span class="text-gray-400 text-xs">Bank</span>
                  <p class="text-gray-800">{{ detail?.bank_name || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-400 text-xs">Account</span>
                  <p class="text-gray-800">{{ detail?.account_number || '—' }}</p>
                </div>
              </div>
              <div class="mt-2">
                <span v-if="detail?.has_bank_confirmation" class="badge-green text-xs">Bank confirmation on file</span>
                <span v-else class="badge-amber text-xs">No bank confirmation</span>
              </div>
            </div>

            <!-- Properties -->
            <div class="border-t border-gray-100 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Properties</h3>
                <div class="flex gap-2">
                  <button @click="showGroupAttach = !showGroupAttach"
                    class="text-xs text-navy hover:underline flex items-center gap-1">
                    <Layers :size="12" /> Attach Group
                  </button>
                </div>
              </div>

              <!-- Group attach -->
              <div v-if="showGroupAttach" class="mb-3 p-3 bg-gray-50 rounded-lg space-y-2">
                <div class="flex gap-2">
                  <select v-model="selectedGroupId" class="input text-sm flex-1">
                    <option value="">Select group…</option>
                    <option v-for="g in propertyGroups" :key="g.id" :value="g.id">
                      {{ g.name }} ({{ g.property_count }} properties)
                    </option>
                  </select>
                  <button class="btn-primary text-xs" :disabled="!selectedGroupId" @click="attachGroup">Attach</button>
                </div>
                <button @click="groupDialog = true" class="text-xs text-navy hover:underline">+ Create new group</button>
              </div>

              <!-- Single property attach -->
              <div class="mb-3 flex gap-2">
                <select v-model="selectedPropertyId" class="input text-sm flex-1">
                  <option value="">Attach a property…</option>
                  <option v-for="p in availableProperties" :key="p.id" :value="p.id">
                    {{ p.name }} — {{ p.city }}
                  </option>
                </select>
                <button class="btn-primary text-xs" :disabled="!selectedPropertyId" @click="attachProperty">Add</button>
              </div>

              <div v-if="detailProperties.length" class="space-y-2">
                <div v-for="lnk in detailProperties" :key="lnk.id"
                  class="flex items-center justify-between p-2 rounded-lg bg-gray-50">
                  <div>
                    <span class="text-sm font-medium text-gray-700">{{ lnk.property_name }}</span>
                    <span class="text-xs text-gray-400 ml-2">{{ lnk.property_city }}</span>
                    <span v-if="lnk.is_preferred" class="badge-blue text-micro ml-2">Preferred</span>
                  </div>
                  <button @click="removePropertyLink(lnk)" class="p-1 text-gray-400 hover:text-danger-500"><Trash2 :size="12" /></button>
                </div>
              </div>
              <p v-else class="text-xs text-gray-400">No properties linked</p>
            </div>

            <!-- Compliance -->
            <div class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Compliance</h3>
              <div class="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <span class="text-gray-400 text-xs">BEE</span>
                  <p class="text-gray-800">{{ detail?.bee_level || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-400 text-xs">CIDB</span>
                  <p class="text-gray-800">{{ detail?.cidb_grading || '—' }}</p>
                </div>
                <div>
                  <span class="text-gray-400 text-xs">Rating</span>
                  <p class="text-gray-800 flex items-center gap-1">
                    <Star v-if="detail?.rating" :size="12" class="text-warning-500 fill-warning-500" />
                    {{ detail?.rating ?? '—' }}
                  </p>
                </div>
              </div>
            </div>

            <!-- Delete -->
            <div class="border-t border-gray-100 pt-4">
              <button class="btn-ghost text-danger-600 hover:bg-danger-50 w-full" @click="deleteSupplier(detail)">
                <Trash2 :size="14" /> Delete Supplier
              </button>
            </div>
          </div>
    </BaseDrawer>

    <!-- Property Group create dialog -->
    <BaseModal :open="groupDialog" title="Create Property Group" size="md" @close="groupDialog = false">
          <div class="space-y-4">
          <div>
            <label class="label">Group name</label>
            <input v-model="newGroup.name" class="input" placeholder="e.g. Welgevonden, Premium >R10m" />
          </div>
          <div>
            <label class="label">Description</label>
            <input v-model="newGroup.description" class="input" placeholder="Optional" />
          </div>
          <div>
            <label class="label">Properties</label>
            <div class="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-2 space-y-1 mt-1">
              <label v-for="p in allProperties" :key="p.id" class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 p-1 rounded">
                <input type="checkbox" :value="p.id" v-model="newGroup.property_ids" class="rounded" />
                {{ p.name }} — {{ p.city }}
              </label>
            </div>
          </div>
          </div>
          <template #footer>
            <button class="btn-ghost" @click="groupDialog = false">Cancel</button>
            <button class="btn-primary" :disabled="!newGroup.name" @click="createGroup">Create Group</button>
          </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import {
  Plus, X, Loader2, Pencil, Star, Trash2,
  Upload, FileText, ExternalLink, Layers,
} from 'lucide-vue-next'
import SearchInput from '../../components/SearchInput.vue'
import FilterPills from '../../components/FilterPills.vue'
import BaseDrawer from '../../components/BaseDrawer.vue'
import BaseModal from '../../components/BaseModal.vue'
import AddressAutocomplete, { type AddressResult } from '../../components/AddressAutocomplete.vue'
import PageHeader from '../../components/PageHeader.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'
import { useToast } from '../../composables/useToast'

const toast = useToast()

const loading = ref(true)
const loadError = ref(false)
const isOffline = ref(false)
const saving = ref(false)
const search = ref('')
const dialog = ref(false)
const editing = ref<number | null>(null)
const activeFilter = ref('all')
const suppliers = ref<any[]>([])
const detail = ref<any | null>(null)
const importResult = ref<any | null>(null)

// Detail panel state
const detailDocs = ref<any[]>([])
const detailProperties = ref<any[]>([])
const showDocUpload = ref(false)
const docUploadType = ref('other')
const docUploadDesc = ref('')
const showGroupAttach = ref(false)
const selectedGroupId = ref('')
const selectedPropertyId = ref('')
const allProperties = ref<any[]>([])
const propertyGroups = ref<any[]>([])

// Group dialog
const groupDialog = ref(false)
const newGroup = ref({ name: '', description: '', property_ids: [] as number[] })

const tabOptions = [
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

const docTypes = [
  { value: 'bank_confirmation', label: 'Bank Confirmation' },
  { value: 'bee_certificate', label: 'BEE Certificate' },
  { value: 'insurance', label: 'Insurance Certificate' },
  { value: 'cidb', label: 'CIDB Registration' },
  { value: 'company_reg', label: 'Company Registration' },
  { value: 'tax_clearance', label: 'Tax Clearance' },
  { value: 'other', label: 'Other' },
]

const emptyForm = () => ({
  name: '', company_name: '', phone: '', email: '', website: '',
  address: '', city: '', province: '',
  latitude: null as number | null, longitude: null as number | null,
  service_radius_km: null as number | null,
  bee_level: '', cidb_grading: '', insurance_expiry: '', insurance_details: '',
  bank_name: '', account_number: '', branch_code: '', account_type: '',
  notes: '', trade_codes: [] as string[],
})

const form = ref(emptyForm())

onMounted(async () => {
  await Promise.all([loadSuppliers(), loadAllProperties(), loadPropertyGroups()])
})

async function loadSuppliers() {
  loading.value = true
  loadError.value = false
  isOffline.value = false
  try {
    const params: Record<string, any> = {}
    if (activeFilter.value === 'active') params.is_active = true
    if (activeFilter.value === 'inactive') params.is_active = false
    const { data } = await api.get('/maintenance/suppliers/', { params })
    suppliers.value = data.results ?? data
  } catch (err: any) {
    isOffline.value = !navigator.onLine
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function loadAllProperties() {
  try {
    const { data } = await api.get('/properties/')
    allProperties.value = data.results ?? data
  } catch { /* ignore */ }
}

async function loadPropertyGroups() {
  try {
    const { data } = await api.get('/properties/groups/')
    propertyGroups.value = data.results ?? data
  } catch { /* ignore */ }
}

const filteredSuppliers = computed(() =>
  suppliers.value.filter(s => {
    const q = search.value.toLowerCase()
    return s.name.toLowerCase().includes(q) ||
      (s.company_name ?? '').toLowerCase().includes(q) ||
      (s.phone ?? '').includes(q)
  })
)

const availableProperties = computed(() => {
  const linked = new Set(detailProperties.value.map((l: any) => l.property))
  return allProperties.value.filter((p: any) => !linked.has(p.id))
})

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  dialog.value = true
}

function openEdit(s: any) {
  editing.value = s.id
  form.value = {
    name: s.name, company_name: s.company_name ?? '', phone: s.phone, email: s.email ?? '',
    website: s.website ?? '',
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

async function openDetail(s: any) {
  // Fetch full detail (includes documents, property_links)
  try {
    const { data } = await api.get(`/maintenance/suppliers/${s.id}/`)
    detail.value = data
    detailDocs.value = data.documents ?? []
    detailProperties.value = data.property_links ?? []
    showGroupAttach.value = false
    selectedPropertyId.value = ''
    selectedGroupId.value = ''
  } catch {
    detail.value = s
    detailDocs.value = []
    detailProperties.value = []
  }
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
    if (!payload.latitude) (payload as any).latitude = null
    else (payload as any).latitude = Math.round(payload.latitude * 1e6) / 1e6
    if (!payload.longitude) (payload as any).longitude = null
    else (payload as any).longitude = Math.round(payload.longitude * 1e6) / 1e6

    if (editing.value) {
      await api.patch(`/maintenance/suppliers/${editing.value}/`, payload)
    } else {
      await api.post('/maintenance/suppliers/', payload)
    }
    dialog.value = false
    form.value = emptyForm()
    toast.success('Supplier saved')
    await loadSuppliers()
  } catch (err: any) {
    const data = err.response?.data
    if (data && typeof data === 'object' && !data.detail) {
      const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
      toast.error(msgs.join(' | '))
    } else {
      toast.error(data?.detail || 'Failed to save supplier')
    }
  } finally {
    saving.value = false
  }
}

async function deleteSupplier(s: any) {
  if (!confirm(`Delete ${s.company_name || s.name}? This cannot be undone.`)) return
  await api.delete(`/maintenance/suppliers/${s.id}/`)
  detail.value = null
  await loadSuppliers()
}

// --- Documents ---

async function uploadDocument(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !detail.value) return
  const fd = new FormData()
  fd.append('file', file)
  fd.append('document_type', docUploadType.value)
  fd.append('description', docUploadDesc.value)
  try {
    await api.post(`/maintenance/suppliers/${detail.value.id}/documents/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    docUploadDesc.value = ''
    // Refresh detail
    await openDetail(detail.value)
    await loadSuppliers()
  } catch { /* ignore */ }
  (e.target as HTMLInputElement).value = ''
}

async function deleteDocument(doc: any) {
  if (!detail.value) return
  await api.delete(`/maintenance/suppliers/${detail.value.id}/documents/${doc.id}/`)
  await openDetail(detail.value)
  await loadSuppliers()
}

// --- Property linking ---

async function attachProperty() {
  if (!detail.value || !selectedPropertyId.value) return
  const { data: newLink } = await api.post(`/maintenance/suppliers/${detail.value.id}/properties/`, {
    property: selectedPropertyId.value,
  })
  // Optimistically update so the dropdown removes the linked property immediately
  detailProperties.value = [...detailProperties.value, newLink]
  selectedPropertyId.value = ''
  await openDetail(detail.value)
  await loadSuppliers()
}

async function removePropertyLink(lnk: any) {
  if (!detail.value) return
  await api.delete(`/maintenance/suppliers/${detail.value.id}/properties/${lnk.id}/`)
  await openDetail(detail.value)
  await loadSuppliers()
}

async function attachGroup() {
  if (!detail.value || !selectedGroupId.value) return
  await api.post(`/maintenance/suppliers/${detail.value.id}/attach_group/`, {
    group_id: selectedGroupId.value,
  })
  selectedGroupId.value = ''
  showGroupAttach.value = false
  await openDetail(detail.value)
  await loadSuppliers()
}

// --- Property groups ---

async function createGroup() {
  if (!newGroup.value.name) return
  await api.post('/properties/groups/', newGroup.value)
  newGroup.value = { name: '', description: '', property_ids: [] }
  groupDialog.value = false
  await loadPropertyGroups()
}

// --- Excel import ---

async function importExcel(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const { data } = await api.post('/maintenance/suppliers/import_excel/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    importResult.value = data
    toast.success(`Imported ${data.created} suppliers`)
    await loadSuppliers()
  } catch (err: any) {
    importResult.value = { created: 0, errors: [err.response?.data?.detail || 'Import failed'] }
    toast.error(err.response?.data?.detail || 'Import failed')
  }
  (e.target as HTMLInputElement).value = ''
}

function onAddressSelect(result: AddressResult) {
  form.value.address = result.street || result.formatted
  form.value.city = result.city
  form.value.province = result.province
  form.value.latitude = result.lat
  form.value.longitude = result.lng
}
</script>
