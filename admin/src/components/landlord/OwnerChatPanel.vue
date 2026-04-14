<template>
  <div class="card flex flex-col h-[640px] max-h-[80vh]">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
      <div class="flex items-center gap-2">
        <Sparkles :size="16" class="text-accent-500" />
        <div>
          <div class="text-sm font-semibold text-gray-900">Mandate Assistant</div>
          <div class="text-xs text-gray-500">
            AI onboarding — checks docs, asks what's missing
          </div>
        </div>
      </div>
      <button
        class="text-xs text-gray-500 hover:text-gray-700"
        :disabled="sending"
        @click="refresh"
      >
        Refresh
      </button>
    </div>

    <!-- Message list -->
    <div
      ref="scrollEl"
      class="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-gray-50"
    >
      <div
        v-if="loading && !visibleMessages.length"
        class="text-xs text-gray-500 italic"
      >
        Loading conversation…
      </div>

      <div
        v-else-if="!visibleMessages.length && !sending"
        class="text-xs text-gray-500 italic"
      >
        Say hi to start — the assistant will review the documents on file.
      </div>

      <template v-for="msg in visibleMessages" :key="msg.id">
        <!-- User bubble -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div
            class="max-w-[85%] rounded-lg bg-[#2B2D6E] text-white px-3 py-2 text-sm whitespace-pre-wrap shadow-sm"
          >
            {{ msg.content }}
          </div>
        </div>

        <!-- Assistant bubble (+ tool-call CTAs) -->
        <div v-else-if="msg.role === 'assistant'" class="space-y-2">
          <div
            v-if="msg.content"
            class="max-w-[90%] rounded-lg bg-white border border-gray-200 px-3 py-2 text-sm text-gray-900 whitespace-pre-wrap shadow-sm"
          >
            {{ msg.content }}
          </div>

          <!-- Tool calls (upload CTAs, field-update confirmations) -->
          <div
            v-for="(tc, idx) in extractToolUses(msg)"
            :key="`${msg.id}-tc-${idx}`"
            class="max-w-[90%]"
          >
            <!-- request_document_upload -->
            <div
              v-if="tc.name === 'request_document_upload'"
              class="flex items-center justify-between rounded-lg border border-accent-200 bg-accent-50 px-3 py-2"
            >
              <div class="flex items-center gap-2 min-w-0">
                <FileUp :size="16" class="text-accent-600 shrink-0" />
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-gray-900 truncate">
                    Upload: {{ prettyDocType(tc.input?.doc_type) }}
                  </div>
                  <div class="text-[11px] text-gray-600 truncate">
                    {{ tc.input?.reason }}
                  </div>
                </div>
              </div>
              <button
                class="text-xs font-semibold text-accent-700 hover:text-accent-800 whitespace-nowrap ml-2"
                @click="$emit('request-upload', String(tc.input?.doc_type ?? ''))"
              >
                Upload
              </button>
            </div>

            <!-- update_landlord_field -->
            <div
              v-else-if="tc.name === 'update_landlord_field'"
              class="flex items-center gap-2 rounded-lg border border-success-200 bg-success-50 px-3 py-2"
            >
              <CheckCircle2 :size="14" class="text-success-600" />
              <div class="text-xs text-gray-700">
                Saved
                <span class="font-semibold">{{ tc.input?.field }}</span>:
                <span class="font-mono">{{ tc.input?.value }}</span>
              </div>
            </div>

            <!-- get_gap_analysis / search_owner_documents — just a subtle chip -->
            <div
              v-else-if="tc.name === 'get_gap_analysis' || tc.name === 'search_owner_documents'"
              class="inline-flex items-center gap-1.5 text-[11px] text-gray-500 italic"
            >
              <Search :size="11" />
              {{ tc.name === 'get_gap_analysis' ? 'Checked gap analysis' : 'Searched documents' }}
            </div>

            <!-- trigger_reclassification -->
            <div
              v-else-if="tc.name === 'trigger_reclassification'"
              class="inline-flex items-center gap-1.5 text-[11px] text-gray-500 italic"
            >
              <RefreshCw :size="11" />
              Re-ran document analysis
            </div>
          </div>
        </div>
      </template>

      <div v-if="sending" class="text-xs text-gray-500 italic">
        <Loader2 :size="12" class="inline animate-spin mr-1" />
        Thinking…
      </div>

      <div v-if="errorMsg" class="text-xs text-danger-600">
        {{ errorMsg }}
      </div>
    </div>

    <!-- Composer -->
    <div class="border-t border-gray-200 p-3 bg-white">
      <form class="flex items-end gap-2" @submit.prevent="submit">
        <textarea
          v-model="draft"
          :disabled="sending"
          class="input flex-1 resize-none text-sm"
          rows="2"
          placeholder="Type a reply… (Enter to send, Shift+Enter for new line)"
          @keydown.enter.exact.prevent="submit"
        />
        <button
          type="submit"
          class="btn-primary px-3 py-2 text-sm"
          :disabled="sending || !draft.trim()"
        >
          <Send :size="14" />
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  CheckCircle2,
  FileUp,
  Loader2,
  RefreshCw,
  Search,
  Send,
  Sparkles,
} from 'lucide-vue-next'

import type { ChatMessage, ContentBlock } from '../../api/ownerChat'
import { useOwnerChatStore } from '../../stores/ownerChat'

const props = defineProps<{ landlordId: number }>()
defineEmits<{ (e: 'request-upload', docType: string): void }>()

const chat = useOwnerChatStore()

const draft = ref('')
const scrollEl = ref<HTMLElement | null>(null)

const allMessages = computed<ChatMessage[]>(() => chat.messages(props.landlordId))
const loading = computed(() => chat.isLoading(props.landlordId))
const sending = computed(() => chat.isSending(props.landlordId))
const errorMsg = computed(() => chat.error(props.landlordId))

/** Hide raw tool_result turns (they're noisy) — keep user + assistant. */
const visibleMessages = computed<ChatMessage[]>(() =>
  allMessages.value.filter((m) => {
    if (m.role === 'assistant') return true
    if (m.role === 'user') {
      // Skip tool_result-only turns (empty content + tool_calls present)
      const hasContent = !!(m.content && m.content.trim())
      const isToolResult =
        Array.isArray(m.tool_calls) &&
        m.tool_calls.some((b) => b?.type === 'tool_result')
      return hasContent || !isToolResult
    }
    return false
  }),
)

function extractToolUses(msg: ChatMessage): ContentBlock[] {
  if (!Array.isArray(msg.tool_calls)) return []
  return msg.tool_calls.filter((b) => b?.type === 'tool_use')
}

function prettyDocType(raw: unknown): string {
  const s = String(raw ?? '')
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

async function submit(): Promise<void> {
  const msg = draft.value.trim()
  if (!msg || sending.value) return
  draft.value = ''
  await chat.send(props.landlordId, msg)
}

async function refresh(): Promise<void> {
  // Sending an empty message prompts the assistant to re-greet if first turn.
  if (!allMessages.value.length) {
    await chat.send(props.landlordId, '')
  } else {
    await chat.load(props.landlordId)
  }
}

function scrollToBottom(): void {
  void nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

onMounted(async () => {
  await chat.load(props.landlordId)
  // First-open auto-greet: if there's no history, kick the assistant.
  if (!allMessages.value.length) {
    await chat.send(props.landlordId, '')
  }
  scrollToBottom()
})

watch(
  () => allMessages.value.length,
  () => scrollToBottom(),
)

watch(
  () => props.landlordId,
  async (id) => {
    if (!id) return
    await chat.load(id)
  },
)
</script>
