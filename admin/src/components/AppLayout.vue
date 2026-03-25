<template>
  <div class="flex h-screen bg-surface overflow-hidden">

    <!-- ── Sidebar ── -->
    <aside
      class="flex flex-col bg-white border-r border-gray-200 flex-shrink-0 transition-all duration-200 z-40"
      :class="collapsed ? 'w-[60px]' : 'w-56'"
    >
      <!-- Logo + collapse toggle -->
      <div class="flex items-center h-14 px-3 border-b border-gray-100 flex-shrink-0">
        <RouterLink to="/" class="flex items-center gap-2 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-navy flex items-center justify-center flex-shrink-0">
            <span class="text-white font-bold text-sm">K</span>
          </div>
          <span v-if="!collapsed" class="font-bold text-gray-900 text-sm truncate">
            Klikk<span class="text-accent">.</span>
          </span>
        </RouterLink>
        <button
          @click="collapsed = !collapsed"
          class="ml-auto p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
          :class="collapsed ? 'mx-auto' : ''"
        >
          <component :is="collapsed ? ChevronsRight : ChevronsLeft" :size="16" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-3 px-2 space-y-5">
        <!-- Primary -->
        <div>
          <div v-if="!collapsed" class="sidebar-section-label">Main</div>
          <div class="space-y-0.5">
            <RouterLink
              v-for="item in primaryNavItems"
              :key="item.to"
              :to="item.to"
              class="sidebar-link"
              :class="[isActive(item.to) ? 'sidebar-link-active' : '', collapsed ? 'justify-center px-0' : '']"
              :title="collapsed ? item.label : undefined"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <!-- Leases -->
        <div>
          <div v-if="!collapsed" class="sidebar-section-label">Leases</div>
          <div class="space-y-0.5">
            <RouterLink
              v-for="item in leaseSubItems"
              :key="item.to"
              :to="item.to"
              class="sidebar-link"
              :class="[isActive(item.to) ? 'sidebar-link-active' : '', collapsed ? 'justify-center px-0' : '']"
              :title="collapsed ? item.label : undefined"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <!-- Maintenance -->
        <div>
          <div v-if="!collapsed" class="sidebar-section-label">Maintenance</div>
          <div class="space-y-0.5">
            <RouterLink
              v-for="item in maintenanceSubItems"
              :key="item.to"
              :to="item.to"
              class="sidebar-link"
              :class="[isActive(item.to) ? 'sidebar-link-active' : '', collapsed ? 'justify-center px-0' : '']"
              :title="collapsed ? item.label : undefined"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <!-- Life Cycle -->
        <div>
          <div v-if="!collapsed" class="sidebar-section-label">Life Cycle</div>
          <div class="space-y-0.5">
            <RouterLink
              v-for="item in lifecycleItems"
              :key="item.to"
              :to="item.to"
              class="sidebar-link"
              :class="[isActive(item.to) ? 'sidebar-link-active' : '', collapsed ? 'justify-center px-0' : '']"
              :title="collapsed ? item.label : undefined"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>

        <!-- Setup -->
        <div>
          <div v-if="!collapsed" class="sidebar-section-label">Setup</div>
          <div class="space-y-0.5">
            <RouterLink
              v-for="item in propertyInfoSubItems"
              :key="item.to"
              :to="item.to"
              class="sidebar-link"
              :class="[isActive(item.to) ? 'sidebar-link-active' : '', collapsed ? 'justify-center px-0' : '']"
              :title="collapsed ? item.label : undefined"
            >
              <component :is="item.icon" :size="18" class="flex-shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- User + Logout at bottom -->
      <div class="border-t border-gray-100 p-2 flex-shrink-0">
        <div
          class="flex items-center gap-2.5 px-2 py-2 rounded-lg"
          :class="collapsed ? 'justify-center' : ''"
        >
          <div class="w-8 h-8 rounded-full bg-navy flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {{ initials }}
          </div>
          <div v-if="!collapsed" class="min-w-0 flex-1">
            <div class="text-sm font-medium text-gray-900 truncate">{{ auth.user?.full_name || 'Admin' }}</div>
            <div class="text-xs text-gray-400 truncate">{{ auth.user?.email }}</div>
          </div>
          <button
            @click="handleLogout"
            class="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0"
            :title="collapsed ? 'Logout' : undefined"
          >
            <LogOut :size="16" />
          </button>
        </div>
      </div>
    </aside>

    <!-- ── Main content ── -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Top bar -->
      <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6 flex-shrink-0 gap-4">
        <h1 class="text-lg font-semibold text-gray-900">{{ currentPageTitle }}</h1>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView v-slot="{ Component }">
          <KeepAlive>
            <component :is="Component" />
          </KeepAlive>
        </RouterView>
      </main>
    </div>

    <!-- Toast notifications -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ToastContainer from './ToastContainer.vue'
import {
  LayoutDashboard, Building2, Users, Wrench, FileText, FileSignature, Calendar,
  LogOut, Sparkles, BookOpen, Info, ChevronsLeft, ChevronsRight, Truck, Hammer, Send,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)

const primaryNavItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties', icon: Building2, label: 'Properties' },
  { to: '/tenants', icon: Users, label: 'Tenants' },
]

const leaseSubItems = [
  { to: '/leases', icon: FileText, label: 'All Leases' },
  { to: '/leases/templates', icon: FileSignature, label: 'Create Template' },
  { to: '/leases/build', icon: Hammer, label: 'Build Lease' },
  { to: '/leases/submit', icon: Send, label: 'Submit Lease' },
]

const lifecycleItems = [
  { to: '/leases/calendar', icon: Calendar, label: 'Calendar' },
]

const maintenanceSubItems = [
  { to: '/maintenance/issues', icon: Wrench, label: 'Issues' },
  { to: '/maintenance/suppliers', icon: Truck, label: 'Suppliers' },
]

const propertyInfoSubItems = [
  { to: '/property-info/agent', icon: Sparkles, label: 'Agent Context' },
  { to: '/property-info/skills', icon: BookOpen, label: 'Skill Library' },
  { to: '/property-info/unit-info', icon: Info, label: 'Property Info' },
]

const allNavItems = [
  ...primaryNavItems,
  ...leaseSubItems,
  ...maintenanceSubItems,
  ...lifecycleItems,
  ...propertyInfoSubItems,
]

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  if (to === '/leases') return route.path === '/leases'
  return route.path === to || route.path.startsWith(`${to}/`)
}

const currentPageTitle = computed(() => {
  const active = allNavItems.find(item => isActive(item.to))
  return active?.label ?? ''
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
