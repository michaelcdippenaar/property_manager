<template>
  <div class="space-y-0">

    <!-- ── Page header ── -->
    <PageHeader
      :title="person?.full_name || '—'"
      :subtitle="person?.email || 'No email'"
      :crumbs="[
        { label: 'Dashboard', to: '/' },
        { label: 'Tenants', to: '/tenants' },
        { label: person?.full_name || '—' },
      ]"
      back
    >
      <template #title-adornment>
        <span v-if="person" :class="isActive ? 'badge-green' : 'badge-red'">
          {{ isActive ? 'Active' : 'Inactive' }}
        </span>
      </template>
    </PageHeader>

    <!-- ── Tabs ── -->
    <div class="flex items-center gap-1 border-b border-gray-200 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === tab.key
          ? 'border-navy text-navy'
          : 'border-transparent text-gray-400 hover:text-gray-600 hover:border-gray-300'"
        @click="activeTab = tab.key"
      >
        <component :is="tab.icon" :size="15" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4 animate-pulse">
      <div class="h-12 bg-gray-100 rounded-xl" />
      <div class="h-56 bg-gray-100 rounded-xl" />
    </div>

    <!-- ── Tab: Details ── -->
    <div v-else-if="activeTab === 'details'" class="grid grid-cols-3 gap-6 pt-2">
      <form @submit.prevent="savePerson" class="col-span-2 space-y-6">
        <!-- Personal info card -->
        <div class="card p-5">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-12 h-12 rounded-xl bg-gray-100 text-gray-600 flex items-center justify-center">
              <User :size="22" />
            </div>
            <div>
              <div class="font-semibold text-gray-900">{{ person?.full_name || '—' }}</div>
              <span class="badge-gray capitalize text-xs">{{ person?.person_type || 'individual' }}</span>
            </div>
          </div>

          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div class="col-span-2">
                <label class="label">Full name</label>
                <input v-model="local.full_name" class="input" />
              </div>
              <div>
                <label class="label">Email</label>
                <input v-model="local.email" type="email" class="input" />
              </div>
              <div>
                <label class="label">Phone</label>
                <input v-model="local.phone" type="tel" class="input" />
              </div>
              <div>
                <label class="label">SA ID / Passport number</label>
                <input v-model="local.id_number" class="input font-mono" data-clarity-mask="True" />
              </div>
              <div>
                <label class="label">Date of birth</label>
                <input v-model="local.date_of_birth" type="date" class="input" />
              </div>
              <div class="col-span-2">
                <label class="label">Address</label>
                <input v-model="local.address" class="input" />
              </div>
            </div>
          </div>
        </div>

        <!-- Employment card -->
        <div class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-4 flex items-center gap-1.5">
            <Briefcase :size="13" /> Employment
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Employer</label>
              <input v-model="local.employer" class="input" />
            </div>
            <div>
              <label class="label">Occupation</label>
              <input v-model="local.occupation" class="input" />
            </div>
            <div>
              <label class="label">Monthly income (ZAR)</label>
              <input v-model="local.monthly_income" type="number" class="input" />
            </div>
          </div>
        </div>

        <!-- Emergency contact card -->
        <div class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-4 flex items-center gap-1.5">
            <Phone :size="13" /> Emergency contact
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Name</label>
              <input v-model="local.emergency_contact_name" class="input" />
            </div>
            <div>
              <label class="label">Phone</label>
              <input v-model="local.emergency_contact_phone" type="tel" class="input" />
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="btn-primary" :disabled="saving">
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            {{ saving ? 'Saving…' : 'Save changes' }}
          </button>
        </div>
      </form>

      <!-- Sidebar -->
      <div class="space-y-4">
        <!-- Current tenancy -->
        <div class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-3 flex items-center gap-1.5">
            <Home :size="13" /> Current tenancy
          </div>
          <div v-if="activeLease" class="space-y-2">
            <RouterLink
              :to="{ name: 'property-detail', params: { id: activeLease.property_id } }"
              class="block hover:opacity-80 transition-opacity"
            >
              <div class="text-sm font-medium text-gray-900">{{ activeLease.unit_label }}</div>
              <div class="text-xs text-gray-400 mt-0.5">
                {{ formatDate(activeLease.start_date) }} – {{ activeLease.end_date ? formatDate(activeLease.end_date) : 'ongoing' }}
              </div>
            </RouterLink>
            <div class="text-xs text-gray-500">
              Rent: <span class="font-medium">{{ formatCurrency(activeLease.monthly_rent) }}/mo</span>
            </div>
          </div>
          <p v-else class="text-xs text-gray-400">No active lease</p>
        </div>

        <!-- Lease history quick count -->
        <div class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-3 flex items-center gap-1.5">
            <FileText :size="13" /> Lease history
          </div>
          <p class="text-sm text-gray-700">{{ leases.length }} lease{{ leases.length !== 1 ? 's' : '' }}</p>
          <button type="button" class="text-xs text-navy mt-1 hover:underline" @click="activeTab = 'leases'">
            View all leases →
          </button>
        </div>

        <!-- Sureties -->
        <div v-if="relatedGuarantors.length" class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-3 flex items-center gap-1.5">
            <Shield :size="13" /> Sureties
          </div>
          <div class="space-y-2">
            <RouterLink
              v-for="g in relatedGuarantors"
              :key="g.id"
              :to="{ name: 'tenant-detail', params: { id: g.id } }"
              class="flex items-center gap-2 group"
            >
              <div class="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 text-xs font-bold flex-shrink-0 group-hover:bg-navy group-hover:text-white transition-colors">
                {{ initials(g.full_name) }}
              </div>
              <div class="min-w-0">
                <div class="text-sm text-gray-900 group-hover:text-navy transition-colors truncate">{{ g.full_name }}</div>
                <div class="text-micro text-gray-400 truncate">{{ g.email || g.leaseNumber }}</div>
              </div>
            </RouterLink>
          </div>
        </div>

        <!-- Occupants -->
        <div v-if="relatedOccupants.length" class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-3 flex items-center gap-1.5">
            <Users :size="13" /> Occupants
          </div>
          <div class="space-y-2">
            <RouterLink
              v-for="o in relatedOccupants"
              :key="o.id"
              :to="{ name: 'tenant-detail', params: { id: o.id } }"
              class="flex items-center gap-2 group"
            >
              <div class="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 text-xs font-bold flex-shrink-0 group-hover:bg-navy group-hover:text-white transition-colors">
                {{ initials(o.full_name) }}
              </div>
              <div class="min-w-0">
                <div class="text-sm text-gray-900 group-hover:text-navy transition-colors truncate">{{ o.full_name }}</div>
                <div class="text-micro text-gray-400 truncate">{{ o.email || o.leaseNumber }}</div>
              </div>
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tab: Leases ── -->
    <div v-else-if="activeTab === 'leases'" class="pt-2">
      <div v-if="leasesLoading" class="space-y-3 animate-pulse">
        <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-xl" />
      </div>
      <div v-else-if="leases.length" class="card">
        <div class="table-scroll"><table class="table-wrap">
          <thead>
            <tr>
              <th scope="col">Lease</th>
              <th scope="col">Property / Unit</th>
              <th scope="col">Period</th>
              <th scope="col">Rent</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="l in leases"
              :key="l.id"
              class="cursor-pointer hover:bg-gray-50"
              @click="router.push({ name: 'property-detail', params: { id: l.property_id } })"
            >
              <td class="font-mono text-xs text-gray-600">{{ l.lease_number }}</td>
              <td class="text-sm text-gray-900">{{ l.unit_label }}</td>
              <td class="text-xs text-gray-500">
                {{ formatDate(l.start_date) }} – {{ l.end_date ? formatDate(l.end_date) : '—' }}
              </td>
              <td class="text-sm text-gray-700">{{ formatCurrency(l.monthly_rent) }}/mo</td>
              <td>
                <span :class="statusBadge(l.status)">{{ l.status }}</span>
              </td>
            </tr>
          </tbody>
        </table></div>
      </div>
      <div v-else class="card p-10 text-center">
        <div class="text-sm text-gray-400">No leases found for this tenant</div>
      </div>
    </div>

    <!-- ── Tab: Onboarding ── -->
    <div v-else-if="activeTab === 'onboarding'" class="pt-2">
      <TenantOnboardingView
        :person-id="personId"
        :latest-lease-id="activeLease?.id ?? (leases[0]?.id ?? null)"
        :lease-deposit="activeLease?.deposit ?? leases[0]?.deposit ?? null"
        :tenant-profile-path="`/tenants/${personId}`"
      />
    </div>

    <!-- ── Tab: Documents ── -->
    <div v-else-if="activeTab === 'documents'" class="pt-2">
      <div class="card p-5 space-y-4">
        <div class="flex items-center justify-between">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <FileUp :size="13" /> Documents
          </div>
        </div>

        <!-- Document type selector -->
        <div>
          <label class="label">Document type</label>
          <select v-model="uploadDocType" class="input">
            <option value="id_copy">ID / Passport Copy</option>
            <option value="proof_of_address">Proof of Address</option>
            <option value="proof_of_income">Proof of Income</option>
            <option value="fica">FICA / KYC Document</option>
            <option value="other">Other</option>
          </select>
        </div>

        <!-- Upload zone -->
        <label
          class="flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors"
          :class="uploadingDocs ? 'border-navy/30 bg-navy/5' : 'border-gray-200 hover:border-navy/40 hover:bg-gray-50'"
        >
          <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
            <Upload :size="18" class="text-gray-400" />
          </div>
          <div class="text-center">
            <span class="text-sm font-medium text-gray-700">Drop documents here or click to browse</span>
            <p class="text-xs text-gray-400 mt-0.5">PDF, JPG, PNG, DOCX — multiple files supported</p>
          </div>
          <Loader2 v-if="uploadingDocs" :size="16" class="animate-spin text-navy" />
          <input
            type="file"
            class="hidden"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.docx"
            @change="uploadDocuments"
          />
        </label>

        <!-- Document list -->
        <div v-if="documents.length" class="space-y-1">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-gray-50 border border-gray-100"
          >
            <FileText :size="13" class="text-gray-400 flex-shrink-0" />
            <span class="text-xs text-gray-700 flex-1 truncate">{{ doc.description || doc.document_type || 'Document' }}</span>
            <span class="text-micro text-gray-400">{{ formatDate(doc.uploaded_at) }}</span>
            <a
              :href="doc.file_url"
              target="_blank"
              class="p-0.5 rounded text-gray-300 hover:text-navy transition-colors"
              aria-label="View file"
            >
              <Eye :size="12" />
            </a>
            <button
              class="p-0.5 rounded text-gray-300 hover:text-danger-500 transition-colors"
              aria-label="Delete document"
              @click.stop="deleteDocument(doc)"
            >
              <X :size="12" />
            </button>
          </div>
        </div>
        <p v-else class="text-xs text-gray-400 text-center py-1">No documents uploaded yet.</p>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, User, Users, Briefcase, Phone, Home, FileText, FileUp,
  Upload, Eye, X, Loader2, Shield, ClipboardList,
} from 'lucide-vue-next'

