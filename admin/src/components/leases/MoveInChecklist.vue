<template>
  <div class="space-y-3">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-gray-900">Move-in prep</h3>
        <p class="text-xs text-gray-400 mt-0.5">{{ completedCount }}/{{ items.length }} completed</p>
      </div>
      <div v-if="allDone" class="flex items-center gap-1.5 text-xs font-medium text-green-600">
        <CheckCircle2 :size="14" />
        All done
      </div>
    </div>

    <!-- Skeleton while loading -->
    <div v-if="loading" class="space-y-2">
      <div v-for="i in 4" :key="i" class="h-12 rounded-xl bg-gray-100 animate-pulse" />
    </div>

    <!-- Checklist items -->
    <div v-else class="space-y-2">
      <div
        v-for="item in items"
        :key="item.key"
        class="flex items-start gap-3 rounded-xl px-3 py-2.5 border transition-colors"
        :class="item.is_completed
          ? 'bg-green-50 border-green-100'
          : 'bg-white border-gray-100 hover:border-gray-200'"
      >
        <!-- Checkbox / tick button -->
        <button
          type="button"
          class="mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
          :class="[
            item.is_completed ? 'bg-green-500 hover:bg-green-600' : 'bg-gray-100 hover:bg-gray-200',
            isReadOnly ? 'cursor-default' : 'cursor-pointer',
          ]"
          :disabled="isReadOnly || toggling === item.key"
          @click="toggleItem(item)"
        >
          <Check v-if="item.is_completed" :size="11" class="text-white" />
          <Loader2
            v-else-if="toggling === item.key"
            :size="11"
            class="text-gray-400 animate-spin"
          />
          <span v-else class="block w-2 h-2 rounded-full bg-gray-300" />
        </button>

        <!-- Label + who/when -->
        <div class="flex-1 min-w-0">
          <p
            class="text-sm font-medium"
            :class="item.is_completed ? 'text-green-700 line-through opacity-70' : 'text-gray-800'"
          >
            {{ item.key_label }}
          </p>
          <p v-if="item.is_completed && item.completed_at" class="text-micro text-gray-400 mt-0.5">
            {{ formatWho(item) }}
          </p>
        </div>

        <!-- Untick button for agents -->
        <button
          v-if="item.is_completed && !isReadOnly"
          type="button"
          class="flex-shrink-0 text-micro text-gray-300 hover:text-gray-400 transition-colors"
          :disabled="toggling === item.key"
          @click="toggleItem(item)"
        >
          Undo
        </button>
      </div>
    </div>

    <!-- Error -->
    <p v-if="error" class="text-xs text-red-500">{{ error }}</p>

    <!-- Incoming inspection placeholder -->
    <div class="mt-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-3 flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
        <Camera :size="15" class="text-gray-400" />
      </div>
      <div>
        <p class="text-sm font-medium text-gray-500">Incoming inspection</p>
        <p class="text-xs text-gray-400">Coming soon — photo evidence + condition report</p>
      </div>
      <span class="ml-auto text-micro font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Planned</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Check, CheckCircle2, Loader2, Camera } from 'lucide-vue-next'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

interface ChecklistItem {
  id: number
  key: string
  key_label: string
  is_completed: boolean
  completed_by: number | null
  completed_by_name: string | null
  completed_at: string | null
}

const props = defineProps<{
  leaseId: number
}>()

const authStore = useAuthStore()

const items = ref<ChecklistItem[]>([])
const loading = ref(true)
const toggling = ref<string | null>(null)
const error = ref<string | null>(null)

// Owner role is read-only — backend enforces this too, but we reflect it in the UI
const isReadOnly = computed(() => authStore.isOwner)

const completedCount = computed(() => items.value.filter(i => i.is_completed).length)
const allDone = computed(() => items.value.length > 0 && completedCount.value === items.value.length)

async function fetchChecklist() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get(`/leases/${props.leaseId}/move-in-checklist/`)
    items.value = data
  } catch {
    error.value = 'Could not load move-in checklist.'
  } finally {
    loading.value = false
  }
}

async function toggleItem(item: ChecklistItem) {
  if (isReadOnly.value || toggling.value) return
  toggling.value = item.key
  error.value = null
  try {
    const { data } = await api.patch(
      `/leases/${props.leaseId}/move-in-checklist/${item.key}/`,
      { is_completed: !item.is_completed },
    )
    const idx = items.value.findIndex(i => i.key === item.key)
    if (idx !== -1) items.value[idx] = data
  } catch {
    error.value = 'Failed to update item. Please try again.'
  } finally {
    toggling.value = null
  }
}

function formatWho(item: ChecklistItem): string {
  const parts: string[] = []
  if (item.completed_by_name) parts.push(`by ${item.completed_by_name}`)
  if (item.completed_at) {
    try {
      const d = new Intl.DateTimeFormat('en-ZA', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      }).format(new Date(item.completed_at))
      parts.push(d)
    } catch {
      parts.push(item.completed_at)
    }
  }
  return parts.join(' — ')
}

onMounted(fetchChecklist)

// Reload if leaseId changes (component reuse scenario)
watch(() => props.leaseId, fetchChecklist)
</script>
