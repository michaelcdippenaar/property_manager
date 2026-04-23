<template>
  <RouterView />
  <ConsentBanner />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ConsentBanner from './components/ConsentBanner.vue'
import { hasClarityConsent, initClarity } from './composables/useClarity'
import { useGlobalSigningNotifications } from './composables/useGlobalSigningNotifications'

// Global signing notification listener — shows toasts for signer_completed /
// submission_completed events regardless of which route the agent is on.
// The composable self-manages the WS lifecycle (connects on auth, stops on logout).
useGlobalSigningNotifications()

onMounted(() => {
  // If the user previously accepted, re-init Clarity on every page load.
  // initClarity() is idempotent so this is safe.
  if (hasClarityConsent()) {
    initClarity()
  }
})
</script>
