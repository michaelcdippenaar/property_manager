<!--
  AgentPreviewLayout — 1:1 port of docs/prototypes/admin-shell/index.html

  Full operations console: topbar (logo + agency switcher + search + actions)
  + segmented sidebar (Operations / Product lines / Settings) + <RouterView>.

  Public (no auth required) so the preview can be shown before login.
  All styles live in /admin/src/assets/agent-shell.css, scoped under
  `.agent-shell` to avoid collisions with the rest of the admin app.

  Loads Google Fonts (Fraunces / DM Sans / JetBrains Mono) on mount.
  Icons: lucide-vue-next (Phosphor removed April 2026).
-->
<script setup lang="ts">
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import {
  Building2,
  ChevronDown,
  Search,
  HelpCircle,
  Bell,
  ArrowLeftRight,
  User,
  LogIn,
  LogOut,
  LayoutGrid,
  Home,
  FileText,
  Vault,
  Wrench,
  ClipboardList,
  Users,
  FolderLock,
  MessageCircle,
  Settings,
  TrendingUp,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import '../assets/agent-shell.css'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

/** Avatar dropdown — contains Switch portal (admin) and Sign out. */
const userMenuOpen = ref(false)

/** Two-letter initials fallback. Uses full_name if loaded, else a stub. */
const initials = computed(() => {
  const full = auth.user?.full_name?.trim() ?? ''
  if (!full) return 'MC'
  const parts = full.split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
})

async function handleLogout() {
  userMenuOpen.value = false
  await auth.logout()
  router.replace('/login')
}

function handleDocClick(e: MouseEvent) {
  if (!userMenuOpen.value) return
  const target = e.target as HTMLElement | null
  if (!target) return
  if (target.closest('[data-agent-user-menu]')) return
  userMenuOpen.value = false
}
function handleDocKey(e: KeyboardEvent) {
  if (e.key === 'Escape') userMenuOpen.value = false
}

// Sidebar icon map — Lucide component references
const NAV_ICONS: Record<string, unknown> = {
  'squares-four':    LayoutGrid,
  'house':           Home,
  'file-text':       FileText,
  'vault':           Vault,
  'wrench':          Wrench,
  'clipboard-text':  ClipboardList,
  'users-three':     Users,
  'folder-lock':     FolderLock,
  'chat-circle-dots': MessageCircle,
  'house-simple':    Home,
  'chart-line-up':   TrendingUp,
  'gear-six':        Settings,
}

interface NavItem {
  to: string
  label: string
  icon: string
  count?: number
}

const operations: NavItem[] = [
  { to: '/agent',             label: 'Dashboard',    icon: 'squares-four' },
  { to: '/agent/properties',  label: 'Properties',   icon: 'house',           count: 47 },
  { to: '/agent/leases',      label: 'Leases',       icon: 'file-text',       count: 38 },
  { to: '/agent/deposits',    label: 'Deposits',     icon: 'vault' },
  { to: '/agent/maintenance', label: 'Maintenance',  icon: 'wrench',          count: 12 },
  { to: '/agent/inspections', label: 'Inspections',  icon: 'clipboard-text' },
  { to: '/agent/contacts',    label: 'Contacts',     icon: 'users-three' },
  { to: '/agent/vault',       label: 'Vault33',      icon: 'folder-lock' },
  { to: '/agent/messaging',   label: 'Messaging',    icon: 'chat-circle-dots', count: 3 },
]

const productLines: NavItem[] = [
  { to: '/agent/sales', label: 'Real Estate', icon: 'house-simple' },
  { to: '/agent/bi',    label: 'BI',          icon: 'chart-line-up' },
]

const settings: NavItem[] = [
  { to: '/agent/settings', label: 'Settings', icon: 'gear-six' },
]

/**
 * Prefix match — /agent/properties/:id should still highlight Properties.
 * The Dashboard (/agent) must be exact to avoid matching everything.
 */
function isActive(to: string): boolean {
  if (to === '/agent') return route.path === '/agent' || route.path === '/agent/'
  return route.path === to || route.path.startsWith(to + '/')
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _hydrated = computed(() => route.path)

onMounted(() => {
  document.addEventListener('click', handleDocClick)
  document.addEventListener('keydown', handleDocKey)

  // Google Fonts (Phosphor CDN block removed April 2026 — using lucide-vue-next)
  if (!document.querySelector('link[data-agent-shell-fonts]')) {
    const pre1 = document.createElement('link')
    pre1.rel = 'preconnect'
    pre1.href = 'https://fonts.googleapis.com'
    document.head.appendChild(pre1)

    const pre2 = document.createElement('link')
    pre2.rel = 'preconnect'
    pre2.href = 'https://fonts.gstatic.com'
    pre2.crossOrigin = ''
    document.head.appendChild(pre2)

    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href =
      'https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap'
    link.dataset.agentShellFonts = '1'
    document.head.appendChild(link)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocClick)
  document.removeEventListener('keydown', handleDocKey)
})
</script>

<template>
  <div class="agent-shell">
    <div class="app">
      <!-- TOP BAR -->
      <header class="topbar">
        <RouterLink to="/agent" class="logo" style="cursor:pointer">
          <div class="dot">K</div>
          <span>Klikk</span>
        </RouterLink>
        <button class="agency" type="button" aria-label="Switch agency">
          <Building2 :size="14" />
          <span>Winelands Property Co.</span>
          <ChevronDown :size="12" style="color:var(--muted)" />
        </button>
        <div class="search">
          <Search :size="16" />
          <input placeholder="Search properties, tenants, leases, documents…" />
          <span class="kbd">⌘K</span>
        </div>
        <div class="top-actions">
          <button class="icon-btn" title="Help" aria-label="Help" type="button">
            <HelpCircle :size="18" />
          </button>
          <button class="icon-btn" title="Notifications" aria-label="Notifications" type="button">
            <Bell :size="18" />
            <span class="dot-alert" />
          </button>
          <div class="user-menu-wrap" data-agent-user-menu>
            <button
              class="avatar avatar-btn"
              type="button"
              :title="auth.user?.full_name || 'Account'"
              :aria-label="auth.user?.full_name || 'Account menu'"
              :aria-expanded="userMenuOpen"
              aria-haspopup="menu"
              @click.stop="userMenuOpen = !userMenuOpen"
            >{{ initials }}</button>

            <div v-if="userMenuOpen" class="user-menu" @click.stop>
              <div class="user-menu-head">
                <strong>{{ auth.user?.full_name || 'Guest preview' }}</strong>
                <span v-if="auth.user?.email">{{ auth.user.email }}</span>
                <span v-else class="muted">Not signed in</span>
              </div>

              <RouterLink
                v-if="auth.user?.role === 'admin'"
                to="/choose-portal"
                class="user-menu-item"
                @click="userMenuOpen = false"
              >
                <ArrowLeftRight :size="15" />
                <span>Switch portal</span>
              </RouterLink>

              <RouterLink
                v-if="auth.isAuthenticated"
                to="/profile"
                class="user-menu-item"
                @click="userMenuOpen = false"
              >
                <User :size="15" />
                <span>Profile</span>
              </RouterLink>

              <div v-if="auth.isAuthenticated" class="user-menu-divider" />

              <button
                v-if="auth.isAuthenticated"
                class="user-menu-item"
                type="button"
                @click="handleLogout"
              >
                <LogOut :size="15" />
                <span>Sign out</span>
              </button>
              <RouterLink
                v-else
                to="/login"
                class="user-menu-item"
                @click="userMenuOpen = false"
              >
                <LogIn :size="15" />
                <span>Sign in</span>
              </RouterLink>
            </div>
          </div>
        </div>
      </header>

      <!-- SIDEBAR -->
      <nav class="sidebar" aria-label="Main navigation">
        <div class="nav-group-label">Operations</div>
        <RouterLink
          v-for="item in operations"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="NAV_ICONS[item.icon]" :size="18" />
          <span>{{ item.label }}</span>
          <span v-if="item.count" class="count">{{ item.count }}</span>
        </RouterLink>

        <div class="nav-divider" />
        <div class="nav-group-label">Product lines</div>
        <RouterLink
          v-for="item in productLines"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="NAV_ICONS[item.icon]" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>

        <div class="nav-divider" />
        <RouterLink
          v-for="item in settings"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="NAV_ICONS[item.icon]" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- MAIN -->
      <main class="main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style>
/*
  Avatar dropdown — scoped to .agent-shell so it inherits the design tokens
  (navy, accent, line, paper) without leaking to the main admin layout.
*/
.agent-shell .user-menu-wrap {
  position: relative;
}
.agent-shell .avatar-btn {
  border: 0;
  cursor: pointer;
  padding: 0;
}
.agent-shell .avatar-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.agent-shell .user-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 220px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 32px rgba(16, 20, 48, 0.12);
  padding: 6px;
  z-index: 50;
}
.agent-shell .user-menu-head {
  display: flex;
  flex-direction: column;
  padding: 10px 12px 8px;
  border-bottom: 1px solid var(--line);
  margin: -6px -6px 6px -6px;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  background: var(--paper);
}
.agent-shell .user-menu-head strong {
  font-size: 13px;
  color: var(--ink);
}
.agent-shell .user-menu-head span {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}
.agent-shell .user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  border-radius: 8px;
  text-decoration: none;
}
.agent-shell .user-menu-item:hover {
  background: var(--paper);
}
.agent-shell .user-menu-item svg {
  color: var(--muted);
}
.agent-shell .user-menu-divider {
  height: 1px;
  background: var(--line);
  margin: 4px 2px;
}
</style>
