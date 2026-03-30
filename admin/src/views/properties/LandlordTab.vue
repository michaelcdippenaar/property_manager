<template>
  <div class="space-y-5">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-12 text-gray-400 text-sm">
      <Loader2 :size="16" class="animate-spin mr-2" /> Loading...
    </div>

    <!-- No ownership yet -->
    <div v-else-if="!ownership" class="text-center py-12 space-y-3">
      <UserCircle :size="32" class="mx-auto text-gray-300" />
      <p class="text-sm text-gray-500">No landlord information set for this property.</p>
      <button class="btn-primary btn-sm" @click="createNew">Set Up Landlord</button>
    </div>

    <!-- Ownership form -->
    <form v-else class="space-y-5" @submit.prevent="save">
      <!-- Owner entity -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Owner Entity</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="label">Owner name</label>
            <input v-model="form.owner_name" class="input" placeholder="e.g. Klikk Pty Ltd" />
          </div>
          <div>
            <label class="label">Entity type</label>
            <select v-model="form.owner_type" class="input">
              <option value="individual">Individual</option>
              <option value="company">Company</option>
              <option value="trust">Trust</option>
            </select>
          </div>
          <div>
            <label class="label">{{ form.owner_type === 'individual' ? 'SA ID / Passport' : 'Registration no.' }}</label>
            <input v-model="form.registration_number" class="input font-mono" />
          </div>
          <div v-if="form.owner_type !== 'individual'">
            <label class="label">VAT number</label>
            <input v-model="form.vat_number" class="input font-mono" />
          </div>
          <div>
            <label class="label">Email</label>
            <input v-model="form.owner_email" type="email" class="input" />
          </div>
          <div>
            <label class="label">Phone</label>
            <input v-model="form.owner_phone" class="input" />
          </div>
        </div>
      </div>

      <!-- Owner address -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Owner Address <span class="font-normal text-gray-400 normal-case">(domicilium)</span></div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="label">Street</label>
            <input v-model="form.owner_address.street" class="input" placeholder="123 Main Road" />
          </div>
          <div>
            <label class="label">City</label>
            <input v-model="form.owner_address.city" class="input" />
          </div>
          <div>
            <label class="label">Province</label>
            <input v-model="form.owner_address.province" class="input" />
          </div>
          <div>
            <label class="label">Postal code</label>
            <input v-model="form.owner_address.postal_code" class="input font-mono" />
          </div>
        </div>
      </div>

      <!-- Representative -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Representative <span class="font-normal text-gray-400 normal-case">(signs leases)</span></div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="label">Full name</label>
            <input v-model="form.representative_name" class="input" placeholder="e.g. MC Dippenaar" />
          </div>
          <div>
            <label class="label">SA ID / Passport</label>
            <input v-model="form.representative_id_number" class="input font-mono" />
          </div>
          <div>
            <label class="label">Phone</label>
            <input v-model="form.representative_phone" class="input" />
          </div>
          <div class="col-span-2">
            <label class="label">Email</label>
            <input v-model="form.representative_email" type="email" class="input" />
          </div>
        </div>
      </div>

      <!-- Bank details -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Bank Details</div>
        <p class="text-xs text-gray-400 -mt-1">Populated in lease payment clauses.</p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Bank name</label>
            <input v-model="form.bank_details.bank_name" class="input" placeholder="e.g. FNB" />
          </div>
          <div>
            <label class="label">Branch code</label>
            <input v-model="form.bank_details.branch_code" class="input font-mono" placeholder="250655" />
          </div>
          <div>
            <label class="label">Account number</label>
            <input v-model="form.bank_details.account_number" class="input font-mono" />
          </div>
          <div>
            <label class="label">Account type</label>
            <select v-model="form.bank_details.account_type" class="input">
              <option value="">Select...</option>
              <option value="cheque">Cheque / Current</option>
              <option value="savings">Savings</option>
              <option value="transmission">Transmission</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="label">Account holder</label>
            <input v-model="form.bank_details.account_holder" class="input" :placeholder="form.owner_name || 'Account holder name'" />
          </div>
        </div>
      </div>

      <!-- Ownership period -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Ownership Period</div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Start date</label>
            <input v-model="form.start_date" type="date" class="input" />
          </div>
          <div>
            <label class="label">End date <span class="text-gray-400 font-normal">(leave blank if current)</span></label>
            <input v-model="form.end_date" type="date" class="input" />
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-between pt-2">
        <div>
          <span
            v-if="saved"
            class="text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full"
          >
            Saved
          </span>
          <span v-if="error" class="text-xs text-red-600">{{ error }}</span>
        </div>
        <button type="submit" class="btn-primary" :disabled="saving">
          <Loader2 v-if="saving" :size="14" class="animate-spin mr-1.5" />
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </form>

    <!-- Ownership history -->
    <div v-if="history.length > 1" class="space-y-2 pt-4 border-t border-gray-100">
      <div class="text-xs font-semibold uppercase tracking-wide text-gray-400">Ownership History</div>
      <div
        v-for="h in history"
        :key="h.id"
        class="flex items-center justify-between text-xs p-3 rounded-lg"
        :class="h.is_current ? 'bg-navy/5 border border-navy/10' : 'bg-gray-50'"
      >
        <div>
          <span class="font-medium text-gray-900">{{ h.owner_name }}</span>
          <span v-if="h.representative_name" class="text-gray-500 ml-1">({{ h.representative_name }})</span>
        </div>
        <div class="text-gray-400">
          {{ h.start_date }} — {{ h.end_date || 'present' }}
          <span v-if="h.is_current" class="ml-1 text-emerald-600 font-medium">current</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Loader2, UserCircle } from 'lucide-vue-next'
