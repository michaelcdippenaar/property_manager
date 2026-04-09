<template>
  <div class="max-w-3xl mx-auto">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Settings :size="20" class="text-navy" />
          Agency Settings
        </h1>
        <p class="text-sm text-gray-400 mt-1">Configure your agency details — these appear on mandates, leases and generated documents.</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-12 justify-center">
      <Loader2 :size="15" class="animate-spin" />
      Loading agency settings...
    </div>

    <!-- Form -->
    <form v-else class="space-y-8" @submit.prevent="save">

      <!-- Agency Details -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Building2 :size="14" class="text-navy" />
            Agency Details
          </h2>
        </div>
        <div class="px-5 py-5 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Registered name <span class="text-red-400">*</span></label>
              <input v-model="form.name" type="text" class="input" required placeholder="e.g. Prestige Properties (Pty) Ltd" />
            </div>
            <div>
              <label class="label">Trading name (t/a)</label>
              <input v-model="form.trading_name" type="text" class="input" placeholder="e.g. Century 21 Stellenbosch" />
              <p class="text-[11px] text-gray-400 mt-1">Shown on documents if different from registered name</p>
            </div>
            <div>
              <label class="label">CIPC registration number</label>
              <input v-model="form.registration_number" type="text" class="input" placeholder="e.g. 2024/123456/07" />
            </div>
            <div>
              <label class="label">VAT number</label>
              <input v-model="form.vat_number" type="text" class="input" placeholder="e.g. 4123456789" />
            </div>
            <div>
              <label class="label">PPRA FFC number</label>
              <input v-model="form.eaab_ffc_number" type="text" class="input" placeholder="e.g. F148660" />
              <p class="text-[11px] text-gray-400 mt-1">Fidelity Fund Certificate number</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Contact Details -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Phone :size="14" class="text-navy" />
            Contact Details
          </h2>
        </div>
        <div class="px-5 py-5 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Contact number</label>
              <input v-model="form.contact_number" type="text" class="input" placeholder="+27..." />
            </div>
            <div>
              <label class="label">Email address</label>
              <input v-model="form.email" type="email" class="input" placeholder="info@agency.co.za" />
            </div>
            <div>
              <label class="label">Website</label>
              <input v-model="form.website" type="url" class="input" placeholder="https://www.agency.co.za" />
            </div>
            <div class="col-span-2">
              <label class="label">Physical address</label>
              <textarea v-model="form.physical_address" rows="2" class="input" placeholder="Street, City, Province, Postal Code" />
            </div>
            <div class="col-span-2">
              <label class="label">Postal address</label>
              <textarea v-model="form.postal_address" rows="2" class="input" placeholder="PO Box / Same as physical" />
            </div>
          </div>
        </div>
      </section>

      <!-- Trust Account -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Landmark :size="14" class="text-navy" />
            Trust Account
          </h2>
        </div>
        <div class="px-5 py-5 space-y-4">
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="label">Bank name</label>
              <input v-model="form.trust_bank_name" type="text" class="input" placeholder="e.g. FNB, Standard Bank" />
            </div>
            <div>
              <label class="label">Account number</label>
              <input v-model="form.trust_account_number" type="text" class="input" placeholder="Trust account number" />
            </div>
            <div>
              <label class="label">Branch code</label>
              <input v-model="form.trust_branch_code" type="text" class="input" placeholder="e.g. 250655" />
            </div>
          </div>
        </div>
      </section>

      <!-- Compliance -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <ShieldCheck :size="14" class="text-navy" />
            Compliance
          </h2>
        </div>
        <div class="px-5 py-5 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Principal agent name</label>
              <input v-model="form.principal_name" type="text" class="input" placeholder="Full name of principal practitioner" />
            </div>
            <div>
              <label class="label">Principal PPRA number</label>
              <input v-model="form.principal_ppra_number" type="text" class="input" placeholder="7-digit registration number" />
            </div>
            <div>
              <label class="label">Auditor name</label>
              <input v-model="form.auditor_name" type="text" class="input" placeholder="Auditing firm name" />
            </div>
            <div>
              <label class="label">Auditor IRBA number</label>
              <input v-model="form.auditor_irba_number" type="text" class="input" placeholder="IRBA practice number" />
            </div>
            <div>
              <label class="label">BEE level</label>
              <select v-model="form.bee_level" class="input">
                <option value="">— Select —</option>
                <option value="Exempt">Exempt (EME)</option>
                <option value="Level 1">Level 1</option>
                <option value="Level 2">Level 2</option>
                <option value="Level 3">Level 3</option>
                <option value="Level 4">Level 4</option>
                <option value="Level 5">Level 5</option>
                <option value="Level 6">Level 6</option>
                <option value="Level 7">Level 7</option>
                <option value="Level 8">Level 8</option>
                <option value="Non-compliant">Non-compliant</option>
              </select>
            </div>
            <div class="flex items-center gap-3 pt-5">
              <label class="relative inline-flex items-center cursor-pointer">
                <input v-model="form.fica_registered" type="checkbox" class="sr-only peer" />
                <div class="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-navy"></div>
              </label>
              <div>
                <span class="text-sm font-medium text-gray-700">FICA registered</span>
                <p class="text-[11px] text-gray-400">Registered as Accountable Institution with FIC</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Financial Cycle -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <CalendarDays :size="14" class="text-navy" />
            Financial Cycle
          </h2>
        </div>
        <div class="px-5 py-5 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Statement date</label>
              <input v-model="form.statement_date" type="text" class="input" placeholder='e.g. "the 5th"' />
              <p class="text-[11px] text-gray-400 mt-1">Day of month statements are issued</p>
            </div>
            <div>
              <label class="label">Disbursement date</label>
              <input v-model="form.disbursement_date" type="text" class="input" placeholder='e.g. "the 7th"' />
              <p class="text-[11px] text-gray-400 mt-1">Day of month owner payouts are made</p>
            </div>
            <div class="col-span-2">
              <label class="label">Information Officer email</label>
              <input v-model="form.information_officer_email" type="email" class="input" placeholder="POPIA information officer" />
              <p class="text-[11px] text-gray-400 mt-1">Required for POPIA compliance — appears on mandate documents</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Logo -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <ImageIcon :size="14" class="text-navy" />
            Branding
          </h2>
        </div>
        <div class="px-5 py-5">
          <label class="label mb-2">Agency logo</label>
          <div class="flex items-center gap-4">
            <div
              class="w-20 h-20 rounded-xl border-2 border-dashed border-gray-200 flex items-center justify-center bg-gray-50 overflow-hidden flex-shrink-0"
            >
              <img v-if="logoPreview" :src="logoPreview" class="w-full h-full object-contain" />
              <ImageIcon v-else :size="24" class="text-gray-300" />
            </div>
            <div>
              <input
                ref="logoInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onLogoChange"
              />
              <button type="button" class="btn-ghost text-xs" @click="($refs.logoInput as HTMLInputElement).click()">
                {{ logoPreview ? 'Change logo' : 'Upload logo' }}
              </button>
              <button
                v-if="logoPreview"
                type="button"
                class="btn-ghost text-xs text-red-500 ml-2"
                @click="removeLogo"
              >
                Remove
              </button>
              <p class="text-[11px] text-gray-400 mt-1">PNG, JPG or SVG. Used on documents and correspondence.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Save -->
      <div class="flex justify-end pb-8">
        <button type="submit" class="btn-primary flex items-center gap-2" :disabled="saving">
          <Loader2 v-if="saving" :size="14" class="animate-spin" />
          <Save v-else :size="14" />
          Save Settings
        </button>
      </div>

    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  Settings, Building2, Landmark, CalendarDays, Image as ImageIcon,
  Save, Loader2, Phone, ShieldCheck,
} from 'lucide-vue-next'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../stores/auth'