import api from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import TenantOnboardingView from './TenantOnboardingView.vue'
import type { Person } from '../../types/person'
import type { Lease } from '../../types/lease'
import { usePersonsStore } from '../../stores/persons'
import { useLeasesStore } from '../../stores/leases'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import { formatDate, initials } from '../../utils/formatters'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const personsStore = usePersonsStore()
const leasesStore = useLeasesStore()

const personId = computed(() => Number(route.params.id))

// ─── State ────────────────────────────────────────────────────────────────────
const person = ref<Person | null>(null)
const leases = ref<Lease[]>([])
const documents = ref<any[]>([])
const loading = ref(true)
const leasesLoading = ref(false)
const saving = ref(false)
const uploadingDocs = ref(false)
const uploadDocType = ref('id_copy')

const local = ref<Partial<Person>>({})

const tabs = [
  { key: 'details',    label: 'Details',    icon: User },
  { key: 'leases',     label: 'Leases',     icon: FileText },
  { key: 'onboarding', label: 'Onboarding', icon: ClipboardList },
  { key: 'documents',  label: 'Documents',  icon: FileUp },
]
const activeTab = ref('details')

// ─── Computed ─────────────────────────────────────────────────────────────────
const activeLease = computed(() =>
  leases.value.find(l => l.status === 'active') ?? null
)

