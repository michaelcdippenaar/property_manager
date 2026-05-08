<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex flex-col bg-white overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center">
            <Pencil :size="14" class="text-white" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-sm">Edit Lease</div>
            <div class="text-xs text-gray-400">{{ lease.lease_number }} · {{ lease.unit_label }}</div>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button @click="onCancelClick" class="btn-ghost">Cancel</button>
          <button @click="saveAll" :disabled="saving" class="btn-primary">
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            Save Changes
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-3xl mx-auto px-6 py-8 space-y-10">

          <!-- Save success toast -->
          <div v-if="saveOk" class="flex items-center gap-2 px-4 py-3 bg-success-50 border border-success-100 rounded-xl text-sm text-success-700">
            <CheckCircle2 :size="15" class="text-success-500 flex-shrink-0" />
            Lease saved successfully
          </div>
          <div v-if="saveError" class="flex items-center gap-2 px-4 py-3 bg-danger-50 border border-danger-100 rounded-xl text-sm text-danger-700">
            <AlertCircle :size="15" class="text-danger-500 flex-shrink-0" />
            {{ saveError }}
          </div>

          <!-- ── Section: Property & Unit ── -->
          <section>
            <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Property &amp; Unit</div>
            <div class="card p-5 grid grid-cols-2 gap-4">
              <div>
                <label class="label">Property</label>
                <select v-model="selectedPropertyId" class="input" @change="onPropertyChange">
                  <option v-for="p in allProperties" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
              </div>
              <div>
                <label class="label">Unit</label>
                <select v-model="form.unit" class="input">
                  <option v-for="u in unitsForSelectedProperty" :key="u.id" :value="u.id">
                    Unit {{ u.unit_number }}
                  </option>
                </select>
              </div>
            </div>
          </section>

          <!-- ── Section: Lease Details ── -->
          <section>
            <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Lease Details</div>
            <div class="card p-5 grid grid-cols-2 gap-4">
              <div>
                <label class="label">Lease Number</label>
                <input v-model="form.lease_number" class="input font-mono" placeholder="L-202601-0001" />
              </div>
              <div>
                <label class="label">Status</label>
                <select v-model="form.status" class="input">
                  <option value="pending">Pending</option>
                  <option value="active">Active</option>
                  <option value="expired">Expired</option>
                  <option value="terminated">Terminated</option>
                </select>
              </div>
              <div>
                <label class="label">Start Date</label>
                <input v-model="form.start_date" type="date" class="input" />
              </div>
              <div>
                <label class="label">End Date</label>
                <input v-model="form.end_date" type="date" class="input" />
              </div>
              <div>
                <label class="label">Monthly Rent (R)</label>
                <input v-model="form.monthly_rent" type="number" min="0" class="input" />
              </div>
              <div>
                <label class="label">Deposit (R)</label>
                <input v-model="form.deposit" type="number" min="0" class="input" />
              </div>
              <div class="col-span-2">
                <label class="label">Payment Reference</label>
                <input v-model="form.payment_reference" class="input" placeholder="e.g. 18 Irene - Smith" />
              </div>
            </div>
          </section>

          <!-- ── Section: Terms ── -->
          <section>
            <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Terms &amp; Utilities</div>
            <div class="card p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <label class="label">Max Occupants</label>
                <input v-model="form.max_occupants" type="number" min="1" class="input" />
              </div>
              <div>
                <label class="label">Notice Period (days)</label>
                <input v-model="form.notice_period_days" type="number" min="0" class="input" />
              </div>
              <div>
                <label class="label">Early Exit Penalty (months)</label>
                <input v-model="form.early_termination_penalty_months" type="number" min="0" class="input" />
              </div>
              <div class="col-span-2 sm:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-4">
                <!-- Water arrangement (Feature 3) -->
                <div>
                  <label class="label">Water</label>
                  <select v-model="form.water_arrangement" class="input">
                    <option value="included">Included in rent</option>
                    <option value="not_included">Not included</option>
                  </select>
                  <div class="text-xs text-gray-400 mt-1">Inherited from property; override per-lease if needed.</div>
                </div>
                <div v-if="form.water_arrangement === 'included'">
                  <label class="label">Water Limit (litres)</label>
                  <input v-model="form.water_limit_litres" type="number" min="0" class="input" />
                </div>
                <!-- Electricity arrangement -->
                <div>
                  <label class="label">Electricity</label>
                  <select v-model="form.electricity_arrangement" class="input">
                    <option value="prepaid">Prepaid</option>
                    <option value="eskom_direct">Direct Eskom account</option>
                    <option value="included">Included in rent</option>
                    <option value="not_included">Tenant arranges separately</option>
                  </select>
                </div>
              </div>
              <div class="col-span-2 sm:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-4">
                <label class="flex items-center gap-2 text-sm">
                  <input v-model="form.gardening_service_included" type="checkbox" /> Gardening service
                </label>
                <label class="flex items-center gap-2 text-sm">
                  <input v-model="form.wifi_included" type="checkbox" /> Wifi included
                </label>
                <label class="flex items-center gap-2 text-sm">
                  <input v-model="form.security_service_included" type="checkbox" /> Armed response
                </label>
              </div>
            </div>
          </section>

          <!-- ── Section: Tenants ── -->
          <section>
            <div class="flex items-center justify-between mb-3">
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest">Tenants — jointly &amp; severally liable</div>
              <button @click="showAddTenant = !showAddTenant" class="btn-ghost text-xs">
                <Plus :size="12" /> Add Tenant
              </button>
            </div>
            <div class="space-y-3">
              <div
                v-for="(t, i) in allTenants"
                :key="t.id ?? `new-${i}`"
                class="card p-4"
              >
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-navy/10 flex items-center justify-center text-navy text-xs font-bold flex-shrink-0">
                      {{ i + 1 }}
                    </div>
                    <span class="text-sm font-medium text-gray-700">Tenant {{ i + 1 }}</span>
                  </div>
                  <button
                    v-if="allTenants.length > 1"
                    @click="removeTenant(t)"
                    :disabled="removingId === t.id"
                    class="text-xs text-danger-400 hover:text-danger-700 transition-colors flex items-center gap-1"
                  >
                    <Loader2 v-if="removingId === t.id" :size="11" class="animate-spin" />
                    <Trash2 v-else :size="11" />
                    Remove
                  </button>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div class="col-span-2">
                    <label class="label">Full Name</label>
                    <input v-model="t.full_name" class="input" placeholder="Full legal name" />
                  </div>
                  <div>
                    <label class="label">ID / Passport</label>
                    <MaskedInput v-model="t.id_number" class="input font-mono" placeholder="SA ID or passport" />
                  </div>
                  <div>
                    <label class="label">Phone</label>
                    <div class="flex gap-2">
                      <PhoneCountryCodeSelect v-model="t.phone_country_code" />
                      <input v-model="t.phone" class="input flex-1" placeholder="phone number" />
                    </div>
                  </div>
                  <div class="col-span-2">
                    <label class="label">Email</label>
                    <input v-model="t.email" type="email" class="input" placeholder="email@example.com" />
                  </div>
                  <div class="col-span-2">
                    <label class="label">Country</label>
                    <CountrySelect v-model="t.country" />
                  </div>
                  <div class="col-span-2">
                    <label class="label">Payment Reference</label>
                    <input v-model="t.payment_reference" class="input" placeholder="e.g. 18 Irene - Smith" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Add tenant inline form -->
            <div v-if="showAddTenant" class="card p-4 mt-3 border-dashed border-2 border-gray-200">
              <div class="text-xs font-semibold text-gray-500 mb-3">New Tenant</div>
              <div class="grid grid-cols-2 gap-3">
                <div class="col-span-2">
                  <label class="label">Full Name *</label>
                  <input v-model="newTenant.full_name" class="input" placeholder="Full legal name" />
                </div>
                <div>
                  <label class="label">ID / Passport</label>
                  <MaskedInput v-model="newTenant.id_number" class="input font-mono" />
                </div>
                <div>
                  <label class="label">Phone</label>
                  <div class="flex gap-2">
                    <PhoneCountryCodeSelect v-model="newTenant.phone_country_code" />
                    <input v-model="newTenant.phone" class="input flex-1" />
                  </div>
                </div>
                <div class="col-span-2">
                  <label class="label">Email</label>
                  <input v-model="newTenant.email" type="email" class="input" />
                </div>
                <div class="col-span-2">
                  <label class="label">Country</label>
                  <CountrySelect v-model="newTenant.country" />
                </div>
              </div>
              <div v-if="addTenantError" class="mt-2 text-xs text-danger-600 flex items-center gap-1.5">
                <AlertCircle :size="12" class="flex-shrink-0" />
                {{ addTenantError }}
              </div>
              <div class="flex items-center gap-2 mt-3">
                <button @click="addTenant" :disabled="!newTenant.full_name || addingTenant" class="btn-primary text-xs">
                  <Loader2 v-if="addingTenant" :size="12" class="animate-spin" />
                  Add Tenant
                </button>
                <button @click="showAddTenant = false; resetNewTenant()" class="btn-ghost text-xs">Cancel</button>
              </div>
            </div>
          </section>

          <!-- ── Section: Occupants ── -->
          <section>
            <div class="flex items-center justify-between mb-3">
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest">Occupants</div>
              <button @click="showAddOccupant = !showAddOccupant" class="btn-ghost text-xs">
                <Plus :size="12" /> Add Occupant
              </button>
            </div>

            <div class="space-y-2">
              <div
                v-for="occ in allOccupants"
                :key="occ.id"
                class="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-gray-200"
              >
                <Users :size="14" class="text-gray-400 flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-gray-800">{{ occ.person.full_name }}</div>
                  <div v-if="occ.relationship_to_tenant" class="text-xs text-gray-400">{{ occ.relationship_to_tenant }}</div>
                </div>
                <button @click="removeOccupant(occ)" class="p-1 text-gray-300 hover:text-danger-500 transition-colors">
                  <X :size="14" />
                </button>
              </div>
              <div v-if="!allOccupants.length" class="text-xs text-gray-400 px-1">No occupants listed</div>
            </div>

            <!-- Add occupant form -->
            <div v-if="showAddOccupant" class="card p-4 mt-3 border-dashed border-2 border-gray-200">
              <div class="text-xs font-semibold text-gray-500 mb-3">New Occupant</div>
              <div class="grid grid-cols-2 gap-3">
                <div class="col-span-2">
                  <label class="label">Full Name *</label>
                  <input v-model="newOccupant.full_name" class="input" placeholder="Full legal name" />
                </div>
                <div class="col-span-2">
                  <label class="label">Relationship to Tenant</label>
                  <input v-model="newOccupant.relationship" class="input" placeholder="e.g. spouse, child, self" />
                </div>
              </div>
              <div class="flex gap-2 mt-3">
                <button @click="addOccupant" :disabled="!newOccupant.full_name || addingOccupant" class="btn-primary text-xs">
                  <Loader2 v-if="addingOccupant" :size="12" class="animate-spin" />
                  Add Occupant
                </button>
                <button @click="showAddOccupant = false; resetNewOccupant()" class="btn-ghost text-xs">Cancel</button>
              </div>
            </div>
          </section>

          <!-- ── Section: Guarantors ── -->
          <section>
            <div class="flex items-center justify-between mb-3">
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest">Guarantors / Sureties</div>
              <button @click="showAddGuarantor = !showAddGuarantor" class="btn-ghost text-xs">
                <Plus :size="12" /> Add Guarantor
              </button>
            </div>

            <div class="space-y-2">
              <div
                v-for="gua in allGuarantors"
                :key="gua.id"
                class="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-gray-200"
              >
                <Shield :size="14" class="text-gray-400 flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-gray-800">{{ gua.person.full_name }}</div>
                  <div v-if="gua.covers_tenant" class="text-xs text-gray-400">covers {{ gua.covers_tenant.full_name }}</div>
                </div>
                <button @click="removeGuarantor(gua)" class="p-1 text-gray-300 hover:text-danger-500 transition-colors">
                  <X :size="14" />
                </button>
              </div>
              <div v-if="!allGuarantors.length" class="text-xs text-gray-400 px-1">No guarantors listed</div>
            </div>

            <!-- Add guarantor form -->
            <div v-if="showAddGuarantor" class="card p-4 mt-3 border-dashed border-2 border-gray-200">
              <div class="text-xs font-semibold text-gray-500 mb-3">New Guarantor</div>
              <div class="grid grid-cols-2 gap-3">
                <div class="col-span-2">
                  <label class="label">Full Name *</label>
                  <input v-model="newGuarantor.full_name" class="input" placeholder="Full legal name" />
                </div>
                <div>
                  <label class="label">ID / Passport</label>
                  <MaskedInput v-model="newGuarantor.id_number" class="input font-mono" />
                </div>
                <div>
                  <label class="label">Phone</label>
                  <input v-model="newGuarantor.phone" class="input" />
                </div>
                <div class="col-span-2">
                  <label class="label">Covers Tenant (optional)</label>
                  <select v-model="newGuarantor.covers_tenant_id" class="input">
                    <option value="">— All tenants —</option>
                    <option v-for="t in allTenants" :key="t.id" :value="t.id">{{ t.full_name }}</option>
                  </select>
                </div>
              </div>
              <div class="flex gap-2 mt-3">
                <button @click="addGuarantor" :disabled="!newGuarantor.full_name || addingGuarantor" class="btn-primary text-xs">
                  <Loader2 v-if="addingGuarantor" :size="12" class="animate-spin" />
                  Add Guarantor
                </button>
                <button @click="showAddGuarantor = false; resetNewGuarantor()" class="btn-ghost text-xs">Cancel</button>
              </div>
            </div>
          </section>

          <!-- ── Section: Documents ── -->
          <section class="pb-12">
            <div class="flex items-center justify-between mb-3">
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest">Documents ({{ docList.length }})</div>
            </div>

            <!-- Existing docs -->
            <div class="space-y-2 mb-4">
              <div
                v-for="doc in docList"
                :key="doc.id"
                class="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-gray-200"
              >
                <FileText :size="14" class="text-gray-400 flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-gray-800 truncate">
                    {{ doc.description || doc.document_type.replace('_', ' ') }}
                  </div>
                  <div class="text-xs text-gray-400">{{ doc.document_type.replace('_', ' ') }} · {{ formatDate(doc.uploaded_at) }}</div>
                </div>
                <a :href="doc.file_url" target="_blank" class="p-1.5 text-gray-400 hover:text-navy rounded transition-colors">
                  <Download :size="14" />
                </a>
                <button @click="deleteDocument(doc)" class="p-1.5 text-gray-300 hover:text-danger-500 rounded transition-colors">
                  <Trash2 :size="14" />
                </button>
              </div>
              <div v-if="!docList.length" class="text-xs text-gray-400 px-1">No documents attached</div>
            </div>

            <!-- Upload new doc -->
            <div class="card p-4 border-dashed border-2 border-gray-200">
              <div class="text-xs font-semibold text-gray-500 mb-3">Upload Document</div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="label">Type</label>
                  <select v-model="newDoc.type" class="input">
                    <option value="signed_lease">Signed Lease</option>
                    <option value="id_copy">ID Copy</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label class="label">Description</label>
                  <input v-model="newDoc.description" class="input" placeholder="Optional label" />
                </div>
                <div class="col-span-2">
                  <label class="label">File</label>
                  <input
                    ref="docFileInput"
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    class="input file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-navy file:text-white hover:file:bg-navy/80"
                    @change="onDocFileChange"
                  />
                </div>
              </div>
              <button
                class="btn-primary text-xs mt-3"
                :disabled="!newDoc.file || uploadingDoc"
                @click="uploadDocument"
              >
                <Loader2 v-if="uploadingDoc" :size="12" class="animate-spin" />
                Upload
              </button>
            </div>
          </section>

          <!-- ── Section: E-Signing ── -->
          <section>
            <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">E-Signing</div>
            <div class="card p-5">
              <ESigningPanel
                :lease-id="lease.id"
                :lease-tenants="allTenants"
              />
            </div>
          </section>

        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '../../api'
