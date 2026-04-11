<template>
  <q-page class="page-container">

    <!-- Loading -->
    <div v-if="loading" class="column q-gutter-sm">
      <q-skeleton v-for="i in 3" :key="i" type="QItem" height="60px" class="rounded-borders" />
    </div>

    <!-- Empty -->
    <div v-else-if="conversations.length === 0" class="text-center q-pt-xl">
      <q-icon name="chat" :size="EMPTY_ICON_SIZE" color="grey-3" class="q-mb-md" />
      <div class="text-weight-semibold text-grey-8">No conversations yet</div>
      <div class="text-caption text-grey-5 q-mt-xs">Start a new chat with your AI assistant</div>
    </div>

    <!-- Conversation list -->
    <q-card v-else flat>
      <q-list separator>
        <q-item
          v-for="conv in conversations"
          :key="conv.id"
          clickable
          v-ripple
          @click="$router.push(`/chat/${conv.id}`)"
        >
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="36px">
              <q-icon name="smart_toy" size="18px" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold ellipsis">{{ conv.title || 'New conversation' }}</q-item-label>
            <q-item-label caption>{{ formatDateShort(conv.updated_at ?? conv.created_at) }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- New chat FAB -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" color="secondary" @click="startNewChat" aria-label="New chat" />
    </q-page-sticky>

  </q-page>
</template>

<script setup lang="ts">
defineOptions({ name: 'ChatListPage' })

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as tenantApi from '../services/api'
import type { Conversation } from '../services/api'
import { EMPTY_ICON_SIZE } from '../utils/designTokens'

const router = useRouter()

const conversations = ref<Conversation[]>([])
const loading       = ref(true)

function formatDateShort(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function startNewChat() {
  try {
    const res = await tenantApi.createConversation()
    router.push(`/chat/${res.data.id}`)
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await tenantApi.listConversations()
    conversations.value = res.data.results ?? res.data as Conversation[]
  } finally {
    loading.value = false
  }
})
</script>
