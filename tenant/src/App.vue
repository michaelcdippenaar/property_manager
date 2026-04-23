<template>
  <div class="h-dvh overflow-hidden relative bg-surface">
    <RouterView v-slot="{ Component, route }">
      <Transition :name="transitionName" mode="out-in">
        <component :is="Component" :key="route.path" class="absolute inset-0 h-dvh" />
      </Transition>
    </RouterView>
    <ToastContainer />
    <!-- POPIA-compliant push opt-in banner (shown post-login, user-gesture only) -->
    <PushOptInBanner v-if="isAuthenticated" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { storeToRefs } from 'pinia'
import ToastContainer from './components/ToastContainer.vue'
import PushOptInBanner from './components/PushOptInBanner.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)

const router = useRouter()
const transitionName = ref('slide-left')

router.beforeEach((to, from) => {
  const toDepth = (to.meta.depth as number) ?? 0
  const fromDepth = (from.meta.depth as number) ?? 0
  if (toDepth === fromDepth) {
    transitionName.value = 'fade'
  } else {
    transitionName.value = toDepth > fromDepth ? 'slide-left' : 'slide-right'
  }
})

onMounted(async () => {
  if (Capacitor.isNativePlatform()) {
    const { StatusBar, Style } = await import('@capacitor/status-bar')
    await StatusBar.setStyle({ style: Style.Dark })
    await StatusBar.setBackgroundColor({ color: '#2B2D6E' })
  }

  // Register service worker silently — no permission prompt here
  if (authStore.isAuthenticated) {
    authStore.initPush()
  }
})
</script>