import {
  Pencil, Loader2, Plus, Trash2, X, Users, Shield,
  FileText, Download, CheckCircle2, AlertCircle,
} from 'lucide-vue-next'
import ESigningPanel from './ESigningPanel.vue'
import MaskedInput from '../../components/shared/MaskedInput.vue'
import CountrySelect from '../../components/CountrySelect.vue'
import PhoneCountryCodeSelect from '../../components/PhoneCountryCodeSelect.vue'
import { usePropertiesStore } from '../../stores/properties'
import { usePersonsStore } from '../../stores/persons'

const props = defineProps<{ lease: any }>()
const emit = defineEmits<{ close: []; done: [updated: any] }>()

// ── State ────────────────────────────────────────────────────────────── //
const saving = ref(false)
const saveOk = ref(false)
const saveError = ref('')
const removingId = ref<number | null>(null)

// Dirty-tracking for unsaved-changes guard (Feature 2). Drawer-level: confirm
// before closing if user has touched fields.
const isDirty = ref(false)
function markDirty() { isDirty.value = true }
function markClean() { isDirty.value = false }

function onCancelClick() {
  if (!isDirty.value) { emit('close'); return }
  // eslint-disable-next-line no-alert
  const ok = typeof window !== 'undefined'
    ? window.confirm('You have unsaved changes. Discard and close?')
    : true
  if (ok) emit('close')
}

