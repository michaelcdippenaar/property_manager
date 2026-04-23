<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="SettingsView">
    <AppHeader title="Settings" />

    <div ref="scrollEl" class="scroll-page page-with-tab-bar px-4 pt-4 pb-8 space-y-4" @scroll="onScroll">
      <!-- Profile card -->
      <div class="list-section">
        <div class="px-5 py-5 flex items-center gap-4">
          <div class="w-14 h-14 rounded-full bg-navy flex items-center justify-center flex-shrink-0">
            <span class="text-white text-xl font-bold">{{ initials }}</span>
          </div>
          <div>
            <p class="text-base font-semibold text-gray-900">{{ auth.user?.full_name }}</p>
            <p class="text-sm text-gray-500 mt-0.5">{{ auth.user?.email }}</p>
            <span class="badge badge-blue mt-1 capitalize">{{ auth.user?.role }}</span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div>
        <p class="list-section-header px-1 pt-0 pb-1">Account</p>
        <div class="list-section">
          <div class="list-row touchable" @click="router.push({ name: 'signing' })">
            <div class="list-row-icon bg-accent/10">
              <FileText :size="18" class="text-accent" />
            </div>
            <span class="flex-1 text-sm font-medium text-gray-900">Lease & Signing</span>
            <ChevronRight :size="16" class="text-gray-300" />
          </div>
          <div class="list-row touchable" @click="router.push({ name: 'chat-list' })">
            <div class="list-row-icon bg-navy/8">
              <MessageCircle :size="18" class="text-navy" />
            </div>
            <span class="flex-1 text-sm font-medium text-gray-900">AI Assistant</span>
            <ChevronRight :size="16" class="text-gray-300" />
          </div>
          <div class="list-row touchable" @click="router.push({ name: 'my-data' })">
            <div class="list-row-icon bg-gray-100">
              <ShieldCheck :size="18" class="text-gray-500" />
            </div>
            <span class="flex-1 text-sm font-medium text-gray-900">My data (POPIA)</span>
            <ChevronRight :size="16" class="text-gray-300" />
          </div>
        </div>
      </div>

      <!-- Logout -->
      <div class="list-section">
        <button class="list-row w-full text-left touchable" @click="handleLogout">
          <div class="list-row-icon bg-danger-50">
            <LogOut :size="18" class="text-danger-600" />
          </div>
          <span class="flex-1 text-sm font-medium text-danger-600">Sign Out</span>
        </button>
      </div>

      <!-- App version -->
      <p class="text-center text-xs text-gray-400 pt-2">Klikk Tenant v1.0.0</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, LogOut, FileText, MessageCircle, ShieldCheck } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const scrollEl = ref<HTMLElement | null>(null)

const initials = computed(() => {
  return auth.user?.full_name
    ?.split(' ')
    .map(n => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() ?? '?'
})

function onScroll() {}

async function handleLogout() {
  await auth.logout()
  toast.success('Signed out')
  router.replace({ name: 'login' })
}
</script>
