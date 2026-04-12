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
          {{ route.meta.title || 'Klikk Tenant' }}
        </q-toolbar-title>

        <!-- Tenant avatar placeholder -->
        <q-avatar v-if="!route.meta.showBackBtn" size="32px" color="white" text-color="primary">
          <span class="text-weight-bold" style="font-size:11px">KT</span>
        </q-avatar>
      </q-toolbar>
    </q-header>

    <!-- ── Page content ────────────────────────────────────────────────────── -->
    <q-page-container>
      <router-view v-slot="{ Component }">
        <keep-alive :include="['HomePage', 'RepairsPage', 'SettingsPage']">
          <transition
            :enter-active-class="`animated ${enterTransition} faster`"
            :leave-active-class="`animated ${leaveTransition} faster`"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </keep-alive>
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
const { isIos, enterTransition, leaveTransition, backIcon, headerClass } = usePlatform()

const tabs = [
  { name: 'dashboard', label: 'Home',     icon: 'home',     path: '/dashboard' },
  { name: 'repairs',   label: 'Repairs',  icon: 'build',    path: '/repairs'   },
  { name: 'settings',  label: 'Settings', icon: 'settings', path: '/settings'  },
]

const activeTab = ref<string>('dashboard')

watch(
  () => route.name,
  (name) => {
    if (name === 'dashboard')  activeTab.value = 'dashboard'
    else if (name === 'repairs')    activeTab.value = 'repairs'
    else if (name === 'settings')   activeTab.value = 'settings'
  },
  { immediate: true },
)
</script>

<style lang="scss">
.agent-tab-bar {
  display: flex;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 0.5px solid var(--klikk-border-strong);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.agent-tab {
  flex: 1;
  height: 49px;
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
  font-size: 11px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.01em;
}
</style>
