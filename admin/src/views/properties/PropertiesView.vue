<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Manage your property portfolio, units, and occupancy.</p>
      <button class="btn-primary flex-shrink-0" @click="dialog = true">
        <Plus :size="15" /> Add Property
      </button>
    </div>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <SearchInput v-model="search" placeholder="Search properties…" />
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else-if="filteredProperties.length" class="table-wrap">
        <thead>
          <tr>
            <th scope="col">Unit</th>
            <th scope="col">Tenant</th>
            <th scope="col">Status</th>
            <th scope="col">Lease Expiry</th>
            <th scope="col">Maintenance</th>
            <th scope="col" class="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="p in filteredProperties" :key="p.id">
            <tr
              v-for="u in (p.units?.length ? p.units : [{ id: 0, unit_number: '—', status: 'available', active_lease_info: null }])"
              :key="`${p.id}-${u.id}`"
              class="cursor-pointer hover:bg-gray-50"
              @click="router.push(`/properties/${p.id}`)"
            >
              <td>
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
                    <img v-if="p.cover_photo" :src="p.cover_photo" class="w-full h-full object-cover" :alt="p.name" />
                    <div v-else class="w-full h-full flex items-center justify-center">
                      <Building2 :size="18" class="text-gray-300" />
                    </div>
                  </div>
                  <div class="min-w-0">
                    <div class="font-medium text-gray-900">{{ p.address || p.name }}<span v-if="u.unit_number && u.unit_number !== '—'" class="text-gray-500 font-normal">, {{ u.unit_number }}</span></div>
                    <div class="text-xs text-gray-400 mt-0.5 truncate">{{ p.city }}<span v-if="p.province">, {{ p.province }}</span></div>
                  </div>
                </div>
              </td>
              <td>
                <template v-if="u.active_lease_info?.tenant_name">
                  <div class="text-sm text-gray-900">{{ u.active_lease_info.tenant_name }}</div>
                  <div class="text-xs text-gray-400">R{{ Number(u.active_lease_info.monthly_rent).toLocaleString('en-ZA', { maximumFractionDigits: 0 }) }}/mo</div>
                </template>
                <span v-else class="text-xs text-gray-300">Vacant</span>
              </td>
              <td>
                <span
                  class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-success-50 text-success-700': u.status === 'occupied',
                    'bg-info-50 text-info-600': u.status === 'available',
                    'bg-warning-50 text-warning-600': u.status === 'maintenance',
                  }"
                >{{ u.status === 'occupied' ? 'Occupied' : u.status === 'maintenance' ? 'Maintenance' : 'Available' }}</span>
              </td>
              <td class="min-w-[140px]">
                <template v-if="u.active_lease_info">
                  <div class="flex items-center gap-2">
                    <span
                      class="text-xs font-semibold px-2 py-0.5 rounded-full"
                      :class="expiryBadge(u.active_lease_info.end_date)"
                    >{{ daysUntil(u.active_lease_info.end_date) }}d</span>
                    <span class="text-xs text-gray-500">{{ leasePct(u.active_lease_info) }}%</span>
                  </div>
                  <div class="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all"
                      :class="leasePct(u.active_lease_info) >= 90 ? 'bg-danger-400' : leasePct(u.active_lease_info) >= 75 ? 'bg-warning-400' : 'bg-navy'"
                      :style="`width:${leasePct(u.active_lease_info)}%`"
                    />
                  </div>
                  <div class="text-[10px] text-gray-400 mt-0.5">{{ fmtDate(u.active_lease_info.end_date) }}</div>
                </template>
                <span v-else class="text-xs text-gray-300">No lease</span>
              </td>
              <td>
                <span
                  v-if="u.open_maintenance_count > 0"
                  class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-danger-50 text-danger-600"
                >
                  <Wrench :size="11" />
                  {{ u.open_maintenance_count }}
                </span>
                <span v-else class="text-xs text-gray-300">—</span>
              </td>
              <td class="text-right">
                <button
                  class="btn-ghost btn-xs text-danger-500 hover:bg-danger-50"
                  aria-label="Delete property"
                  @click.stop="confirmDelete(p)"
                >
                  <Trash2 :size="14" />
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <EmptyState
        v-else
        title="No properties found"
        description="Add your first property to get started managing your portfolio."
        :icon="Building2"
      >
        <button class="btn-primary btn-sm" @click="dialog = true">
          <Plus :size="14" /> Add Property
        </button>
      </EmptyState>
    </div>

    <!-- Add Property Dialog -->
    <BaseModal :open="dialog" title="Add Property" @close="dialog = false">
      <div class="space-y-4">
        <div>
          <label class="label">Property name <span class="text-danger-500">*</span></label>
          <input v-model="newProperty.name" class="input" placeholder="18 Irene Park" required />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Type</label>
            <select v-model="newProperty.property_type" class="input">
              <option v-for="t in propertyTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div>
            <label class="label">City</label>
            <input v-model="newProperty.city" class="input" placeholder="Stellenbosch" />
          </div>
        </div>
        <div>
          <label class="label">Address</label>
          <AddressAutocomplete
            :model-value="selectedAddress"
            placeholder="Start typing an address…"
            @select="onAddressSelect"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Province</label>
            <input v-model="newProperty.province" class="input" placeholder="Western Cape" />
          </div>
          <div>
            <label class="label">Postal code</label>
            <input v-model="newProperty.postal_code" class="input" placeholder="7600" />
          </div>
        </div>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="dialog = false">Cancel</button>
        <button class="btn-primary" :disabled="saving || !newProperty.name" @click="createProperty">
          <Loader2 v-if="saving" :size="14" class="animate-spin" />
          Save Property
        </button>
      </template>
    </BaseModal>

    <!-- Delete confirmation -->
    <BaseModal :open="deleteDialog" title="Delete property?" @close="deleteDialog = false">
      <p class="text-sm text-gray-600">
        Are you sure you want to delete <strong>{{ deletingProperty?.name }}</strong>? This will remove all units, leases, and documents associated with this property. This action cannot be undone.
      </p>
      <template #footer>
        <button class="btn-ghost" @click="deleteDialog = false">Cancel</button>
        <button class="btn-danger" :disabled="deleting" @click="doDelete">
          <Loader2 v-if="deleting" :size="14" class="animate-spin" />
          Delete property
        </button>
      </template>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import BaseModal from '../../components/BaseModal.vue'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import AddressAutocomplete from '../../components/AddressAutocomplete.vue'
