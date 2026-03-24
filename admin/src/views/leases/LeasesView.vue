<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-gray-900">Leases</h1>
      <button class="btn-primary" @click="openCreateDialog">
        <Plus :size="15" /> New Lease
      </button>
    </div>

    <div class="card">
      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>
      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Tenant</th>
            <th>Property / Unit</th>
            <th>Period</th>
            <th>Rent</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lease in leases" :key="lease.id">
            <td class="font-medium text-gray-900">{{ lease.tenant_name }}</td>
            <td class="text-gray-600">{{ lease.unit_label }}</td>
            <td class="text-xs text-gray-500">{{ formatDate(lease.start_date) }} → {{ formatDate(lease.end_date) }}</td>
            <td class="font-medium text-gray-800">R{{ Number(lease.monthly_rent).toLocaleString() }}</td>
            <td><span :class="statusBadge(lease.status)">{{ lease.status }}</span></td>
            <td>
              <button @click="openDocs(lease)" class="p-1.5 text-gray-400 hover:text-navy rounded-lg hover:bg-gray-100 transition-colors" title="Documents">
                <Paperclip :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="!leases.length">
            <td colspan="6" class="text-center text-gray-400 py-10">No leases found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Documents Drawer -->
    <Teleport to="body">
      <div v-if="docsDrawer" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="docsDrawer = false" />
        <div class="relative bg-white w-full max-w-sm shadow-xl flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <div>
              <div class="font-semibold text-gray-900 text-sm">Documents</div>
              <div class="text-xs text-gray-500">{{ selectedLease?.tenant_name }}</div>
            </div>
            <button @click="docsDrawer = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <div class="flex-1 overflow-y-auto p-5 space-y-4">
            <!-- Upload -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Upload Document</h3>
              <div>
                <label class="label">Type</label>
                <select v-model="uploadType" class="input">
                  <option value="signed_lease">Signed Lease</option>
                  <option value="id_copy">ID Copy</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label class="label">Description (optional)</label>
                <input v-model="uploadDescription" class="input" placeholder="e.g. John Smith ID" />
              </div>
              <div>
                <label class="label">File</label>
                <input
                  ref="fileInputRef"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  class="input file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-navy file:text-white hover:file:bg-navy-dark"
                  @change="onFileChange"
                />
              </div>
              <button
                class="btn-primary w-full justify-center"
                :disabled="!uploadFile || uploading"
                @click="uploadDocument"
              >
                <Loader2 v-if="uploading" :size="14" class="animate-spin" />
                {{ uploading ? 'Uploading…' : 'Upload' }}
              </button>
            </div>

            <!-- Doc list -->
            <div>
              <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Attached</h3>
              <div v-if="docsLoading" class="space-y-2 animate-pulse">
                <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-lg"></div>
              </div>
              <div v-else class="space-y-2">
                <div v-for="doc in documents" :key="doc.id" class="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div>
                    <span :class="docTypeBadge(doc.document_type)" class="mb-1 inline-block">
                      {{ doc.document_type.replace('_', ' ') }}
                    </span>
                    <div class="text-xs text-gray-500">{{ doc.description || formatDate(doc.uploaded_at) }}</div>
                  </div>
                  <a :href="doc.file_url" target="_blank" class="p-1.5 text-navy hover:bg-navy/10 rounded-lg transition-colors">
                    <Download :size="15" />
                  </a>
                </div>
                <div v-if="!documents.length" class="text-center text-gray-400 py-6 text-sm">No documents yet</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Create Lease Dialog -->
    <Teleport to="body">
      <div v-if="createDialog" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="createDialog = false" />
        <div class="relative card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="font-semibold text-gray-900">New Lease</h2>
            <div class="flex items-center gap-2">
              <!-- Parse with AI -->
              <button
                class="btn-ghost text-xs px-3 py-1.5"
                :disabled="parsing"
                @click="aiParseInput?.click()"
              >
                <Loader2 v-if="parsing" :size="13" class="animate-spin" />
                <Sparkles v-else :size="13" class="text-pink-brand" />
                {{ parsing ? 'Parsing…' : 'Parse with AI' }}
              </button>
              <input ref="aiParseInput" type="file" accept=".pdf" class="hidden" @change="parseWithAI" />
              <button @click="createDialog = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
            </div>
          </div>

          <!-- AI parse status -->
          <div v-if="parseError" class="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
            <AlertCircle :size="15" class="text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <div class="font-medium text-red-700">Parse failed</div>
              <div class="text-red-600 text-xs mt-0.5 font-mono whitespace-pre-wrap">{{ parseError }}</div>
            </div>
          </div>
          <div v-if="parseSuccess" class="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
            <CheckCircle2 :size="15" />
            {{ parseSuccess }}
          </div>

          <!-- Form -->
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="label">Unit</label>
              <select v-model="newLease.unit" class="input">
                <option value="" disabled>Select unit…</option>
                <option v-for="u in units" :key="u.id" :value="u.id">{{ u.label }}</option>
              </select>
            </div>
            <div class="col-span-2">
              <label class="label">Tenant</label>
              <select v-model="newLease.tenant" class="input">
                <option value="" disabled>Select tenant…</option>
                <option v-for="t in tenants" :key="t.id" :value="t.id">{{ t.full_name || t.email }}</option>
              </select>
            </div>
            <div>
              <label class="label">Start date</label>
              <input v-model="newLease.start_date" type="date" class="input" />
            </div>
            <div>
              <label class="label">End date</label>
              <input v-model="newLease.end_date" type="date" class="input" />
            </div>
            <div>
              <label class="label">Monthly rent (R)</label>
              <input v-model="newLease.monthly_rent" type="number" class="input" placeholder="5000" />
            </div>
            <div>
              <label class="label">Deposit (R)</label>
              <input v-model="newLease.deposit" type="number" class="input" placeholder="5000" />
            </div>
            <div class="col-span-2">
              <label class="label">Payment reference</label>
              <input v-model="newLease.payment_reference" class="input" placeholder="18 Irene - Smith" />
            </div>
            <div>
              <label class="label">Max occupants</label>
              <input v-model="newLease.max_occupants" type="number" class="input" />
            </div>
            <div class="flex items-end gap-4 pb-1">
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input v-model="newLease.water_included" type="checkbox" class="rounded" />
                Water included
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input v-model="newLease.electricity_prepaid" type="checkbox" class="rounded" />
                Prepaid elec.
              </label>
            </div>
          </div>

          <!-- AI extracted data preview -->
          <div v-if="parsedData" class="pt-2 border-t border-gray-100 space-y-3">
            <!-- Primary tenant -->
            <div>
              <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Primary Tenant</div>
              <div class="grid grid-cols-2 gap-2 text-sm">
                <div class="p-2 bg-gray-50 rounded-lg">
                  <div class="text-xs text-gray-400">Name</div>
                  <div class="font-medium text-gray-800">{{ parsedData.primary_tenant?.full_name || '—' }}</div>
                </div>
                <div class="p-2 bg-gray-50 rounded-lg">
                  <div class="text-xs text-gray-400">ID Number</div>
                  <div class="font-medium text-gray-800 font-mono text-xs">{{ parsedData.primary_tenant?.id_number || '—' }}</div>
                </div>
                <div class="p-2 bg-gray-50 rounded-lg">
                  <div class="text-xs text-gray-400">Phone</div>
                  <div class="font-medium text-gray-800">{{ parsedData.primary_tenant?.phone || '—' }}</div>
                </div>
                <div class="p-2 bg-gray-50 rounded-lg">
                  <div class="text-xs text-gray-400">Email</div>
                  <div class="font-medium text-gray-800 text-xs truncate">{{ parsedData.primary_tenant?.email || '—' }}</div>
                </div>
              </div>
            </div>
            <!-- Co-tenants -->
            <div v-if="parsedData.co_tenants?.length">
              <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Co-Tenants (jointly liable)
              </div>
              <div v-for="(ct, i) in parsedData.co_tenants" :key="i" class="p-2 bg-blue-50 border border-blue-100 rounded-lg text-sm mb-1.5">
                <div class="font-medium text-gray-800">{{ ct.full_name }}</div>
                <div class="text-xs text-gray-500 mt-0.5 font-mono">{{ ct.id_number || '—' }} · {{ ct.phone || '—' }}</div>
              </div>
            </div>
            <!-- Occupants -->
            <div v-if="parsedData.occupants?.length">
              <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Occupants</div>
              <div v-for="(oc, i) in parsedData.occupants" :key="i" class="p-2 bg-emerald-50 border border-emerald-100 rounded-lg text-sm mb-1.5">
                <div class="font-medium text-gray-800">{{ oc.full_name }}
                  <span v-if="oc.relationship_to_tenant" class="ml-1 text-xs text-gray-400">({{ oc.relationship_to_tenant }})</span>
                </div>
              </div>
            </div>
            <!-- Guardians -->
            <div v-if="parsedData.guardians?.length">
              <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Guardians / Sureties</div>
              <div v-for="(g, i) in parsedData.guardians" :key="i" class="p-2 bg-amber-50 border border-amber-100 rounded-lg text-sm mb-1.5">
                <div class="font-medium text-gray-800">{{ g.full_name }}</div>
                <div class="text-xs text-gray-500">For: {{ g.for_tenant }}</div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="createDialog = false">Cancel</button>
            <button class="btn-primary" :disabled="saving" @click="createLease">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              Create Lease
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
import { Plus, Paperclip, X, Download, Loader2, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-vue-next'

const loading = ref(true)
const saving = ref(false)
const leases = ref<any[]>([])
const units = ref<any[]>([])
const tenants = ref<any[]>([])

// Documents drawer
const docsDrawer = ref(false)
const docsLoading = ref(false)
const uploading = ref(false)
const selectedLease = ref<any>(null)
const documents = ref<any[]>([])
const uploadFile = ref<File | null>(null)
const uploadType = ref('signed_lease')
const uploadDescription = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

// Create dialog
const createDialog = ref(false)
const newLease = ref({
  unit: '', tenant: '', start_date: '', end_date: '',
  monthly_rent: '', deposit: '', payment_reference: '',
  max_occupants: 4, water_included: true, electricity_prepaid: true,
})

// AI parsing
const parsing = ref(false)
const parsedData = ref<any>(null)
const parseError = ref('')
const parseSuccess = ref('')
const aiParseInput = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  await Promise.all([loadLeases(), loadUnits(), loadTenants()])
})

