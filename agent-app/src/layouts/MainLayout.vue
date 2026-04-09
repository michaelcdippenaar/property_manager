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
          @click="router.back()"
        />

        <q-toolbar-title
          :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'"
        >
          {{ route.meta.title || 'Klikk Agent' }}
        </q-toolbar-title>

        <!-- Agency logo placeholder -->
        <q-avatar v-if="!route.meta.showBackBtn" size="32px" color="white" text-color="primary">
          <span class="text-weight-bold" style="font-size:11px">KA</span>
        </q-avatar>
      </q-toolbar>
    </q-header>

    <!-- ── Android FAB (book viewing) ──────────────────────────────────────── -->
    <q-page-sticky
      v-if="isAndroid && route.meta.showFab !== false"
      position="bottom-right"
      :offset="[18, 88]"
    >
      <q-btn
        fab
        icon="add"
        color="secondary"
        @click="router.push('/viewings/new')"
        aria-label="Book viewing"
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
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlatform } from '../composables/usePlatform'

const route  = useRoute()
const router = useRouter()
const { isIos, isAndroid, enterTransition, leaveTransition, backIcon, headerClass } = usePlatform()

const tabs = [
  { name: 'dashboard',  label: 'Dashboard',  icon: 'bar_chart', path: '/dashboard'  },
  { name: 'properties', label: 'Properties', icon: 'home',      path: '/properties' },
  { name: 'calendar',   label: 'Calendar',   icon: 'event',     path: '/calendar'   },
  { name: 'settings',   label: 'Settings',   icon: 'settings',  path: '/settings'   },
]

const activeTab = ref<string>('properties')

watch(
  () => route.name,
  (name) => {
    if (name === 'dashboard')                                       activeTab.value = 'dashboard'
    else if (name === 'calendar')                                   activeTab.value = 'calendar'
    else if (name === 'settings')                                   activeTab.value = 'settings'
    else if (name === 'properties' || name === 'property-detail')  activeTab.value = 'properties'
  },
  { immediate: true },
)
</script>

<style lang="scss">
.agent-tab-bar {
  display: flex;
  align-items: stretch;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 0.5px solid rgba(0, 0, 0, 0.14);
  height: 56px;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.agent-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: none;
  border: none;
  cursor: pointer;
  color: #9e9e9e;
  transition: color 0.15s;
  padding: 0;

  &--active {
    color: #2B2D6E;
  }

  &:active {
    opacity: 0.7;
  }
}

.agent-tab-label {
  font-size: 9.5px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.01em;
}
</style>