// Properties & units for reassignment
const propertiesStore = usePropertiesStore()
const personsStore = usePersonsStore()
const allProperties = computed(() => propertiesStore.list)
const selectedPropertyId = ref<number | null>(null)

const unitsForSelectedProperty = computed(() => {
  if (!selectedPropertyId.value) return []
  const prop = allProperties.value.find((p: any) => p.id === selectedPropertyId.value)
  return prop?.units ?? []
})

function onPropertyChange() {
  const units = unitsForSelectedProperty.value
  if (units.length) {
    form.unit = units[0].id
  }
}

// Basic form fields (deep copy so we don't mutate the prop)
const form = reactive({
  unit: props.lease.unit ?? null,
  lease_number: props.lease.lease_number ?? '',
  status: props.lease.status ?? 'pending',
  start_date: props.lease.start_date ?? '',
  end_date: props.lease.end_date ?? '',
  monthly_rent: props.lease.monthly_rent ?? '',
  deposit: props.lease.deposit ?? '',
  payment_reference: props.lease.payment_reference ?? '',
  max_occupants: props.lease.max_occupants ?? 1,
  water_included: props.lease.water_included ?? true,
  water_limit_litres: props.lease.water_limit_litres ?? 4000,
  electricity_prepaid: props.lease.electricity_prepaid ?? true,
  // Feature 3 — services & facilities (lease-level overrides)
  water_arrangement: props.lease.water_arrangement ?? (props.lease.water_included ? 'included' : 'not_included'),
  electricity_arrangement: props.lease.electricity_arrangement ?? (props.lease.electricity_prepaid ? 'prepaid' : 'included'),
  gardening_service_included: props.lease.gardening_service_included ?? false,
  wifi_included: props.lease.wifi_included ?? false,
  security_service_included: props.lease.security_service_included ?? false,
  notice_period_days: props.lease.notice_period_days ?? 20,
  early_termination_penalty_months: props.lease.early_termination_penalty_months ?? 3,
})

