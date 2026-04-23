<template>
  <!-- POPIA opt-in banner: shown after login, dismissed on user action -->
  <Transition name="slide-up">
    <div
      v-if="visible"
      class="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg px-4 py-4 safe-area-bottom"
      role="dialog"
      aria-labelledby="push-banner-title"
      aria-describedby="push-banner-desc"
    >
      <div class="max-w-md mx-auto">
        <p id="push-banner-title" class="text-sm font-semibold text-navy mb-1">
          Stay updated on your tenancy
        </p>
        <p id="push-banner-desc" class="text-xs text-gray-500 mb-3">
          Receive notifications for rent receipts, maintenance updates, and lease
          changes. You can change this at any time in settings.
          <!-- POPIA s18: purpose of collection disclosed -->
        </p>
        <div class="flex gap-3">
          <button
            class="flex-1 py-2 px-4 bg-accent text-white rounded-lg text-sm font-medium"
            @click="onEnable"
          >
            Enable notifications
          </button>
          <button
            class="flex-1 py-2 px-4 border border-gray-300 text-gray-600 rounded-lg text-sm"
            @click="onDismiss"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { requestAndSubscribe } from '../services/push'
import api from '../api'

const STORAGE_KEY = 'push_banner_dismissed'

const visible = ref(false)

onMounted(() => {
  // Show banner only if:
  //   1. Web Push is supported
  //   2. Permission not already determined
  //   3. User hasn't previously dismissed (in this browser)
  if (!('PushManager' in window)) return
  if (Notification.permission !== 'default') return
  if (localStorage.getItem(STORAGE_KEY)) return
  visible.value = true
})

async function onEnable() {
  visible.value = false
  // This is triggered by a user gesture (button click) — POPIA compliant
  const result = await requestAndSubscribe(async (token, platform) => {
    await api.post('/auth/push-token/', { token, platform })
  })
  if (result === 'denied') {
    localStorage.setItem(STORAGE_KEY, 'denied')
  }
}

function onDismiss() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, 'dismissed')
}
</script>

<style scoped>
.text-navy { color: #2B2D6E; }
.bg-accent { background-color: #FF3D7F; }
.safe-area-bottom { padding-bottom: max(1rem, env(safe-area-inset-bottom)); }

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}
</style>
