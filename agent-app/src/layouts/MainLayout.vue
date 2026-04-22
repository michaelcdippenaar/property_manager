<template>
  <q-layout view="hHh lpR fFf">

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <q-header
      :elevated="!isIos"
      :class="headerClass"
    >
      <q-toolbar>
        <!-- Back button (detail pages) -->
        <q-btn
          v-if="route.meta.showBackBtn"
          flat
          round
          :icon="backIcon"
          :color="isIos ? 'primary' : 'white'"
          aria-label="Go back"
          @click="router.back()"
        />

        <q-toolbar-title
          :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'"
        >
          {{ pageTitle || route.meta.title || 'Klikk Agent' }}
        </q-toolbar-title>

        <!-- Profile avatar (opens settings) -->
        <q-btn
          v-if="!route.meta.showBackBtn"
          flat
          round
          dense
          aria-label="Profile"
          @click="router.push('/settings')"
        >
          <q-avatar size="32px" color="primary" text-color="white">
            <span class="text-weight-bold logo-initials">{{ profileInitials }}</span>
          </q-avatar>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- ── Android FAB (quick action) ──────────────────────────────────────── -->
    <q-page-sticky
      v-if="isAndroid && route.meta.showFab !== false"
      position="bottom-right"
      :offset="[18, 88]"
    >
      <q-btn
        fab
        icon="add"
        color="secondary"
        @click="handleFab"
        aria-label="Quick action"
      />
    </q-page-sticky>

    <!-- ── Page content ────────────────────────────────────────────────────── -->
    <q-page-container>
      <router-view v-slot="{ Component }">
        <transition
          :enter-active-class="`animated ${enterTransition} faster`"
          :leave-active-class="`animated ${leaveTransition} faster`"
          mode="out-in"
        >
          <component :is="Component" />
        </transition>
      </router-view>
    </q-page-container>

    <!-- ── Bottom Tab Bar ──────────────────────────────────────────────────── -->
    <q-footer v-if="!route.meta.showBackBtn" bordered class="bg-transparent">
      <div class="agent-tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.name"
          class="agent-tab"
          :class="{ 'agent-tab--active': activeTab === tab.name }"
          @click="router.push(tab.path)"
        >
          <q-icon :name="tab.icon" size="22px" />
          <span class="agent-tab-label">{{ tab.label }}</span>
        </button>
      </div>
    </q-footer>

  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, provide, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlatform } from '../composables/usePlatform'
import { useAuthStore } from '../stores/auth'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const { isIos, isAndroid, enterTransition, leaveTransition, backIcon, headerClass } = usePlatform()

// Allow child pages to override the header title
const pageTitle = shallowRef<string | null>(null)
provide('setPageTitle', (title: string | null) => { pageTitle.value = title })

const profileInitials = computed(() => {
  const u = auth.user
  const f = u?.first_name?.[0] ?? ''
  const l = u?.last_name?.[0] ?? ''
  return (f + l).toUpperCase() || 'KA'
})

const tabs = [
  { name: 'today',    label: 'Today',    icon: 'today',       path: '/today'    },
  { name: 'pipeline', label: 'Pipeline', icon: 'insights',    path: '/pipeline' },
  { name: 'people',   label: 'People',   icon: 'groups',      path: '/people'   },
  { name: 'inbox',    label: 'Inbox',    icon: 'inbox',       path: '/inbox'    },
]

const activeTab = ref<string>('today')

// Map descendant routes to their parent tab so deep links keep the right tab highlighted.
const tabForRoute: Record<string, string> = {
  today:                'today',
  pipeline:             'pipeline',
  people:               'people',
  inbox:                'inbox',
  // Existing sub-routes map under Pipeline
  dashboard:            'today',
  viewings:             'pipeline',
  'viewing-detail':     'pipeline',
  'book-viewing':       'pipeline',
  'create-lease':       'pipeline',
  calendar:             'pipeline',
  leases:               'pipeline',
  properties:           'pipeline',
  'property-detail':    'pipeline',
  'create-direct-lease': 'pipeline',
  maintenance:          'inbox',
}

watch(
  () => route.name,
  (name) => {
    pageTitle.value = null
    const key = String(name ?? '')
    activeTab.value = tabForRoute[key] ?? 'today'
  },
  { immediate: true },
)

function handleFab() {
  // Context-aware quick action: viewings from Pipeline, otherwise book a viewing
  if (activeTab.value === 'inbox') {
    router.push('/viewings/new')
  } else {
    router.push('/viewings/new')
  }
}
</script>

<style lang="scss">
.agent-tab-bar {
  display: flex;
  // flex-start so tabs sit in the 49px area; padding-bottom handles safe zone
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 0.5px solid var(--klikk-border-strong);
  // No fixed height — tab buttons are 49px + safe area padding below them
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.agent-tab {
  flex: 1;
  height: 49px;   // iOS HIG: 49pt tab bar height (content only, above safe area)
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--klikk-text-muted);
  transition: color 0.15s;
  padding: 0;

  &--active {
    color: var(--q-primary);
  }

  &:active {
    opacity: 0.7;
  }
}

.agent-tab-label {
  font-size: 11px;   /* iOS Caption 2 = 11pt */
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.01em;
}

// Header avatar initials — tight 11px label.
.logo-initials {
  font-size: 11px;
  line-height: 1;
}
</style>