// Tenants: flatten primary + co_tenants into one editable array
const allTenants = ref<any[]>([])
// Store original person data so we can diff on save
const originalPersonData = new Map<number, Record<string, string>>()

function initTenants() {
  const tenants: any[] = []
  if (props.lease.primary_tenant_detail) {
    tenants.push({
      ...props.lease.primary_tenant_detail,
      _is_primary: true,
      _co_tenant_id: null,
      payment_reference: props.lease.payment_reference ?? '',
    })
  }
  for (const ct of props.lease.co_tenants ?? []) {
    tenants.push({
      ...ct.person,
      _is_primary: false,
      _co_tenant_id: ct.id,
      payment_reference: (ct as any).payment_reference ?? '',
    })
  }
  allTenants.value = tenants
  for (const t of tenants) {
    if (t.id) {
      originalPersonData.set(t.id, {
        full_name: t.full_name ?? '',
        id_number: t.id_number ?? '',
        phone: t.phone ?? '',
        phone_country_code: t.phone_country_code ?? '',
        email: t.email ?? '',
        country: t.country ?? '',
        payment_reference: t.payment_reference ?? '',
      })
    }
  }
}

// Occupants
const allOccupants = ref<any[]>([...(props.lease.occupants ?? [])])

// Guarantors
const allGuarantors = ref<any[]>([...(props.lease.guarantors ?? [])])

