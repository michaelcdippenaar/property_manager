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
              v-for="u in (p.units?.length ? p.units : [{ id: 0, unit_number: '—', status: p.property_active_lease_info ? 'occupied' : 'available', active_lease_info: p.property_active_lease_info ?? null }])"
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
                <span :class="{
                  'badge-green':  u.status === 'occupied' && u.active_lease_info?.status === 'active',
                  'badge-purple': u.status === 'occupied' && u.active_lease_info?.status === 'pending',
                  'badge-blue':   u.status === 'available',
                  'badge-amber':  u.status === 'maintenance',
                }">{{
                  u.status === 'occupied' && u.active_lease_info?.status === 'pending' ? 'Pending'
                  : u.status === 'occupied' ? 'Occupied'
                  : u.status === 'maintenance' ? 'Maintenance'
                  : 'Available'
                }}</span>
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

        <!-- Municipal bill upload -->
        <div class="border border-dashed border-gray-200 rounded-xl p-4 transition-colors"
             :class="parsingBill ? 'border-navy/30 bg-navy/5' : 'hover:border-navy/40'">
          <div class="flex items-center justify-between mb-1.5">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
              <Sparkles :size="12" /> Auto-fill from Municipal Bill
            </div>
            <span v-if="billFilename" class="text-[10px] text-gray-400 truncate max-w-[160px]">{{ billFilename }}</span>
          </div>
          <p class="text-xs text-gray-500 mb-2">Upload a rates bill — AI will extract the address, erf number, and property details.</p>
          <label class="btn-ghost btn-sm cursor-pointer inline-flex items-center gap-1.5"
                 :class="parsingBill ? 'pointer-events-none opacity-60' : ''">
            <Loader2 v-if="parsingBill" :size="12" class="animate-spin" />
            <Upload v-else :size="12" />
            {{ parsingBill ? 'Reading bill…' : 'Upload Municipal Bill' }}
            <input type="file" class="hidden" accept=".pdf,.jpg,.jpeg,.png" @change="parseMunicipalBill" />
          </label>
          <p v-if="billError" class="text-xs text-danger-600 mt-1.5 flex items-center gap-1">
            <AlertTriangle :size="11" /> {{ billError }}
          </p>
          <div v-if="billExtracted" class="mt-2 flex items-center gap-1.5 text-xs text-success-600">
            <CheckCircle2 :size="12" /> Fields auto-filled from {{ billFilename }}
          </div>
        </div>

        <div>
          <label class="label">Property name <span class="text-danger-500">*</span></label>
          <input v-model="newProperty.name" class="input" placeholder="18 Irene Park" required />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Type</label>
            <select v-model="newProperty.property_type" class="input">
              <option v-for="t in propertyTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
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
        <div>
          <label class="label">Owner (landlord)</label>
          <select v-model="newPropertyLandlordId" class="input">
            <option :value="null">— Select owner —</option>
            <option v-for="ll in landlords" :key="ll.id" :value="ll.id">{{ ll.name }}</option>
          </select>
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
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import BaseModal from '../../components/BaseModal.vue'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import AddressAutocomplete from '../../components/AddressAutocomplete.vue'
import type { AddressResult } from '../../components/AddressAutocomplete.vue'
import { extractApiError } from '../../utils/api-errors'
import { PROPERTY_TYPES, PROPERTY_TYPE_VALUES } from '../../constants/property'
import { useLandlordsStore } from '../../stores/landlords'
import { usePropertiesStore } from '../../stores/properties'
import { useOwnershipsStore } from '../../stores/ownerships'
import { AlertTriangle, CheckCircle2, Loader2, Plus, Building2, Sparkles, Trash2, Upload, Wrench } from 'lucide-vue-next'

const router = useRouter()

const toast = useToast()
const propertiesStore = usePropertiesStore()
const ownershipsStore = useOwnershipsStore()
const { list: properties, loading } = storeToRefs(propertiesStore)
const saving = ref(false)
const search = ref('')
const dialog = ref(false)
const propertyTypes = PROPERTY_TYPES
const propertyTypeValues = PROPERTY_TYPE_VALUES
const newProperty = ref({ name: '', property_type: 'apartment', address: '', city: '', province: '', postal_code: '' })
const selectedAddress = ref<AddressResult | null>(null)
const landlordsStore = useLandlordsStore()
const { list: landlords } = storeToRefs(landlordsStore)
const newPropertyLandlordId = ref<number | null>(null)
const deleteDialog = ref(false)
const deleting = ref(false)
const deletingProperty = ref<any>(null)

