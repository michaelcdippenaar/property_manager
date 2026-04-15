<template>
  <div class="space-y-5">
    <PageHeader
      title="Owners"
      subtitle="Manage owners, their properties, and bank accounts."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Owners' }]"
    >
      <template #actions>
        <button class="btn-primary" @click="openCreate">
          <Plus :size="15" /> Add Owner
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100 flex flex-col gap-3">
        <SearchInput v-model="search" placeholder="Search owners…" />
        <FilterPills v-model="typeFilter" :options="typeOptions" />
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <div v-else-if="filteredLandlords.length" class="table-scroll"><table class="table-wrap">
        <thead>
          <tr>
            <th scope="col">
              <button class="flex items-center gap-1 hover:text-gray-700 transition-colors" @click="toggleSort('name')">
                Owner <component :is="sortIcon('name')" :size="12" />
              </button>
            </th>
            <th scope="col">Type</th>
            <th scope="col">
              <button class="flex items-center gap-1 hover:text-gray-700 transition-colors" @click="toggleSort('profile')">
                Profile <component :is="sortIcon('profile')" :size="12" />
              </button>
            </th>
            <th scope="col">Email</th>
            <th scope="col" class="text-right">
              <button class="flex items-center gap-1 ml-auto hover:text-gray-700 transition-colors" @click="toggleSort('properties')">
                Properties <component :is="sortIcon('properties')" :size="12" />
              </button>
            </th>
            <th scope="col" class="w-8"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ll in filteredLandlords"
            :key="ll.id"
            class="group cursor-pointer hover:bg-gray-50"
            @click="openLandlord(ll)"
          >
            <td>
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                  :class="ll.landlord_type === 'company' ? 'bg-info-50 text-info-600' : ll.landlord_type === 'trust' ? 'bg-purple-50 text-purple-700' : ll.landlord_type === 'cc' ? 'bg-warning-50 text-warning-600' : ll.landlord_type === 'partnership' ? 'bg-success-50 text-success-600' : 'bg-gray-100 text-gray-600'"
                >
                  <Building2 v-if="ll.landlord_type === 'company'" :size="14" />
                  <Shield v-else-if="ll.landlord_type === 'trust'" :size="14" />
                  <Briefcase v-else-if="ll.landlord_type === 'cc'" :size="14" />
                  <Users v-else-if="ll.landlord_type === 'partnership'" :size="14" />
                  <User v-else :size="14" />
                </div>
                <div class="font-medium text-gray-900 group-hover:text-navy transition-colors">{{ ll.name }}</div>
              </div>
            </td>
            <td>
              <span :class="{
                'badge-indigo':     ll.landlord_type === 'company' || ll.landlord_type === 'trust',
                'badge-amber-deep': ll.landlord_type === 'cc',
                'badge-emerald':    ll.landlord_type === 'partnership',
                'badge-gray':       ll.landlord_type === 'individual' || !['company','trust','cc','partnership'].includes(ll.landlord_type),
              }">{{ LANDLORD_TYPE_LABELS[ll.landlord_type] ?? ll.landlord_type }}</span>
            </td>
            <td>
              <div class="flex items-center gap-2">
                <div
                  class="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden"
                  role="progressbar"
                  :aria-valuenow="completionPct(ll)"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :title="`Profile ${completionPct(ll)}% complete`"
                >
                  <div
                    class="h-full rounded-full transition-all"
                    :class="completionPct(ll) >= 100 ? 'bg-accent' : completionPct(ll) >= 60 ? 'bg-navy' : 'bg-warning-400'"
                    :style="`width:${completionPct(ll)}%`"
                  />
                </div>
                <span class="text-xs tabular-nums" :class="completionPct(ll) >= 100 ? 'text-accent font-medium' : 'text-gray-400'">{{ completionPct(ll) }}%</span>
              </div>
            </td>
            <td class="text-gray-600">{{ ll.email || '—' }}</td>
            <td class="text-right text-gray-600">{{ ll.property_count ?? 0 }}</td>
            <td class="text-right pr-3">
              <ChevronRight :size="14" class="text-accent group-hover:text-accent transition-colors" />
            </td>
          </tr>
        </tbody>
      </table></div>

      <EmptyState
        v-else
        title="No owners found"
        description="Add an owner to start linking them to properties and leases."
        :icon="UserCheck"
      >
        <button class="btn-primary btn-sm" @click="openCreate">
          <Plus :size="14" /> Add Owner
        </button>
      </EmptyState>
    </div>

    <!-- Create modal -->
    <BaseModal :open="showCreate" title="New Owner" @close="showCreate = false">
      <div class="space-y-4">
        <div>
          <label class="label">Legal name <span class="text-danger-500">*</span></label>
          <input v-model="createForm.name" class="input" required />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Type</label>
            <select v-model="createForm.landlord_type" class="input">
              <option value="individual">Individual</option>
              <option value="company">Company (Pty Ltd / NPC)</option>
              <option value="trust">Trust</option>
              <option value="cc">Close Corporation (CC)</option>
              <option value="partnership">Partnership</option>
            </select>
          </div>
          <div>
            <label class="label">{{ createForm.landlord_type === 'individual' ? 'SA ID' : 'Reg no.' }}</label>
            <input v-model="createForm.registration_number" class="input font-mono" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Email</label>
            <input v-model="createForm.email" type="email" class="input" />
          </div>
          <div>
            <label class="label">Phone</label>
            <input v-model="createForm.phone" class="input" />
          </div>
        </div>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="showCreate = false">Cancel</button>
        <button class="btn-primary" :disabled="saving || !createForm.name" @click="createLandlord">
          <Loader2 v-if="saving" :size="14" class="animate-spin" />
          Create
        </button>
      </template>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { ArrowDownUp, ArrowUpAZ, ArrowDownAZ, Briefcase, Building2, ChevronRight, Loader2, Plus, Shield, User, UserCheck, Users } from 'lucide-vue-next'
