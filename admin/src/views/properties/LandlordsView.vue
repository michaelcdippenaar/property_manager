<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Manage owners, their properties, and bank accounts.</p>
      <button class="btn-primary flex-shrink-0" @click="openCreate">
        <Plus :size="15" /> Add Owner
      </button>
    </div>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <SearchInput v-model="search" placeholder="Search owners…" />
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else-if="filteredLandlords.length" class="table-wrap">
        <thead>
          <tr>
            <th scope="col">Owner</th>
            <th scope="col">Type</th>
            <th scope="col">Profile</th>
            <th scope="col">Email</th>
            <th scope="col" class="text-right">Properties</th>
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
            <td><span class="badge-gray capitalize">{{ ll.landlord_type }}</span></td>
            <td>
              <div class="flex items-center gap-2">
                <div class="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="completionPct(ll) >= 100 ? 'bg-success-500' : completionPct(ll) >= 60 ? 'bg-navy' : 'bg-warning-400'"
                    :style="`width:${completionPct(ll)}%`"
                  />
                </div>
                <span class="text-xs tabular-nums" :class="completionPct(ll) >= 100 ? 'text-success-600 font-medium' : 'text-gray-400'">{{ completionPct(ll) }}%</span>
              </div>
            </td>
            <td class="text-gray-600">{{ ll.email || '—' }}</td>
            <td class="text-right text-gray-600">{{ ll.property_count ?? 0 }}</td>
            <td class="text-right pr-3">
              <ChevronRight :size="14" class="text-accent group-hover:text-accent transition-colors" />
            </td>
          </tr>
        </tbody>
      </table>

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

    <!-- Detail drawer -->
    <LandlordDrawer
      :open="drawerOpen"
      :landlord="selectedLandlord"
      @close="drawerOpen = false"
      @saved="onDrawerSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Briefcase, Building2, ChevronRight, Loader2, Plus, Shield, User, UserCheck, Users } from 'lucide-vue-next'
import api from '../../api'
import BaseModal from '../../components/BaseModal.vue'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import LandlordDrawer from './LandlordDrawer.vue'

const router = useRouter()

const landlords = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const showCreate = ref(false)
const drawerOpen = ref(false)
const selectedLandlord = ref<any>(null)

const createForm = ref({
  name: '',
  landlord_type: 'individual',
  registration_number: '',
  email: '',
  phone: '',
})

onMounted(() => loadLandlords())

async function loadLandlords() {
  loading.value = true
  try {
    const { data } = await api.get('/properties/landlords/')
    landlords.value = (data.results ?? data).map((ll: any) => ({
      ...ll,
      address: ll.address && typeof ll.address === 'object' ? ll.address : {},
    }))
  } finally {
    loading.value = false
  }
}

const filteredLandlords = computed(() =>
  landlords.value.filter(ll =>
    ll.name.toLowerCase().includes(search.value.toLowerCase()) ||
    (ll.email ?? '').toLowerCase().includes(search.value.toLowerCase())
  )
)

function completionPct(ll: any): number {
  const checks = [
    !!ll.name,
    !!ll.email,
    !!ll.phone,
    !!ll.registration_number || !!ll.id_number,
    (ll.bank_accounts?.length ?? 0) > 0,
    (ll.property_count ?? 0) > 0,
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
}

function openLandlord(ll: any) {
  router.push(`/landlords/${ll.id}`)
}

function openCreate() {
  createForm.value = { name: '', landlord_type: 'individual', registration_number: '', email: '', phone: '' }
  showCreate.value = true
}

async function createLandlord() {
  saving.value = true
  try {
    await api.post('/properties/landlords/', createForm.value)
    showCreate.value = false
    await loadLandlords()
  } finally {
    saving.value = false
  }
}

async function onDrawerSaved() {
  await loadLandlords()
  // Update the selected landlord with fresh data
  if (selectedLandlord.value) {
    const fresh = landlords.value.find(ll => ll.id === selectedLandlord.value.id)
    if (fresh) {
      selectedLandlord.value = fresh
    } else {
      drawerOpen.value = false
    }
  }
}
</script>
