<template>
  <RouterView />
  <ConsentBanner />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ConsentBanner from './components/ConsentBanner.vue'
import { hasClarityConsent, initClarity } from './composables/useClarity'

onMounted(() => {
  // If the user previously accepted, re-init Clarity on every page load.
  // initClarity() is idempotent so this is safe.
  if (hasClarityConsent()) {
    initClarity()
  }
})
</script>