const isActive = computed(() => leases.value.some(l => l.status === 'active'))

// Unique guarantors across all leases, excluding the primary tenant themselves
const relatedGuarantors = computed(() => {
  const seen = new Set<number>()
  const result: { id: number; full_name: string; email?: string; leaseNumber: string }[] = []
  for (const lease of leases.value) {
    for (const g of lease.guarantors ?? []) {
      if (g.id === personId.value) continue
      if (seen.has(g.id)) continue
      seen.add(g.id)
      result.push({ ...g, leaseNumber: lease.lease_number })
    }
  }
  return result
})

// Unique occupants across all leases, excluding the primary tenant themselves
const relatedOccupants = computed(() => {
  const seen = new Set<number>()
  const result: { id: number; full_name: string; email?: string; leaseNumber: string }[] = []
  for (const lease of leases.value) {
    for (const o of lease.occupants ?? []) {
      if (o.id === personId.value) continue
      if (seen.has(o.id)) continue
      seen.add(o.id)
      result.push({ ...o, leaseNumber: lease.lease_number })
    }
  }
  return result
})

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatCurrency(val: string | number | null | undefined): string {
  if (val == null || val === '') return '—'
  return `R ${Number(val).toLocaleString('en-ZA', { minimumFractionDigits: 0 })}`
}

