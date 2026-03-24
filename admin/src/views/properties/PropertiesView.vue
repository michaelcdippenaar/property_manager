<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-gray-900">Properties</h1>
      <button class="btn-primary" @click="dialog = true">
        <Plus :size="15" /> Add Property
      </button>
    </div>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <div class="relative max-w-xs">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input v-model="search" class="input pl-8" placeholder="Search properties…" />
        </div>
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Property</th>
            <th>Type</th>
            <th>City</th>
            <th>Units</th>
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
            <td class="text-gray-600">{{ p.unit_count ?? 0 }}</td>
            <td class="min-w-[100px]">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full bg-navy rounded-full" :style="`width:${occupancyPercent(p)}%`" />
                </div>
                <span class="text-xs text-gray-400">{{ occupancyPercent(p) }}%</span>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredProperties.length">
            <td colspan="5" class="text-center text-gray-400 py-10">No properties found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add Property Dialog -->
    <Teleport to="body">
      <div v-if="dialog" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="dialog = false" />
        <div class="relative card w-full max-w-md p-6 space-y-4">
          <div class="flex items-center justify-between mb-2">
            <h2 class="font-semibold text-gray-900">Add Property</h2>
            <button @click="dialog = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <div>
            <label class="label">Property name</label>
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

          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="dialog = false">Cancel</button>
            <button class="btn-primary" :disabled="saving" @click="createProperty">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              Save Property
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { Plus, Search, X, Loader2 } from 'lucide-vue-next'

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
    await loadProperties()
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