import api from '../../api'

const props = defineProps<{ propertyId: number }>()

const loading = ref(true)
const saving  = ref(false)
const saved   = ref(false)
const error   = ref('')

const ownership = ref<any>(null)
const history   = ref<any[]>([])

const emptyForm = () => ({
  owner_name: '',
  owner_type: 'company' as string,
  registration_number: '',
  vat_number: '',
  owner_email: '',
  owner_phone: '',
  owner_address: { street: '', city: '', province: '', postal_code: '' },
  representative_name: '',
  representative_id_number: '',
  representative_email: '',
  representative_phone: '',
  bank_details: { bank_name: '', branch_code: '', account_number: '', account_type: '', account_holder: '' },
  start_date: new Date().toISOString().slice(0, 10),
  end_date: '',
  is_current: true,
})

const form = ref(emptyForm())

async function load() {
  loading.value = true
  try {
    // Get current ownership
    try {
      const { data } = await api.get(`/properties/ownerships/current/${props.propertyId}/`)
      ownership.value = data
      populateForm(data)
    } catch (e: any) {
      if (e?.response?.status === 404) {
        ownership.value = null
      }
    }

    // Get full history
    const { data: list } = await api.get(`/properties/ownerships/?property=${props.propertyId}`)
    history.value = list.results ?? list
  } finally {
    loading.value = false
  }
}

function populateForm(data: any) {
  form.value = {
    owner_name: data.owner_name || '',
    owner_type: data.owner_type || 'company',
    registration_number: data.registration_number || '',
    vat_number: data.vat_number || '',
    owner_email: data.owner_email || '',
    owner_phone: data.owner_phone || '',
    owner_address: { street: '', city: '', province: '', postal_code: '', ...(data.owner_address || {}) },
    representative_name: data.representative_name || '',
    representative_id_number: data.representative_id_number || '',
    representative_email: data.representative_email || '',
    representative_phone: data.representative_phone || '',
    bank_details: { bank_name: '', branch_code: '', account_number: '', account_type: '', account_holder: '', ...(data.bank_details || {}) },
    start_date: data.start_date || new Date().toISOString().slice(0, 10),
    end_date: data.end_date || '',
    is_current: data.is_current ?? true,
  }
}

function createNew() {
  ownership.value = { _new: true }
  form.value = emptyForm()
}

async function save() {
  error.value = ''
  saving.value = true
  saved.value = false
  try {
    const payload = {
      ...form.value,
      property: props.propertyId,
      end_date: form.value.end_date || null,
    }

    if (ownership.value?._new || !ownership.value?.id) {
      const { data } = await api.post('/properties/ownerships/', payload)
      ownership.value = data
    } else {
      const { data } = await api.patch(`/properties/ownerships/${ownership.value.id}/`, payload)
      ownership.value = data
    }

    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)

    // Refresh history
    const { data: list } = await api.get(`/properties/ownerships/?property=${props.propertyId}`)
    history.value = list.results ?? list
  } catch (e: any) {
    const detail = e?.response?.data
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    saving.value = false
  }
}

watch(() => props.propertyId, () => { if (props.propertyId) load() })
onMounted(() => { if (props.propertyId) load() })
</script>