import BaseModal from '../../components/BaseModal.vue'
import PageHeader from '../../components/PageHeader.vue'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import FilterPills from '../../components/FilterPills.vue'
import type { PillOption } from '../../components/FilterPills.vue'
import { useToast } from '../../composables/useToast'
import { useLandlordsStore } from '../../stores/landlords'
import { extractApiError } from '../../utils/api-errors'
import type { Landlord } from '../../types/landlord'

const LANDLORD_TYPE_LABELS: Record<string, string> = {
  individual: 'Individual',
  company: 'Company',
  trust: 'Trust',
  cc: 'Close Corp',
  partnership: 'Partnership',
}

const toast = useToast()
const router = useRouter()

const landlordsStore = useLandlordsStore()
const { list: landlords, loading } = storeToRefs(landlordsStore)

const saving = ref(false)
const search = ref('')
const typeFilter = ref('all')
type LLSortField = 'name' | 'profile' | 'properties'
const sortBy = ref<LLSortField>('name')
const sortDir = ref<'asc' | 'desc'>('asc')
const showCreate = ref(false)

const createForm = ref({
  name: '',
  landlord_type: 'individual',
  registration_number: '',
  email: '',
  phone: '',
})

// Store handles cross-view reactivity — fetchAll() is a no-op within the
// staleness window, so this is safe to call on every mount.
onMounted(() => {
  landlordsStore.fetchAll().catch((err) => toast.error(extractApiError(err, 'Failed to load owners')))
})

const typeOptions = computed((): PillOption[] => {
  const all = landlords.value
  const count = (type: string) => all.filter(l => l.landlord_type === type).length
  return [
    { label: 'All', value: 'all', count: all.length },
    { label: 'Individual', value: 'individual', count: count('individual') },
    { label: 'Company', value: 'company', count: count('company') },
    { label: 'Trust', value: 'trust', count: count('trust') },
    { label: 'Close Corp', value: 'cc', count: count('cc') },
    { label: 'Partnership', value: 'partnership', count: count('partnership') },
  ].filter(o => o.value === 'all' || (o.count ?? 0) > 0)
})

function toggleSort(field: LLSortField) {
  if (sortBy.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortDir.value = 'asc'
  }
}

function sortIcon(field: LLSortField) {
  if (sortBy.value !== field) return ArrowDownUp
  return sortDir.value === 'asc' ? ArrowUpAZ : ArrowDownAZ
}

const filteredLandlords = computed(() => {
  const q = search.value.toLowerCase()
  let result = landlords.value.filter((ll) => {
    const matchesSearch = !q ||
      ll.name.toLowerCase().includes(q) ||
      (ll.email ?? '').toLowerCase().includes(q)
    if (!matchesSearch) return false
    if (typeFilter.value !== 'all' && ll.landlord_type !== typeFilter.value) return false
    return true
  })
  result = [...result].sort((a, b) => {
    let cmp = 0
    if (sortBy.value === 'name') cmp = a.name.localeCompare(b.name)
    else if (sortBy.value === 'profile') cmp = completionPct(a) - completionPct(b)
    else if (sortBy.value === 'properties') cmp = (a.property_count ?? 0) - (b.property_count ?? 0)
    return sortDir.value === 'asc' ? cmp : -cmp
  })
  return result
})

function completionPct(ll: Landlord): number {
  const hasAddress = !!(ll.address?.line1 || ll.address?.city)
  const needsRepresentative = ll.landlord_type !== 'individual'
  const checks = [
    !!ll.name,
    !!ll.email,
    !!ll.phone,
    !!ll.registration_number || !!ll.id_number,
    hasAddress,
    (ll.bank_accounts?.length ?? 0) > 0,
    !!ll.mandate_document,
    // Representative required for non-individual entities
    !needsRepresentative || !!ll.representative_name,
    !needsRepresentative || !!ll.representative_email,
    // VAT number required for companies and CCs
    !['company', 'cc'].includes(ll.landlord_type) || !!ll.vat_number,
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
}

function openLandlord(ll: Landlord) {
  router.push(`/landlords/${ll.id}`)
}


function openCreate() {
  createForm.value = { name: '', landlord_type: 'individual', registration_number: '', email: '', phone: '' }
  showCreate.value = true
}

async function createLandlord() {
  saving.value = true
  try {
    await landlordsStore.create(createForm.value as Partial<Landlord>)
    showCreate.value = false
    toast.success('Owner created')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to create owner'))
  } finally {
    saving.value = false
  }
}

</script>
