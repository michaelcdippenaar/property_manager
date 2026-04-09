<template>
  <div class="space-y-5">
    <p class="text-sm text-gray-500">Browse and manage tenant profiles, contact details, and lease history.</p>
    <div class="card">
      <div class="px-4 pt-4 pb-0 border-b border-gray-100 flex items-center gap-4">
        <div class="flex gap-0">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="px-4 py-2.5 text-sm font-medium transition-colors relative"
            :class="activeTab === tab.key ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
            <span v-if="activeTab === tab.key" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
          </button>
        </div>
        <div class="ml-auto pb-2">
          <SearchInput v-model="search" placeholder="Search tenants…" />
        </div>
      </div>

      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 5" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <table v-else-if="filteredTenants.length" class="table-wrap">
        <thead>
          <tr>
            <th scope="col">Tenant</th>
            <th scope="col">Phone</th>
            <th scope="col">ID Number</th>
            <th scope="col">Joined</th>
            <th scope="col">Status</th>
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
        title="No tenants yet"
        description="Tenants are added when you create a lease. Build a lease to register your first tenant."
        :icon="Users"
      >
        <RouterLink to="/leases/build" class="btn-primary text-xs">
          <FilePlus2 :size="14" />
          Create lease
        </RouterLink>
      </EmptyState>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { RouterLink } from 'vue-router'
import { Users, FilePlus2 } from 'lucide-vue-next'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import { useToast } from '../../composables/useToast'
import { initials, formatDate } from '../../utils/formatters'
import { extractApiError } from '../../utils/api-errors'
import { usePersonsStore } from '../../stores/persons'

const toast = useToast()
const personsStore = usePersonsStore()
const { tenants, loading } = storeToRefs(personsStore)
const search = ref('')
const activeTab = ref<'all' | 'active' | 'inactive'>('all')

const tabs = [
  { key: 'all',      label: 'All' },
  { key: 'active',   label: 'Active' },
  { key: 'inactive', label: 'Inactive' },
]

onMounted(() => {
  personsStore.fetchTenants().catch((err) => toast.error(extractApiError(err, 'Failed to load tenants')))
})

const filteredTenants = computed(() => {
  let list = tenants.value
  if (activeTab.value === 'active')   list = list.filter(t => t.is_active)
  if (activeTab.value === 'inactive') list = list.filter(t => !t.is_active)
  const q = search.value.toLowerCase()
  if (q) list = list.filter(t =>
    (t.full_name ?? '').toLowerCase().includes(q) ||
    (t.email ?? '').toLowerCase().includes(q) ||
    (t.phone ?? '').includes(q) ||
    (t.id_number ?? '').includes(q)
  )
  return list
})

</script>
