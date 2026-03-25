<template>
  <div class="flex flex-col h-screen bg-gray-50 overflow-hidden">
    <header class="bg-navy flex items-center h-14 px-6 flex-shrink-0 z-50 gap-6">
      <RouterLink to="/owner" class="flex items-center mr-4 flex-shrink-0">
        <span class="text-white font-bold text-xl leading-none whitespace-nowrap">Klikk<span class="text-pink-brand">.</span></span>
      </RouterLink>

      <nav class="flex items-center gap-1 flex-1 min-w-0">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
          :class="isActive(item.to)
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:text-white hover:bg-white/10'"
        >
          <component :is="item.icon" :size="15" class="flex-shrink-0" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="flex items-center gap-3 flex-shrink-0">
        <div class="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center text-white text-xs font-bold">
          {{ initials }}
        </div>
        <button @click="handleLogout"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors text-sm">
          <LogOut :size="15" />
        </button>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto p-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { LayoutDashboard, Building2, LogOut } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { to: '/owner',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/owner/properties', icon: Building2,       label: 'Properties' },
]

function isActive(to: string) {
  if (to === '/owner') return route.path === '/owner'
  return route.path.startsWith(to)
}

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'O'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