const { showToast } = useToast()
const auth = useAuthStore()

const loading  = ref(true)
const saving   = ref(false)
const logoFile = ref<File | null>(null)
const logoPreview = ref<string | null>(null)
const existingId = ref<number | null>(null)

const defaultForm = () => ({
  name: '',
  trading_name: '',
  registration_number: '',
  vat_number: '',
  eaab_ffc_number: '',
  contact_number: '',
  email: '',
  physical_address: '',
  postal_address: '',
  website: '',
  trust_account_number: '',
  trust_bank_name: '',
  trust_branch_code: '',
  principal_name: '',
  principal_ppra_number: '',
  auditor_name: '',
  auditor_irba_number: '',
  bee_level: '',
  fica_registered: false,
  statement_date: 'the 5th',
  disbursement_date: 'the 7th',
  information_officer_email: '',
})

const form = ref(defaultForm())

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/auth/agency/')
    if (data && data.id) {
      existingId.value = data.id
      form.value = {
        name:                      data.name || '',
        trading_name:              data.trading_name || '',
        registration_number:       data.registration_number || '',
        vat_number:                data.vat_number || '',
        eaab_ffc_number:           data.eaab_ffc_number || '',
        contact_number:            data.contact_number || '',
        email:                     data.email || '',
        physical_address:          data.physical_address || '',
        postal_address:            data.postal_address || '',
        website:                   data.website || '',
        trust_account_number:      data.trust_account_number || '',
        trust_bank_name:           data.trust_bank_name || '',
        trust_branch_code:         data.trust_branch_code || '',
        principal_name:            data.principal_name || '',
        principal_ppra_number:     data.principal_ppra_number || '',
        auditor_name:              data.auditor_name || '',
        auditor_irba_number:       data.auditor_irba_number || '',
        bee_level:                 data.bee_level || '',
        fica_registered:           data.fica_registered || false,
        statement_date:            data.statement_date || 'the 5th',
        disbursement_date:         data.disbursement_date || 'the 7th',
        information_officer_email: data.information_officer_email || '',
      }
      if (data.logo) {
        logoPreview.value = data.logo
      }
    }
  } catch {
    showToast('Failed to load agency settings', 'error')
  } finally {
    loading.value = false
  }
}

function onLogoChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  logoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
}

function removeLogo() {
  logoFile.value = null
  logoPreview.value = null
}

async function save() {
  saving.value = true
  try {
    const fd = new FormData()
    for (const [key, val] of Object.entries(form.value)) {
      if (typeof val === 'boolean') {
        fd.append(key, val ? 'true' : 'false')
      } else {
        fd.append(key, val as string)
      }
    }
    if (logoFile.value) {
      fd.append('logo', logoFile.value)
    }

    const { data } = await api.put('/auth/agency/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    existingId.value = data.id
    // Refresh agency in auth store
    await auth.fetchAgency()
    showToast('Agency settings saved', 'success')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.response?.data?.name?.[0] || 'Failed to save'
    showToast(msg, 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
