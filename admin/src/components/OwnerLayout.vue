<template>
  <div class="flex flex-col h-screen bg-gray-50 overflow-hidden">
    <header class="bg-navy flex-shrink-0 z-50">
      <div class="flex items-center h-14 px-4 sm:px-6 gap-4 sm:gap-6">
        <RouterLink to="/owner" class="flex items-center gap-2 mr-2 sm:mr-4 flex-shrink-0" aria-label="Home">
          <span class="text-white font-extrabold text-lg leading-none tracking-tight whitespace-nowrap">Klikk<span class="text-accent">.</span></span>
          <span class="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded-md bg-accent/15 text-accent text-xs font-bold tracking-[0.12em] uppercase leading-none">
            Owner
          </span>
        </RouterLink>

        <!-- Mobile hamburger -->
        <button
          class="sm:hidden p-2 -ml-1 text-white/70 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
          @click="mobileMenuOpen = !mobileMenuOpen"
          aria-label="Toggle menu"
        >
          <Menu v-if="!mobileMenuOpen" :size="20" />
          <X v-else :size="20" />
        </button>

        <nav class="hidden sm:flex items-center gap-1 flex-1 min-w-0">
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

        <div class="flex items-center gap-3 flex-shrink-0 ml-auto">
          <div class="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center text-white text-xs font-bold">
            {{ initials }}
          </div>
          <button @click="handleLogout"
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors text-sm">
            <LogOut :size="15" />
          </button>
        </div>
      </div>

      <!-- Mobile nav dropdown -->
      <div v-if="mobileMenuOpen" class="sm:hidden bg-navy border-t border-white/10 px-4 py-2 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(item.to)
            ? 'bg-white/15 text-white'
            : 'text-white/60 hover:text-white hover:bg-white/10'"
        >
          <component :is="item.icon" :size="16" class="flex-shrink-0" />
          {{ item.label }}
        </RouterLink>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto">
      <div class="max-w-[1400px] mx-auto p-4 sm:p-6">
        <RouterView />
      </div>
    </main>

    <!-- AI Guide widget (feature-flagged via VITE_ENABLE_AI_GUIDE) -->
    <AIGuide portal-role="owner" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { LayoutDashboard, Building2, FileText, LogOut, Menu, X } from 'lucide-vue-next'
import AIGuide from './AIGuide.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)

watch(() => route.path, () => { mobileMenuOpen.value = false })

const navItems = [
  { to: '/owner',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/owner/properties', icon: Building2,       label: 'Properties' },
  { to: '/owner/leases',     icon: FileText,        label: 'Leases' },
]

function isActive(to: string) {
  if (to === '/owner') return route.path === '/owner'
  return route.path.startsWith(to)
}

const initials = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'O'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>
