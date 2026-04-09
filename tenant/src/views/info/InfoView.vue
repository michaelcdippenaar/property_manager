<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="InfoView">
    <AppHeader title="Your Unit" subtitle="Property information" />

    <div ref="scrollEl" class="scroll-page page-with-tab-bar px-4 pt-4 pb-4" @scroll="onScroll">
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 5" :key="i" class="h-14 bg-white rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="items.length === 0" class="flex flex-col items-center justify-center pt-20 text-center">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <Info :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No info available</p>
        <p class="text-sm text-gray-400 mt-1">Your agent hasn't added unit info yet</p>
      </div>

      <template v-else>
        <!-- Group by category if available -->
        <div v-for="group in grouped" :key="group.label">
          <p class="list-section-header px-1 pt-0 pb-1">{{ group.label }}</p>
          <div class="list-section">
            <div
              v-for="item in group.items"
              :key="item.id"
              class="list-row"
              :class="isSensitive(item) ? 'touchable' : ''"
              @click="isSensitive(item) ? toggleReveal(item.id) : undefined"
            >
              <div class="list-row-icon" :class="iconBg(item.icon_type)">
                <component :is="iconFor(item.icon_type)" :size="18" :class="iconColor(item.icon_type)" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">{{ item.label }}</p>
                <p class="text-sm font-medium text-gray-900 font-mono">
                  {{ revealed.has(item.id) ? item.value : maskedValue(item) }}
                </p>
              </div>
              <Eye v-if="isSensitive(item) && !revealed.has(item.id)" :size="16" class="text-gray-300 flex-shrink-0" />
              <EyeOff v-else-if="isSensitive(item) && revealed.has(item.id)" :size="16" class="text-gray-300 flex-shrink-0" />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Info, Wifi, Zap, Droplets, Lock, Shield, Eye, EyeOff, Flame, Building2 } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'

const items = ref<any[]>([])
const loading = ref(true)
const revealed = ref(new Set<number>())
const scrollEl = ref<HTMLElement | null>(null)

const SENSITIVE = new Set(['wifi', 'alarm', 'gate', 'key', 'code', 'password'])

function isSensitive(item: any) {
  return SENSITIVE.has(item.icon_type?.toLowerCase()) || item.is_sensitive
}
function maskedValue(item: any) {
  return isSensitive(item) ? '••••••••' : item.value
}
function toggleReveal(id: number) {
  if (revealed.value.has(id)) revealed.value.delete(id)
  else revealed.value.add(id)
  revealed.value = new Set(revealed.value) // trigger reactivity
}

const ICON_MAP: Record<string, any> = {
  wifi: Wifi, electricity: Zap, water: Droplets, alarm: Shield,
  gate: Lock, key: Lock, gas: Flame, default: Building2,
}
function iconFor(type: string) { return ICON_MAP[type] ?? ICON_MAP.default }
function iconBg(type: string) {
  return { wifi: 'bg-blue-50', electricity: 'bg-yellow-50', water: 'bg-cyan-50', alarm: 'bg-red-50', gate: 'bg-navy/8', gas: 'bg-orange-50' }[type] ?? 'bg-gray-100'
}
function iconColor(type: string) {
  return { wifi: 'text-blue-500', electricity: 'text-yellow-500', water: 'text-cyan-500', alarm: 'text-red-500', gate: 'text-navy', gas: 'text-orange-500' }[type] ?? 'text-gray-500'
}

const grouped = computed(() => {
  const map = new Map<string, any[]>()
  for (const item of items.value) {
    const cat = item.category || 'General'
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat)!.push(item)
  }
  return Array.from(map.entries()).map(([label, items]) => ({ label, items }))
})

function onScroll() {}

onMounted(async () => {
  try {
    const res = await api.get('/properties/unit-info/')
    items.value = res.data.results ?? res.data
  } finally {
    loading.value = false
  }
})
</script>