// Documents
const docList = ref<any[]>([...(props.lease.documents ?? [])])

// ── Add / remove tenant ──────────────────────────────────────────────── //
const showAddTenant = ref(false)
const addingTenant = ref(false)
const addTenantError = ref('')
const newTenant = ref({ full_name: '', id_number: '', phone: '', phone_country_code: '+27', email: '', country: 'ZA' })
function resetNewTenant() { newTenant.value = { full_name: '', id_number: '', phone: '', phone_country_code: '+27', email: '', country: 'ZA' }; addTenantError.value = '' }

async function addTenant() {
  if (!newTenant.value.full_name) return
  addingTenant.value = true
  addTenantError.value = ''
  try {
    const { data } = await api.post(`/leases/${props.lease.id}/tenants/`, {
      person: { person_type: 'individual', ...newTenant.value },
    })
    allTenants.value.push({ ...data })
    originalPersonData.set(data.id, {
      full_name: data.full_name ?? '',
      id_number: data.id_number ?? '',
      phone: data.phone ?? '',
      email: data.email ?? '',
    })
    showAddTenant.value = false
    resetNewTenant()
  } catch (e: any) {
    addTenantError.value = e?.response?.data
      ? JSON.stringify(e.response.data)
      : 'Failed to add tenant — please try again'
  } finally {
    addingTenant.value = false
  }
}

