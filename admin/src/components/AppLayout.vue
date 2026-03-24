<template>
  <div class="flex flex-col h-screen bg-gray-50 overflow-hidden">

    <!-- Top nav -->
    <header class="bg-navy flex items-center h-14 px-6 flex-shrink-0 z-50 gap-6">

      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-1.5 mr-4 flex-shrink-0">
        <span class="text-white font-bold text-xl leading-none">K<span class="text-pink-brand">.</span></span>
        <span class="text-white font-bold text-lg leading-none whitespace-nowrap">Klikk<span class="text-pink-brand">.</span></span>
      </RouterLink>

      <!-- Primary nav -->
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

      <!-- Right: user + logout -->
      <div class="flex items-center gap-3 flex-shrink-0">
        <div class="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center text-white text-xs font-bold">
          {{ initials }}
        </div>
        <button
          @click="handleLogout"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors text-sm"
        >
          <LogOut :size="15" />
        </button>
      </div>
    </header>

    <!-- Page content -->
    <main class="flex-1 overflow-y-auto p-6">
      <RouterView />
    </main>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  LayoutDashboard, Building2, Users, Wrench, Truck, FileText, LogOut,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { to: '/',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties',  icon: Building2,       label: 'Properties' },
  { to: '/tenants',     icon: Users,           label: 'Tenants' },
  { to: '/maintenance', icon: Wrench,          label: 'Maintenance' },
  { to: '/suppliers',   icon: Truck,           label: 'Suppliers' },
  { to: '/leases',      icon: FileText,        label: 'Leases' },
]

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'A'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