async function loadLeases() {
  loading.value = true
  try {
    const { data } = await api.get('/leases/')
    leases.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function loadUnits() {
  const { data } = await api.get('/properties/units/')
  units.value = (data.results ?? data).map((u: any) => ({
    ...u,
    label: `${u.property_name ?? u.property} — Unit ${u.unit_number}`,
  }))
}

async function loadTenants() {
  const { data } = await api.get('/auth/tenants/')
  tenants.value = data.results ?? data
}

function openCreateDialog() {
  parsedData.value = null
  parseError.value = ''
  parseSuccess.value = ''
  createDialog.value = true
}

async function openDocs(lease: any) {
  selectedLease.value = lease
  docsDrawer.value = true
  docsLoading.value = true
  try {
    const { data } = await api.get(`/leases/${lease.id}/documents/`)
    documents.value = data
  } finally {
    docsLoading.value = false
  }
}

function onFileChange(e: Event) {
  uploadFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function uploadDocument() {
  if (!uploadFile.value || !selectedLease.value) return
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', uploadFile.value)
    form.append('document_type', uploadType.value)
    form.append('description', uploadDescription.value)
    const { data } = await api.post(`/leases/${selectedLease.value.id}/documents/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    documents.value.unshift(data)
    uploadFile.value = null
    uploadDescription.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
  } finally {
    uploading.value = false
  }
}

async function createLease() {
  saving.value = true
  try {
    await api.post('/leases/', {
      ...newLease.value,
      ...(parsedData.value ? { ai_parse_result: parsedData.value } : {}),
    })
    createDialog.value = false
    parsedData.value = null
    await loadLeases()
  } finally {
    saving.value = false
  }
}

async function parseWithAI(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  parsing.value = true
  parseError.value = ''
  parseSuccess.value = ''
  parsedData.value = null

  try {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/leases/parse-document/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    parsedData.value = data

    if (data.monthly_rent)        newLease.value.monthly_rent = data.monthly_rent
    if (data.deposit)             newLease.value.deposit = data.deposit
    if (data.start_date)          newLease.value.start_date = data.start_date
    if (data.end_date)            newLease.value.end_date = data.end_date
    if (data.payment_reference)   newLease.value.payment_reference = data.payment_reference
    if (data.max_occupants)       newLease.value.max_occupants = data.max_occupants
    if (data.water_included != null)      newLease.value.water_included = data.water_included
    if (data.electricity_prepaid != null) newLease.value.electricity_prepaid = data.electricity_prepaid

    parseSuccess.value = 'Fields extracted — select the Unit and Tenant above to complete.'
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.response?.data ?? e?.message ?? 'Unknown error'
    parseError.value = typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2)
  } finally {
    parsing.value = false
    input.value = ''
  }
}

function statusBadge(s: string) {
  return { active: 'badge-green', pending: 'badge-amber', expired: 'badge-red', terminated: 'badge-gray' }[s] ?? 'badge-gray'
}
function docTypeBadge(t: string) {
  return { signed_lease: 'badge-purple', id_copy: 'badge-blue', other: 'badge-gray' }[t] ?? 'badge-gray'
}
function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA') : '—'
}
</script>
