<template>
  <div class="space-y-5">
    <p class="text-sm text-gray-500">Browse and manage tenant profiles, contact details, and lease history.</p>
    <div class="card">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100">
        <SearchInput v-model="search" placeholder="Search tenants…" />
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else-if="filteredTenants.length" class="table-wrap">
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
        </tbody>
      </table>

      <EmptyState
        v-else
        title="No tenants found"
        description="Tenants will appear here once they are added to a property."
        :icon="Users"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Users } from 'lucide-vue-next'
import api from '../../api'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import { useToast } from '../../composables/useToast'

const toast = useToast()
const loading = ref(true)
const search = ref('')
const tenants = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/tenants/')
    tenants.value = data.results ?? data
  } catch {
    toast.error('Failed to load tenants')
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
