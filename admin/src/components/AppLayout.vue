<template>
  <div class="flex flex-col h-screen bg-surface overflow-hidden">

    <!-- ── Header with navigation ── -->
    <header class="header-nav flex-shrink-0 z-50">
      <div class="h-16 flex items-center px-5 gap-2">
        <!-- Logo -->
        <RouterLink to="/" class="flex items-center gap-2 mr-3 flex-shrink-0">
          <span class="font-extrabold text-white text-lg tracking-tight">
            Klikk<span class="text-accent">.</span>
          </span>
        </RouterLink>

        <!-- Primary navigation -->
        <nav class="flex items-center gap-1 flex-1">
          <!-- Dashboard -->
          <RouterLink
            to="/"
            class="header-nav-link"
            :class="route.path === '/' ? 'header-nav-link-active' : ''"
          >
            <LayoutDashboard :size="15" />
            Dashboard
          </RouterLink>

          <!-- Section dropdowns -->
          <div
            v-for="section in primaryNav"
            :key="section.key"
            class="relative"
            @mouseenter="openDropdown = section.key"
            @mouseleave="openDropdown = null"
          >
            <button
              class="header-nav-link"
              :class="isSectionActive(section) ? 'header-nav-link-active' : ''"
            >
              <span class="whitespace-nowrap">{{ section.label }}</span>
              <span v-if="activeSectionChild(section)" class="opacity-60 font-normal whitespace-nowrap">· {{ activeSectionChild(section) }}</span>
              <ChevronDown :size="12" class="opacity-50 flex-shrink-0" />
            </button>

            <Transition
              enter-active-class="transition ease-out duration-100"
              enter-from-class="opacity-0 scale-95 -translate-y-1"
              enter-to-class="opacity-100 scale-100 translate-y-0"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="opacity-100 scale-100 translate-y-0"
              leave-to-class="opacity-0 scale-95 -translate-y-1"
            >
              <div
                v-if="openDropdown === section.key"
                class="absolute left-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-xl shadow-xl py-1 z-50 origin-top-left"
              >
                <RouterLink
                  v-for="item in section.items"
                  :key="item.to"
                  :to="item.to"
                  class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                  :class="isActive(item.to) ? 'text-navy bg-navy/5 font-medium' : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'"
                  @click="openDropdown = null"
                >
                  <component :is="item.icon" :size="16" class="flex-shrink-0 text-gray-400" />
                  <span class="flex-1">{{ item.label }}</span>
                  <span
                    v-if="item.badgeKey && badges[item.badgeKey]"
                    class="min-w-[16px] h-4 px-1 rounded-full bg-accent text-white text-[10px] font-bold flex items-center justify-center leading-none"
                  >{{ badges[item.badgeKey] }}</span>
                </RouterLink>
              </div>
            </Transition>
          </div>
        </nav>

        <!-- ── User menu ── -->
        <div
          class="relative ml-auto flex-shrink-0"
          @mouseenter="openDropdown = 'user'"
          @mouseleave="openDropdown = null"
        >
          <button
            class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="User menu"
          >
            <div class="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0">
              {{ initials }}
            </div>
            <div class="text-sm text-white/70 hidden sm:block">{{ auth.user?.full_name || 'Admin' }}</div>
            <ChevronDown :size="12" class="text-white/40 hidden sm:block" />
          </button>

          <!-- User dropdown -->
          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="opacity-0 scale-95 -translate-y-1"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-95 -translate-y-1"
          >
            <div
              v-if="openDropdown === 'user'"
              class="absolute right-0 top-full mt-1 w-56 bg-white border border-gray-200 rounded-xl shadow-xl py-1 z-50 origin-top-right"
            >
              <!-- Profile -->
              <RouterLink
                to="/profile"
                class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                :class="isActive('/profile') ? 'text-navy bg-navy/5 font-medium' : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'"
                @click="openDropdown = null"
              >
                <User :size="16" class="flex-shrink-0 text-gray-400" />
                <span>Profile</span>
              </RouterLink>

              <div class="my-1 border-t border-gray-100" />

              <!-- Admin items (admin only) -->
              <template v-if="auth.user?.role === 'admin'">
                <p class="px-3 pt-1.5 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Admin</p>
                <RouterLink
                  v-for="item in adminItems"
                  :key="item.to"
                  :to="item.to"
                  class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                  :class="isActive(item.to) ? 'text-navy bg-navy/5 font-medium' : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'"
                  @click="openDropdown = null"
                >
                  <component :is="item.icon" :size="16" class="flex-shrink-0 text-gray-400" />
                  <span>{{ item.label }}</span>
                </RouterLink>

                <!-- Developer -->
                <RouterLink
                  v-for="item in developerItems"
                  :key="item.to"
                  :to="item.to"
                  class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                  :class="isActive(item.to) ? 'text-navy bg-navy/5 font-medium' : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'"
                  @click="openDropdown = null"
                >
                  <component :is="item.icon" :size="16" class="flex-shrink-0 text-gray-400" />
                  <span>{{ item.label }}</span>
                </RouterLink>

                <div class="my-1 border-t border-gray-100" />
              </template>

              <!-- Knowledge Base -->
              <p class="px-3 pt-1.5 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Knowledge Base</p>
              <RouterLink
                v-for="item in propertyInfoSubItems"
                :key="item.to"
                :to="item.to"
                class="flex items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                :class="isActive(item.to) ? 'text-navy bg-navy/5 font-medium' : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'"
                @click="openDropdown = null"
              >
                <component :is="item.icon" :size="16" class="flex-shrink-0 text-gray-400" />
                <span>{{ item.label }}</span>
              </RouterLink>

              <div class="my-1 border-t border-gray-100" />

              <!-- Logout -->
              <button
                class="flex items-center gap-2.5 px-3 py-2 text-sm w-full text-left text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
                @click="handleLogout"
              >
                <LogOut :size="16" class="flex-shrink-0 text-gray-400" />
                <span>Log out</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <!-- ── Main content ── -->
    <main class="flex-1 overflow-y-auto p-6">
      <RouterView v-slot="{ Component }">
        <KeepAlive exclude="TemplateEditorView,TiptapEditorView,LeaseBuilderView">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>

    <!-- AI assistant FAB -->
    <RouterLink
      to="/property-info/agent"
      class="fixed bottom-6 right-6 z-40 w-11 h-11 rounded-full bg-navy shadow-lg shadow-navy/25 flex items-center justify-center text-white hover:bg-navy-dark hover:shadow-xl hover:scale-105 active:scale-95 transition-all"
      aria-label="Ask AI assistant"
    >
      <Sparkles :size="18" />
    </RouterLink>

    <!-- Toast notifications -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import ToastContainer from './ToastContainer.vue'
