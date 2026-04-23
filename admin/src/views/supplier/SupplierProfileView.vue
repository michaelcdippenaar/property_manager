<template>
  <div class="space-y-5 max-w-3xl">
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card p-5 animate-pulse space-y-3">
        <div class="h-4 bg-gray-100 rounded w-1/3"></div>
        <div class="h-3 bg-gray-100 rounded w-2/3"></div>
      </div>
    </div>

    <div v-else-if="profile" class="space-y-5">
      <!-- Company info -->
      <div class="card p-5 space-y-4">
        <h2 class="text-sm font-medium text-gray-700">Company Information</h2>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label text-xs">Contact person</label>
            <input v-model="profile.name" class="input" />
          </div>
          <div>
            <label class="label text-xs">Company name</label>
            <input v-model="profile.company_name" class="input" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="label text-xs">Phone</label>
            <input v-model="profile.phone" class="input" />
          </div>
          <div>
            <label class="label text-xs">Email</label>
            <input v-model="profile.email" class="input" type="email" />
          </div>
          <div>
            <label class="label text-xs">Website</label>
            <input v-model="profile.website" class="input" type="url" />
          </div>
        </div>
      </div>

      <!-- Address -->
      <div class="card p-5 space-y-4">
        <h2 class="text-sm font-medium text-gray-700">Address</h2>
        <div>
          <input v-model="profile.address" class="input" placeholder="Street address" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div><input v-model="profile.city" class="input" placeholder="City" /></div>
          <div><input v-model="profile.province" class="input" placeholder="Province" /></div>
          <div>
            <input v-model.number="profile.service_radius_km" class="input" type="number" placeholder="Radius (km)" />
          </div>
        </div>
      </div>

      <!-- Trades -->
      <div class="card p-5 space-y-3">
        <h2 class="text-sm font-medium text-gray-700">Services</h2>
        <div class="flex flex-wrap gap-2">
          <button v-for="t in tradeOptions" :key="t.value" type="button"
            @click="toggleTrade(t.value)"
            class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors border"
            :class="selectedTrades.has(t.value) ? 'bg-navy text-white border-navy' : 'bg-white text-gray-600 border-gray-200'">
            {{ t.label }}
          </button>
        </div>
      </div>

      <!-- Banking -->
      <div class="card p-5 space-y-4">
        <h2 class="text-sm font-medium text-gray-700">Banking</h2>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label text-xs">Bank</label><input v-model="profile.bank_name" class="input" /></div>
          <div>
            <label class="label text-xs">Account type</label>
            <select v-model="profile.account_type" class="input">
              <option value="">—</option>
              <option value="cheque">Cheque</option>
              <option value="savings">Savings</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label text-xs">Account number</label><MaskedInput v-model="profile.account_number" class="input" /></div>
          <div><label class="label text-xs">Branch code</label><MaskedInput v-model="profile.branch_code" class="input" /></div>
        </div>
      </div>

      <!-- Documents -->
      <div class="card p-5 space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-medium text-gray-700">Documents</h2>
          <label class="text-xs text-navy hover:underline cursor-pointer flex items-center gap-1">
            <Upload :size="12" /> Upload
            <input type="file" class="hidden" @change="uploadDoc" />
          </label>
        </div>
        <div v-if="docs.length" class="space-y-2">
          <div v-for="d in docs" :key="d.id" class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
            <div class="flex items-center gap-2 text-sm">
              <FileText :size="14" class="text-gray-400" />
              <span class="font-medium text-gray-700">{{ d.type_label }}</span>
              <span v-if="d.description" class="text-gray-400">— {{ d.description }}</span>
            </div>
            <a :href="d.file" target="_blank" class="text-xs text-navy hover:underline">View</a>
          </div>
        </div>
        <p v-else class="text-xs text-gray-400">No documents uploaded</p>

        <div v-if="showUploadForm" class="p-3 bg-gray-50 rounded-lg space-y-2">
          <select v-model="uploadType" class="input text-sm">
            <option value="bank_confirmation">Bank Confirmation</option>
            <option value="bee_certificate">BEE Certificate</option>
            <option value="insurance">Insurance</option>
            <option value="cidb">CIDB Registration</option>
            <option value="company_reg">Company Registration</option>
            <option value="tax_clearance">Tax Clearance</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>

      <!-- Save -->
      <button @click="saveProfile" :disabled="saving" class="btn-primary">
        <Loader2 v-if="saving" :size="14" class="animate-spin" />
        Save Profile
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { Upload, FileText, Loader2 } from 'lucide-vue-next'
import MaskedInput from '../../components/shared/MaskedInput.vue'

const loading = ref(true)
const saving = ref(false)
const profile = ref<any | null>(null)
const docs = ref<any[]>([])
const selectedTrades = ref(new Set<string>())
const showUploadForm = ref(false)
const uploadType = ref('other')

const tradeOptions = [
  { value: 'plumbing', label: 'Plumbing' }, { value: 'electrical', label: 'Electrical' },
  { value: 'carpentry', label: 'Carpentry' }, { value: 'painting', label: 'Painting' },
  { value: 'roofing', label: 'Roofing' }, { value: 'hvac', label: 'HVAC' },
  { value: 'locksmith', label: 'Locksmith' }, { value: 'pest_control', label: 'Pest Control' },
  { value: 'landscaping', label: 'Landscaping' }, { value: 'appliance', label: 'Appliance Repair' },
  { value: 'general', label: 'General' }, { value: 'security', label: 'Security' },
  { value: 'cleaning', label: 'Cleaning' }, { value: 'other', label: 'Other' },
]

onMounted(async () => {
  try {
    const [profileRes, docsRes] = await Promise.all([
      api.get('/maintenance/supplier/profile/'),
      api.get('/maintenance/supplier/documents/'),
    ])
    profile.value = profileRes.data
    docs.value = docsRes.data
    selectedTrades.value = new Set(profile.value.trades?.map((t: any) => t.trade) ?? [])
  } finally {
    loading.value = false
  }
})

function toggleTrade(code: string) {
  if (selectedTrades.value.has(code)) selectedTrades.value.delete(code)
  else selectedTrades.value.add(code)
}

async function saveProfile() {
  if (!profile.value) return
  saving.value = true
  try {
    const payload = { ...profile.value, trade_codes: Array.from(selectedTrades.value) }
    delete payload.trades
    delete payload.documents
    const { data } = await api.patch('/maintenance/supplier/profile/', payload)
    profile.value = data
  } finally {
    saving.value = false
  }
}

async function uploadDoc(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  showUploadForm.value = true
  const fd = new FormData()
  fd.append('file', file)
  fd.append('document_type', uploadType.value)
  try {
    await api.post('/maintenance/supplier/documents/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const { data } = await api.get('/maintenance/supplier/documents/')
    docs.value = data
    showUploadForm.value = false
  } catch { /* ignore */ }
  (e.target as HTMLInputElement).value = ''
}
</script>
