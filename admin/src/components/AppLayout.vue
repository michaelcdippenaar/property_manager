<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">

    <!-- Sidebar -->
    <aside
      class="flex flex-col flex-shrink-0 transition-all duration-200 bg-navy"
      :class="collapsed ? 'w-16' : 'w-56'"
    >
      <!-- Logo -->
      <div class="flex items-center gap-3 px-4 h-14 border-b border-white/10 overflow-hidden">
        <span class="text-white font-bold text-xl leading-none flex-shrink-0">K<span class="text-pink-brand">.</span></span>
        <span v-if="!collapsed" class="text-white font-bold text-lg leading-none whitespace-nowrap">Klikk<span class="text-pink-brand">.</span></span>
      </div>

      <!-- Nav items -->
      <nav class="flex-1 px-2 py-4 space-y-1 overflow-hidden">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-2 py-2 rounded-lg transition-colors text-sm font-medium group"
          :class="isActive(item.to)
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:text-white hover:bg-white/10'"
        >
          <component :is="item.icon" class="flex-shrink-0" :size="18" />
          <span v-if="!collapsed" class="whitespace-nowrap">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- Logout -->
      <div class="px-2 py-4 border-t border-white/10">
        <button
          @click="handleLogout"
          class="flex items-center gap-3 w-full px-2 py-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors text-sm font-medium"
        >
          <LogOut :size="18" class="flex-shrink-0" />
          <span v-if="!collapsed">Logout</span>
        </button>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex flex-col flex-1 min-w-0">
      <!-- Topbar -->
      <header class="flex items-center gap-4 h-14 px-5 bg-white border-b border-gray-200 flex-shrink-0">
        <button
          @click="collapsed = !collapsed"
          class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
        >
          <Menu :size="18" />
        </button>
        <h1 class="text-sm font-semibold text-gray-800 flex-1">{{ currentTitle }}</h1>
        <div
          class="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
        >
          {{ initials }}
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  LayoutDashboard, Building2, Users, Wrench, FileText, LogOut, Menu,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)

const navItems = [
  { to: '/',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties',  icon: Building2,       label: 'Properties' },
  { to: '/tenants',     icon: Users,           label: 'Tenants' },
  { to: '/maintenance', icon: Wrench,          label: 'Maintenance' },
  { to: '/leases',      icon: FileText,        label: 'Leases' },
]

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

const currentTitle = computed(() => {
  const item = navItems.find(n => isActive(n.to))
  return item?.label ?? 'Klikk Admin'
})

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'A'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
