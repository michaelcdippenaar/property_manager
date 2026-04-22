<template>
  <router-view />
</template>

<script setup lang="ts">
import { App as CapApp } from '@capacitor/app'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  CapApp.addListener('backButton', ({ canGoBack }) => {
    if (!canGoBack) CapApp.exitApp()
    else void router.back()
  })
})
</script>
