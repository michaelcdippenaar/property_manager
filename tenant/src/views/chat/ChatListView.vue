<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="AI Assistant" show-back back-label="Home" />

    <div class="scroll-page px-4 pt-4 pb-24 space-y-2">
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 3" :key="i" class="h-16 bg-white rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="conversations.length === 0" class="flex flex-col items-center justify-center pt-20 text-center">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <MessageCircle :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No conversations yet</p>
        <p class="text-sm text-gray-400 mt-1">Start a new chat with your AI assistant</p>
      </div>

      <div v-else class="list-section">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="list-row touchable"
          @click="router.push({ name: 'chat-detail', params: { id: conv.id } })"
        >
          <div class="list-row-icon bg-navy/8">
            <Bot :size="18" class="text-navy" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-900 truncate">{{ conv.title || 'New conversation' }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ formatDate(conv.updated_at ?? conv.created_at) }}</p>
          </div>
          <ChevronRight :size="16" class="text-gray-300 flex-shrink-0" />
        </div>
      </div>
    </div>

    <!-- New chat FAB -->
    <button class="fab" @click="createConversation">
      <Plus :size="26" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessageCircle, ChevronRight, Plus, Bot } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'

const router = useRouter()
const conversations = ref<any[]>([])
const loading = ref(true)

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function createConversation() {
  try {
    const res = await api.post('/tenant-portal/conversations/', {})
    router.push({ name: 'chat-detail', params: { id: res.data.id } })
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await api.get('/tenant-portal/conversations/')
    conversations.value = res.data.results ?? res.data
  } finally {
    loading.value = false
  }
})
</script>