async function removeTenant(t: any) {
  if (!t.id) { allTenants.value = allTenants.value.filter(x => x !== t); return }
  removingId.value = t.id
  try {
    await api.delete(`/leases/${props.lease.id}/tenants/${t.id}/`)
    allTenants.value = allTenants.value.filter(x => x.id !== t.id)
  } finally {
    removingId.value = null
  }
}

// ── Add / remove occupant ────────────────────────────────────────────── //
const showAddOccupant = ref(false)
const addingOccupant = ref(false)
const newOccupant = ref({ full_name: '', relationship: '' })
function resetNewOccupant() { newOccupant.value = { full_name: '', relationship: '' } }

async function addOccupant() {
  if (!newOccupant.value.full_name) return
  addingOccupant.value = true
  try {
    const { data } = await api.post(`/leases/${props.lease.id}/occupants/`, {
      person: { person_type: 'individual', full_name: newOccupant.value.full_name },
      relationship_to_tenant: newOccupant.value.relationship,
    })
    allOccupants.value.push(data)
    showAddOccupant.value = false
    resetNewOccupant()
  } finally {
    addingOccupant.value = false
  }
}

async function removeOccupant(occ: any) {
  await api.delete(`/leases/${props.lease.id}/occupants/${occ.id}/`)
  allOccupants.value = allOccupants.value.filter(o => o.id !== occ.id)
}

// ── Add / remove guarantor ───────────────────────────────────────────── //
const showAddGuarantor = ref(false)
const addingGuarantor = ref(false)
const newGuarantor = ref({ full_name: '', id_number: '', phone: '', covers_tenant_id: '' })
function resetNewGuarantor() { newGuarantor.value = { full_name: '', id_number: '', phone: '', covers_tenant_id: '' } }

async function addGuarantor() {
  if (!newGuarantor.value.full_name) return
  addingGuarantor.value = true
  try {
    const { data } = await api.post(`/leases/${props.lease.id}/guarantors/`, {
      person: { person_type: 'individual', full_name: newGuarantor.value.full_name, id_number: newGuarantor.value.id_number, phone: newGuarantor.value.phone },
      covers_tenant_id: newGuarantor.value.covers_tenant_id || null,
    })
    allGuarantors.value.push(data)
    showAddGuarantor.value = false
    resetNewGuarantor()
  } finally {
    addingGuarantor.value = false
  }
}

async function removeGuarantor(gua: any) {
  await api.delete(`/leases/${props.lease.id}/guarantors/${gua.id}/`)
  allGuarantors.value = allGuarantors.value.filter(g => g.id !== gua.id)
}

// ── Documents ────────────────────────────────────────────────────────── //
const docFileInput = ref<HTMLInputElement | null>(null)
const uploadingDoc = ref(false)
const newDoc = ref({ type: 'signed_lease', description: '', file: null as File | null })

