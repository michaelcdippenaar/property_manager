<template>
  <div class="flex flex-col h-screen bg-gray-50 overflow-hidden">

    <!-- ── Top nav ── -->
    <header class="bg-navy flex items-center h-14 px-6 flex-shrink-0 z-50 gap-6">

      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-1.5 mr-4 flex-shrink-0">
        <span class="text-white font-bold text-xl leading-none">K<span class="text-pink-brand">.</span></span>
        <span class="text-white font-bold text-lg leading-none whitespace-nowrap">Klikk<span class="text-pink-brand">.</span></span>
      </RouterLink>

      <!-- Primary nav items -->
      <nav class="flex items-center gap-1 flex-1 min-w-0">
        <RouterLink
          v-for="item in primaryNavItems"
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

        <!-- Maintenance dropdown -->
        <div class="relative" ref="maintDropRef">
          <button
            @click="maintOpen = !maintOpen"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="isMaintActive
              ? 'bg-white/15 text-white'
              : 'text-white/60 hover:text-white hover:bg-white/10'"
          >
            <Wrench :size="15" class="flex-shrink-0" />
            Maintenance
            <ChevronDown :size="13" class="transition-transform" :class="maintOpen ? 'rotate-180' : ''" />
          </button>
          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div
              v-if="maintOpen"
              class="absolute left-0 top-full mt-1.5 w-52 rounded-xl bg-white shadow-lg ring-1 ring-black/5 py-1.5 z-50"
            >
              <RouterLink
                v-for="item in maintenanceSubItems"
                :key="item.to"
                :to="item.to"
                @click="maintOpen = false"
                class="flex items-center gap-2.5 px-3.5 py-2 text-sm font-medium transition-colors"
                :class="isActive(item.to)
                  ? 'text-navy bg-indigo-50'
                  : 'text-gray-700 hover:bg-gray-50'"
              >
                <component :is="item.icon" :size="15" class="flex-shrink-0 text-gray-400" />
                {{ item.label }}
              </RouterLink>
            </div>
          </Transition>
        </div>

        <!-- Property Info dropdown -->
        <div class="relative" ref="propDropRef">
          <button
            @click="propOpen = !propOpen"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            :class="isPropInfoActive
              ? 'bg-white/15 text-white'
              : 'text-white/60 hover:text-white hover:bg-white/10'"
          >
            <Info :size="15" class="flex-shrink-0" />
            Property Info
            <ChevronDown :size="13" class="transition-transform" :class="propOpen ? 'rotate-180' : ''" />
          </button>

          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div
              v-if="propOpen"
              class="absolute left-0 top-full mt-1.5 w-48 rounded-xl bg-white shadow-lg ring-1 ring-black/5 py-1.5 z-50"
            >
              <RouterLink
                v-for="item in propertyInfoSubItems"
                :key="item.to"
                :to="item.to"
                @click="propOpen = false"
                class="flex items-center gap-2.5 px-3.5 py-2 text-sm font-medium transition-colors"
                :class="isActive(item.to)
                  ? 'text-navy bg-indigo-50'
                  : 'text-gray-700 hover:bg-gray-50'"
              >
                <component :is="item.icon" :size="15" class="flex-shrink-0 text-gray-400" />
                {{ item.label }}
              </RouterLink>
            </div>
          </Transition>
        </div>
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

    <!-- ── Page content ── -->
    <main class="flex-1 overflow-y-auto p-6">
      <RouterView v-slot="{ Component }">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  LayoutDashboard, Building2, Users, Wrench, FileText,
  LogOut, Sparkles, BookOpen, Info, ChevronDown, Bot, HelpCircle, Truck,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const propOpen = ref(false)
const propDropRef = ref<HTMLElement | null>(null)
const maintOpen = ref(false)
const maintDropRef = ref<HTMLElement | null>(null)

const primaryNavItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties', icon: Building2, label: 'Properties' },
  { to: '/tenants', icon: Users, label: 'Tenants' },
  { to: '/leases', icon: FileText, label: 'Leases' },
]

const maintenanceSubItems = [
  { to: '/maintenance/issues', icon: Wrench, label: 'Issues' },
  { to: '/maintenance/suppliers', icon: Truck, label: 'Suppliers' },
  { to: '/maintenance/ai-questions', icon: HelpCircle, label: 'AI Agent Questions' },
  { to: '/maintenance/ai-sandbox', icon: Bot, label: 'AI Agent Sandbox' },
]

const propertyInfoSubItems = [
  { to: '/property-info/agent', icon: Sparkles, label: 'Agent context' },
  { to: '/property-info/skills', icon: BookOpen, label: 'Skill library' },
  { to: '/property-info/unit-info', icon: Info, label: 'Property info' },
]

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}

const isPropInfoActive = computed(() =>
  propertyInfoSubItems.some((i) => isActive(i.to))
)

const isMaintActive = computed(() =>
  maintenanceSubItems.some((i) => isActive(i.to))
)

// Close dropdowns on outside click
function onClickOutside(e: MouseEvent) {
  if (propDropRef.value && !propDropRef.value.contains(e.target as Node)) {
    propOpen.value = false
  }
  if (maintDropRef.value && !maintDropRef.value.contains(e.target as Node)) {
    maintOpen.value = false
  }
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'A'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