import type { AddressResult } from '../../components/AddressAutocomplete.vue'
import { Plus, Building2, Loader2, Trash2, Wrench } from 'lucide-vue-next'

const router = useRouter()

const toast = useToast()
const loading = ref(true)
const saving = ref(false)
const search = ref('')
const dialog = ref(false)
const properties = ref<any[]>([])
const propertyTypes = ['apartment', 'house', 'townhouse', 'commercial']
const newProperty = ref({ name: '', property_type: 'apartment', address: '', city: '', province: '', postal_code: '' })
const selectedAddress = ref<AddressResult | null>(null)
const deleteDialog = ref(false)
const deleting = ref(false)
const deletingProperty = ref<any>(null)

function onAddressSelect(addr: AddressResult) {
  selectedAddress.value = addr
  newProperty.value.address = addr.street || addr.formatted
  newProperty.value.city = addr.city
  newProperty.value.province = addr.province
  newProperty.value.postal_code = addr.postal_code
}
onMounted(() => loadProperties())

async function loadProperties() {
  loading.value = true
  try {
    const { data } = await api.get('/properties/')
    properties.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function createProperty() {
  if (!newProperty.value.name) return
  saving.value = true
  try {
    await api.post('/properties/', newProperty.value)
    dialog.value = false
    newProperty.value = { name: '', property_type: 'apartment', address: '', city: '', province: '', postal_code: '' }
    selectedAddress.value = null
    toast.success('Property created successfully')
    await loadProperties()
  } catch {
    toast.error('Failed to create property')
  } finally {
    saving.value = false
  }
}

const filteredProperties = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return properties.value
  return properties.value.filter(p =>
    p.name.toLowerCase().includes(q) ||
    (p.address ?? '').toLowerCase().includes(q) ||
    (p.city ?? '').toLowerCase().includes(q) ||
    p.units?.some((u: any) => u.unit_number?.toLowerCase().includes(q))
  )
})

function confirmDelete(p: any) {
  deletingProperty.value = p
  deleteDialog.value = true
}

async function doDelete() {
  if (!deletingProperty.value) return
  deleting.value = true
  const id = deletingProperty.value.id
  try {
    await api.delete(`/properties/${id}/`)
    properties.value = properties.value.filter(p => p.id !== id)
    deleteDialog.value = false
    deletingProperty.value = null
    toast.success('Property deleted')
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.response?.data?.message || 'Failed to delete property'
    toast.error(typeof msg === 'string' ? msg : 'Failed to delete property')
  } finally {
    deleting.value = false
  }
}

function occupancyPercent(p: any) {
  if (!p.unit_count) return 0
  const occupied = p.units?.filter((u: any) => u.status === 'occupied').length ?? 0
  return Math.round((occupied / p.unit_count) * 100)
}

function daysUntil(iso: string): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000))
}

function leasePct(lease: { start_date: string; end_date: string }): number {
  const start = new Date(lease.start_date).getTime()
  const end = new Date(lease.end_date).getTime()
  if (end <= start) return 100
  return Math.min(100, Math.max(0, Math.round(((Date.now() - start) / (end - start)) * 100)))
}

function expiryBadge(iso: string): string {
  const d = daysUntil(iso)
  if (d <= 30) return 'bg-danger-50 text-danger-600'
  if (d <= 90) return 'bg-warning-50 text-warning-600'
  return 'bg-success-50 text-success-700'
}

function fmtDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-ZA', { dateStyle: 'medium' })
}
</script>
