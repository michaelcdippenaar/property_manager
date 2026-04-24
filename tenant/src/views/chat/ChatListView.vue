<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="AI Assistant" show-back back-label="Home" />

    <div class="scroll-page px-4 pt-4 pb-24 space-y-2">
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 3" :key="i" class="h-16 bg-white rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="conversations.length === 0" class="flex flex-col items-center justify-center pt-16 text-center px-2">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <MessageCircle :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No conversations yet</p>
        <p class="text-sm text-gray-400 mt-1 max-w-xs leading-relaxed">
          Ask about your lease, maintenance requests, or anything about your property
        </p>

        <!-- Suggested starter prompts -->
        <div class="mt-6 w-full max-w-sm space-y-2">
          <button
            v-for="prompt in suggestedPrompts"
            :key="prompt"
            class="w-full text-left px-4 py-3 bg-white border border-gray-200 rounded-2xl text-sm text-gray-700 font-medium touchable ripple shadow-sm"
            @click="startWithPrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
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
    <button class="fab fab--labeled" @click="createConversation()">
      <Plus :size="20" />
      <span class="fab-label">New conversation</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessageCircle, ChevronRight, Plus, Bot } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const router = useRouter()
const toast = useToast()
const conversations = ref<any[]>([])
const loading = ref(true)

const suggestedPrompts = [
  'Report a repair',
  'When is my rent due?',
  'What does my lease say about pets?',
]

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function createConversation(prefill?: string) {
  try {
    const res = await api.post('/tenant-portal/conversations/', {})
    router.push({ name: 'chat-detail', params: { id: res.data.id }, query: prefill ? { prefill } : undefined })
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 401 || status === 403) {
      router.push({ name: 'login' })
    } else {
      toast.error("Couldn't start a chat — please try again")
    }
  }
}

async function startWithPrompt(prompt: string) {
  await createConversation(prompt)
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
