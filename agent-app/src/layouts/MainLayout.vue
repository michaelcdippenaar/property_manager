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
    <q-footer v-if="!route.meta.showBackBtn">
      <q-tabs
        v-model="activeTab"
        :class="tabBarClass"
        indicator-color="transparent"
        :active-color="isIos ? 'primary' : 'primary'"
        no-caps
        align="justify"
      >
        <q-tab name="properties" icon="home" label="Properties" @click="router.push('/properties')" />
        <q-tab name="calendar"   icon="event" label="Calendar"   @click="router.push('/calendar')" />
        <q-tab name="dashboard"  icon="bar_chart" label="Dashboard" @click="router.push('/dashboard')" />
      </q-tabs>
    </q-footer>

  </q-layout>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlatform } from '../composables/usePlatform'

const route  = useRoute()
const router = useRouter()
const { isIos, isAndroid, enterTransition, leaveTransition, backIcon, tabBarClass, headerClass } = usePlatform()

// Sync bottom tab with current route
const activeTab = ref<string>('dashboard')

watch(
  () => route.name,
  (name) => {
    if (name === 'dashboard')    activeTab.value = 'dashboard'
    else if (name === 'calendar') activeTab.value = 'calendar'
    else if (name === 'properties' || name === 'property-detail') activeTab.value = 'properties'
  },
  { immediate: true },
)
</script>