function statusBadge(status: string): string {
  return {
    active:     'badge-green',
    pending:    'badge-gray',
    expired:    'badge-red',
    terminated: 'badge-red',
  }[status] ?? 'badge-gray'
}

// ─── Data fetching ────────────────────────────────────────────────────────────
async function loadPerson(): Promise<void> {
  loading.value = true
  try {
    const p = await personsStore.fetchPerson(personId.value)
    person.value = p
    local.value = { ...p }
    // documents are nested in the person response
    documents.value = (p as any).documents ?? []
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load tenant'))
  } finally {
    loading.value = false
  }
}

async function loadLeases(): Promise<void> {
  leasesLoading.value = true
  try {
    leases.value = await leasesStore.fetchForPerson(personId.value)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load leases'))
  } finally {
    leasesLoading.value = false
  }
}

onMounted(async () => {
  await loadPerson()
  loadLeases()
})

watch(activeTab, (tab) => {
  if (tab === 'leases' && leases.value.length === 0) loadLeases()
})

// ─── Mutations ────────────────────────────────────────────────────────────────
async function savePerson(): Promise<void> {
  saving.value = true
  try {
    const patch: Partial<Person> = {
      full_name: local.value.full_name,
      email: local.value.email,
      phone: local.value.phone,
      id_number: local.value.id_number,
      date_of_birth: local.value.date_of_birth,
      address: local.value.address,
      employer: local.value.employer,
      occupation: local.value.occupation,
      monthly_income: local.value.monthly_income,
      emergency_contact_name: local.value.emergency_contact_name,
      emergency_contact_phone: local.value.emergency_contact_phone,
    }
    const updated = await personsStore.updatePerson(personId.value, patch)
    person.value = updated
    toast.success('Tenant details saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save'))
  } finally {
    saving.value = false
  }
}

async function uploadDocuments(event: Event): Promise<void> {
  const files = (event.target as HTMLInputElement).files
  if (!files || files.length === 0) return
  uploadingDocs.value = true
  try {
    const fd = new FormData()
    fd.append('document_type', uploadDocType.value)
    for (const f of Array.from(files)) fd.append('file', f)
    const { data } = await api.post(`/auth/persons/${personId.value}/documents/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const added = Array.isArray(data) ? data : [data]
    documents.value = [...documents.value, ...added]
    toast.success(files.length === 1 ? 'Document uploaded' : `${files.length} documents uploaded`)
  } catch (err) {
    toast.error(extractApiError(err, 'Upload failed'))
  } finally {
    uploadingDocs.value = false
    ;(event.target as HTMLInputElement).value = ''
  }
}

async function deleteDocument(doc: any): Promise<void> {
  try {
    await api.delete(`/auth/persons/${personId.value}/documents/${doc.id}/`)
    documents.value = documents.value.filter(d => d.id !== doc.id)
    toast.success('Document deleted')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete document'))
  }
}
</script>