function onDocFileChange(e: Event) {
  newDoc.value.file = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function uploadDocument() {
  if (!newDoc.value.file) return
  uploadingDoc.value = true
  try {
    const fd = new FormData()
    fd.append('file', newDoc.value.file)
    fd.append('document_type', newDoc.value.type)
    fd.append('description', newDoc.value.description)
    const { data } = await api.post(`/leases/${props.lease.id}/documents/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    docList.value.unshift(data)
    newDoc.value = { type: 'signed_lease', description: '', file: null }
    if (docFileInput.value) docFileInput.value.value = ''
  } finally {
    uploadingDoc.value = false
  }
}

async function deleteDocument(doc: any) {
  await api.delete(`/leases/${props.lease.id}/documents/${doc.id}/`)
  docList.value = docList.value.filter(d => d.id !== doc.id)
}

// ── Save all ─────────────────────────────────────────────────────────── //
async function saveAll() {
  saving.value = true
  saveOk.value = false
  saveError.value = ''
  try {
    // Primary tenant payment ref lives on Lease.payment_reference.
    const primary = allTenants.value.find((t: any) => t._is_primary)
    if (primary) {
      form.payment_reference = primary.payment_reference ?? ''
    }

    // 1. Patch lease basic fields
    const { data: updated } = await api.patch(`/leases/${props.lease.id}/`, form)

    // 2. Patch any person details that changed (and per co-tenant payment_reference)
    const personPatches: Promise<any>[] = []
    for (const t of allTenants.value) {
      if (!t.id) continue
      const orig = originalPersonData.get(t.id)
      if (
        orig &&
        (orig.full_name !== (t.full_name ?? '') ||
          orig.id_number !== (t.id_number ?? '') ||
          orig.phone !== (t.phone ?? '') ||
          orig.phone_country_code !== (t.phone_country_code ?? '') ||
          orig.email !== (t.email ?? '') ||
          orig.country !== (t.country ?? ''))
      ) {
        personPatches.push(
          personsStore.updatePerson(t.id, {
            full_name: t.full_name,
            id_number: t.id_number,
            phone: t.phone,
            phone_country_code: t.phone_country_code,
            email: t.email,
            country: t.country,
          })
        )
      }
      // Co-tenant payment_reference patch (LeaseTenant row).
      if (
        !t._is_primary &&
        t._co_tenant_id &&
        orig &&
        orig.payment_reference !== (t.payment_reference ?? '')
      ) {
        personPatches.push(
          api.patch(`/leases/${props.lease.id}/co-tenants/${t._co_tenant_id}/`, {
            payment_reference: t.payment_reference ?? '',
          })
        )
      }
      // Update snapshot so re-saving doesn't re-patch
      originalPersonData.set(t.id, {
        full_name: t.full_name ?? '',
        id_number: t.id_number ?? '',
        phone: t.phone ?? '',
        phone_country_code: t.phone_country_code ?? '',
        email: t.email ?? '',
        country: t.country ?? '',
        payment_reference: t.payment_reference ?? '',
      })
    }
    await Promise.all(personPatches)

    markClean()
    emit('done', updated)
    emit('close')
  } catch (err: any) {
    saveError.value = err?.response?.data
      ? JSON.stringify(err.response.data)
      : 'Save failed — please try again'
  } finally {
    saving.value = false
  }
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA') : '—'
}

onMounted(async () => {
  initTenants()
  try {
    await propertiesStore.fetchAll()
    const currentUnitId = props.lease.unit
    if (currentUnitId) {
      const ownerProp = allProperties.value.find((p: any) =>
        (p.units ?? []).some((u: any) => u.id === currentUnitId)
      )
      if (ownerProp) selectedPropertyId.value = ownerProp.id
    }
  } catch {
    /* properties will be empty — user can still edit other fields */
  }
  // Install dirty watchers AFTER initial state load.
  markClean()
  watch(form, markDirty, { deep: true })
  watch(allTenants, markDirty, { deep: true })
  watch(allOccupants, markDirty, { deep: true })
  watch(allGuarantors, markDirty, { deep: true })
})
</script>
