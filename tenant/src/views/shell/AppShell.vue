<template>
  <div class="h-dvh flex flex-col overflow-hidden bg-surface">
    <!-- Tab content — fills available space above tab bar -->
    <div class="flex-1 overflow-hidden relative">
      <RouterView v-slot="{ Component, route }">
        <KeepAlive :include="['HomeView', 'IssuesView', 'InfoView', 'SettingsView']">
          <component :is="Component" :key="route.name" class="absolute inset-0 h-full" />
        </KeepAlive>
      </RouterView>
    </div>

    <!-- Bottom tab bar -->
    <nav class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="tab-item"
        :class="isActive(tab.name) ? 'tab-item-active' : ''"
        @click="router.push({ name: tab.name })"
      >
        <component :is="tab.icon" :size="24" :stroke-width="isActive(tab.name) ? 2.2 : 1.6" />
        <span class="text-[10px] font-medium">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Home, Wrench, Info, Settings } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const tabs = [
  { name: 'home',     label: 'Home',     icon: Home },
  { name: 'issues',   label: 'Repairs',  icon: Wrench },
  { name: 'info',     label: 'Info',     icon: Info },
  { name: 'settings', label: 'Settings', icon: Settings },
]

const activeTab = computed(() => route.name as string)
function isActive(name: string) { return activeTab.value === name }
</script>