// Municipal bill parser
const parsingBill = ref(false)
const billError = ref('')
const billFilename = ref('')
const billExtracted = ref(false)

async function parseMunicipalBill(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  parsingBill.value = true
  billError.value = ''
  billExtracted.value = false
  billFilename.value = file.name
  try {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/properties/parse-municipal-bill/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const ext = data.extracted
    if (ext.property_name && !newProperty.value.name) newProperty.value.name = ext.property_name
    if (ext.address) newProperty.value.address = ext.address
    if (ext.city) newProperty.value.city = ext.city
    if (ext.province) newProperty.value.province = ext.province
    if (ext.postal_code) newProperty.value.postal_code = ext.postal_code
    if (ext.property_type && propertyTypeValues.includes(ext.property_type)) newProperty.value.property_type = ext.property_type
    billExtracted.value = true
  } catch (err: any) {
    billError.value = err?.response?.data?.detail || 'Failed to parse municipal bill.'
  } finally {
    parsingBill.value = false
    ;(e.target as HTMLInputElement).value = ''
  }
}

function onAddressSelect(addr: AddressResult) {
  selectedAddress.value = addr
  newProperty.value.address = addr.street || addr.formatted
  newProperty.value.city = addr.city
  newProperty.value.province = addr.province
  newProperty.value.postal_code = addr.postal_code
}
// Both lists flow through Pinia stores: cross-view mutations stay in sync
// reactively, the 30s staleness window dedupes navigation, and KeepAlive's
// stale-on-revisit problem is gone — no `onActivated` workaround needed.
onMounted(() => {
  propertiesStore.fetchAll().catch((err) => toast.error(extractApiError(err, 'Failed to load properties')))
  landlordsStore.fetchAll().catch((err) => toast.error(extractApiError(err, 'Failed to load owners')))
})

async function createProperty() {
  if (!newProperty.value.name) return

  // Validate landlord selection BEFORE the property is created so we never
  // end up with a dangling property if the ownership step would fail.
  let ownershipPayload: Record<string, unknown> | null = null
  if (newPropertyLandlordId.value) {
    const ll = landlords.value.find(l => l.id === newPropertyLandlordId.value)
    if (!ll) {
      toast.error('Selected owner could not be found. Please reselect.')
      return
    }
    if (!ll.name?.trim()) {
      toast.error('Selected owner has no name. Please update the owner first.')
      return
    }
    ownershipPayload = {
      landlord: newPropertyLandlordId.value,
      owner_name: ll.name,
      owner_type: ll.landlord_type === 'company' ? 'company' : ll.landlord_type === 'trust' ? 'trust' : 'individual',
      is_current: true,
      start_date: new Date().toISOString().slice(0, 10),
    }
  }

  saving.value = true
  try {
    const created = await propertiesStore.create(newProperty.value)

    if (ownershipPayload) {
      try {
        await ownershipsStore.create({ ...ownershipPayload, property: created.id } as any)
      } catch (ownershipErr) {
        // Ownership failed — roll back the property so we don't leave an orphan.
        try {
          await propertiesStore.remove(created.id)
        } catch {
          // Best-effort rollback; surface the original ownership error regardless.
        }
        throw ownershipErr
      }
    }

    dialog.value = false
    newProperty.value = { name: '', property_type: 'apartment', address: '', city: '', province: '', postal_code: '' }
    selectedAddress.value = null
    newPropertyLandlordId.value = null
    toast.success('Property created successfully')
    // The store has already upserted the new property; force a refetch so
    // unit_count + nested ownership data come back from the server.
    await propertiesStore.fetchAll({ force: true })
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to create property'))
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
    await propertiesStore.remove(id)
    deleteDialog.value = false
    deletingProperty.value = null
    toast.success('Property deleted')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete property'))
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