import {
  LayoutDashboard, Building2, Users, UserCheck, Wrench, FileText, FileSignature, Calendar,
  LogOut, Sparkles, BookOpen, Info, ChevronDown, Truck,
  Activity, HelpCircle, ShieldCheck, User, FlaskConical, Settings,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const openDropdown = ref<string | null>(null)

// ── Primary nav (always visible in header) ────────────────────────────────────
const entityNavItems = [
  { to: '/landlords', icon: UserCheck, label: 'Owners' },
  { to: '/properties', icon: Building2, label: 'Properties' },
  { to: '/tenants', icon: Users, label: 'Tenants' },
]

const leaseSubItems = [
  { to: '/leases/overview', icon: LayoutDashboard, label: 'Overview' },
  { to: '/leases/templates', icon: FileSignature, label: 'Templates' },
  { to: '/leases', icon: FileText, label: 'Leases' },
  { to: '/leases/calendar', icon: Calendar, label: 'Calendar' },
]

const maintenanceSubItems = [
  { to: '/maintenance/issues', icon: Wrench, label: 'Issues', badgeKey: 'open_issues' },
  { to: '/maintenance/questions', icon: HelpCircle, label: 'Questions', badgeKey: 'pending_questions' },
  { to: '/maintenance/suppliers', icon: Truck, label: 'Suppliers' },
]

interface NavSection {
  key: string
  label: string
  items: typeof entityNavItems
}

const primaryNav = computed<NavSection[]>(() => [
  { key: 'entities', label: 'Entities', items: entityNavItems },
  { key: 'leases', label: 'Leases', items: leaseSubItems },
  { key: 'maintenance', label: 'Maintenance', items: maintenanceSubItems },
])

// ── User menu items (under avatar dropdown) ───────────────────────────────────
const adminItems = [
  { to: '/admin/users', icon: ShieldCheck, label: 'Users' },
  { to: '/admin/agency', icon: Settings, label: 'Agency Settings' },
]

const developerItems = [
  { to: '/testing', icon: FlaskConical, label: 'Testing Portal' },
]

const propertyInfoSubItems = [
  { to: '/property-info/agent', icon: Sparkles, label: 'Agent Context' },
  { to: '/property-info/skills', icon: BookOpen, label: 'Skill Library' },
  { to: '/property-info/unit-info', icon: Info, label: 'Property Info' },
  { to: '/property-info/monitor', icon: Activity, label: 'Agent Monitor' },
]

function isSectionActive(section: NavSection): boolean {
  return section.items.some(item => isActive(item.to))
}

function activeSectionChild(section: NavSection): string | null {
  const active = section.items.find(item => isActive(item.to))
  return active ? active.label : null
}

const badges = ref<Record<string, number>>({})

async function loadBadges() {
  try {
    const { data } = await api.get('/maintenance/badges/')
    badges.value = data
  } catch { /* ignore */ }
}

onMounted(() => {
  loadBadges()
  setInterval(loadBadges, 60_000)

  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
  const token = localStorage.getItem('access_token') || ''
  const ws = new WebSocket(`${wsUrl}/ws/maintenance/updates/?token=${token}`)
  ws.onmessage = () => loadBadges()
})

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  if (to === '/leases') return route.path === '/leases' || route.path === '/leases/build'
  if (to === '/leases/overview') return route.path === '/leases/overview'
  if (to === '/leases/status') return route.path === '/leases/status'
  return route.path === to || route.path.startsWith(`${to}/`)
}

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'A'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

function handleLogout() {
  openDropdown.value = null
  auth.logout()
  router.push('/login')
}
</script>
