<template>
  <div class="space-y-5">
    <h1 class="text-lg font-semibold text-gray-900">Tenants</h1>

    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <div class="relative max-w-xs">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input v-model="search" class="input pl-8" placeholder="Search tenants…" />
        </div>
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Tenant</th>
            <th>Phone</th>
            <th>ID Number</th>
            <th>Joined</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filteredTenants" :key="t.id">
            <td>
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {{ initials(t.full_name || t.email) }}
                </div>
                <div>
                  <div class="font-medium text-gray-900">{{ t.full_name || '—' }}</div>
                  <div class="text-xs text-gray-400">{{ t.email }}</div>
                </div>
              </div>
            </td>
            <td class="text-gray-600">{{ t.phone || '—' }}</td>
            <td class="text-gray-600 font-mono text-xs">{{ t.id_number || '—' }}</td>
            <td class="text-gray-500 text-xs">{{ formatDate(t.date_joined) }}</td>
            <td>
              <span :class="t.is_active ? 'badge-green' : 'badge-red'">
                {{ t.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
          </tr>
          <tr v-if="!filteredTenants.length">
            <td colspan="5" class="text-center text-gray-400 py-10">No tenants found</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { Search } from 'lucide-vue-next'

const loading = ref(true)
const search = ref('')
const tenants = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/tenants/')
    tenants.value = data.results ?? data
  } finally {
    loading.value = false
  }
})

const filteredTenants = computed(() =>
  tenants.value.filter(t =>
    (t.full_name ?? '').toLowerCase().includes(search.value.toLowerCase()) ||
    t.email.toLowerCase().includes(search.value.toLowerCase())
  )
)

function initials(name: string) {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}
function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
