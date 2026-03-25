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
            <th>Property</th>
            <th>Type</th>
            <th>City</th>
            <th class="text-right">Units</th>
            <th>Occupancy</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in filteredProperties" :key="p.id">
            <td>
              <div class="font-medium text-gray-900">{{ p.name }}</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ p.address }}</div>
            </td>
            <td><span class="badge-gray capitalize">{{ p.property_type }}</span></td>
            <td class="text-gray-600">{{ p.city }}</td>
            <td class="text-right text-gray-600">{{ p.unit_count ?? 0 }}</td>
            <td class="min-w-[120px]">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full bg-navy rounded-full transition-all" :style="`width:${occupancyPercent(p)}%`" />
                </div>
                <span class="text-xs text-gray-500 w-8 text-right">{{ occupancyPercent(p) }}%</span>
              </div>
            </td>
          </tr>
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
          <input v-model="newProperty.address" class="input" placeholder="18 Irene Park Road, La Colline" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import BaseModal from '../../components/BaseModal.vue'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import { Plus, Building2, Loader2 } from 'lucide-vue-next'

const toast = useToast()
const loading = ref(true)
const saving = ref(false)
const search = ref('')
const dialog = ref(false)
const properties = ref<any[]>([])
const propertyTypes = ['apartment', 'house', 'townhouse', 'commercial']
const newProperty = ref({ name: '', property_type: 'apartment', address: '', city: '', province: '', postal_code: '' })

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
    toast.success('Property created successfully')
    await loadProperties()
  } catch {
    toast.error('Failed to create property')
  } finally {
    saving.value = false
  }
}

const filteredProperties = computed(() =>
  properties.value.filter(p =>
    p.name.toLowerCase().includes(search.value.toLowerCase()) ||
    (p.city ?? '').toLowerCase().includes(search.value.toLowerCase())
  )
)

function occupancyPercent(p: any) {
  if (!p.unit_count) return 0
  const occupied = p.units?.filter((u: any) => u.status === 'occupied').length ?? 0
  return Math.round((occupied / p.unit_count) * 100)
}
</script>
