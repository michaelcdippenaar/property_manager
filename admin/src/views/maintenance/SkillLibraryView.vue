<template>
  <div class="space-y-6">
    <p class="text-sm text-gray-500">
      Maintenance skills in the database. Use the agent below to query <strong>vectorized contracts</strong> from
      <code class="text-xs bg-gray-100 px-1 rounded">backend/documents</code> plus skill context.
    </p>

    <div class="card p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-sm font-semibold text-gray-800">Skills</span>
        <span v-if="skillsLoading" class="text-xs text-gray-400">Loading…</span>
        <span v-else class="text-xs text-gray-500">{{ skills.length }} active</span>
      </div>
      <div v-if="skillsError" class="text-sm text-red-600">{{ skillsError }}</div>
      <ul v-else class="max-h-48 overflow-y-auto text-sm text-gray-700 space-y-1 border border-gray-100 rounded-lg p-2">
        <li v-for="s in skills.slice(0, 200)" :key="s.id" class="truncate">
          <span class="text-gray-400 font-mono text-xs">{{ s.trade }}</span>
          · {{ s.name }}
        </li>
      </ul>
      <p v-if="skills.length > 200" class="text-xs text-gray-400">Showing first 200.</p>
    </div>

    <div class="card p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-sm font-semibold text-gray-800">Agent assistant</span>
        <div class="flex items-center gap-3">
          <span v-if="ragStatus" class="text-xs text-gray-500">
            RAG: <strong>{{ ragStatus.chunks ?? '—' }}</strong> chunks
            <span v-if="ragStatus.agent_qa_chunks"> · Q&amp;A: <strong>{{ ragStatus.agent_qa_chunks }}</strong></span>
            <span v-if="ragStatus.chat_knowledge_chunks"> · Learned: <strong>{{ ragStatus.chat_knowledge_chunks }}</strong></span>
            <span v-if="ragStatus.embedding_model" class="ml-1 text-gray-400">({{ ragStatus.embedding_model.split('/').pop() }})</span>
            <span v-if="ragStatus.web_fetch_enabled" class="ml-2 text-indigo-600">· web fetch on</span>
          </span>
          <button
            v-if="chatHistory.length > 0"
            type="button"
            class="text-xs text-gray-400 hover:text-gray-600 underline"
            @click="clearHistory"
          >
            Clear history
          </button>
        </div>
      </div>
      <p class="text-xs text-gray-500">
        Run <code class="bg-gray-100 px-1 rounded">python manage.py ingest_contract_documents</code> on the server to
        (re)build the vector index. Set <code class="bg-gray-100 px-1 rounded">ANTHROPIC_WEB_FETCH_ENABLED=true</code>
        for internet access (ask-before-fetch rules apply in the model).
      </p>

      <!-- Chat history display -->
      <div
        v-if="chatHistory.length > 0"
        class="max-h-[min(50vh,400px)] overflow-y-auto border border-gray-100 rounded-lg p-3 space-y-3 bg-gray-50"
      >
        <div
          v-for="(msg, idx) in chatHistory"
          :key="idx"
          :class="[
            'text-sm rounded-lg p-2',
            msg.role === 'user'
              ? 'bg-indigo-50 text-indigo-900 ml-8'
              : 'bg-white text-gray-800 mr-8 border border-gray-200'
          ]"
        >
          <div class="text-xs font-semibold mb-1" :class="msg.role === 'user' ? 'text-indigo-600' : 'text-gray-500'">
            {{ msg.role === 'user' ? 'You' : 'Agent' }}
          </div>
          <div class="whitespace-pre-wrap">{{ msg.content }}</div>
        </div>
      </div>

      <textarea
        v-model="agentMsg"
        rows="4"
        class="input w-full text-sm"
        placeholder="Ask about a lease clause, house rules, or maintenance context…"
        :disabled="agentLoading"
        @keydown.meta.enter="runAgent"
        @keydown.ctrl.enter="runAgent"
      />
      <div class="flex gap-2">
        <button type="button" class="btn-primary text-sm" :disabled="agentLoading || !agentMsg.trim()" @click="runAgent">
          {{ agentLoading ? 'Thinking…' : 'Ask agent' }}
        </button>
        <span v-if="chatHistory.length > 0" class="text-xs text-gray-400 self-center">
          {{ chatHistory.length }} messages in context
        </span>
      </div>
      <div v-if="agentMeta" class="text-xs text-gray-400">
        RAG hits in prompt: {{ agentMeta.rag_populated ? 'yes' : 'no' }}
        <span v-if="agentMeta.rag_chunks_returned">({{ agentMeta.rag_chunks_returned }} excerpts)</span>
        <span v-if="agentMeta.qa_populated" class="ml-2">· Staff Q&amp;A: yes</span>
      </div>
      <div v-if="agentError" class="text-sm text-red-600">{{ agentError }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const skills = ref<any[]>([])
const skillsLoading = ref(false)
const skillsError = ref('')

const ragStatus = ref<any>(null)
const agentMsg = ref('')
const agentError = ref('')
const agentLoading = ref(false)
const agentMeta = ref<{
  rag_populated?: boolean
  rag_chunks_returned?: number
  qa_populated?: boolean
} | null>(null)

// Multi-turn conversation history — sent with every request
const chatHistory = ref<ChatMessage[]>([])

onMounted(async () => {
  skillsLoading.value = true
  try {
    const { data } = await api.get('/maintenance/skills/', { params: { is_active: true } })
    skills.value = Array.isArray(data) ? data : data.results ?? []
  } catch (e: any) {
    skillsError.value = e?.response?.data?.detail ?? 'Could not load skills.'
    skills.value = []
  } finally {
    skillsLoading.value = false
  }
  try {
    const { data } = await api.get('/maintenance/agent-assist/rag-status/')
    ragStatus.value = data
  } catch {
    ragStatus.value = null
  }
})

function clearHistory() {
  chatHistory.value = []
  agentMeta.value = null
}

async function runAgent() {
  if (!agentMsg.value.trim() || agentLoading.value) return

  const userMessage = agentMsg.value.trim()
  agentError.value = ''
  agentMeta.value = null
  agentLoading.value = true

  // Add user message to history immediately (optimistic)
  chatHistory.value.push({ role: 'user', content: userMessage })
  agentMsg.value = ''

  try {
    const { data } = await api.post('/maintenance/agent-assist/chat/', {
      message: userMessage,
      history: chatHistory.value.slice(0, -1), // Send prior history (excluding current message which is sent as `message`)
    })
    const reply = data.reply ?? ''
    // Add assistant reply to history
    chatHistory.value.push({ role: 'assistant', content: reply })
    agentMeta.value = {
      rag_populated: data.rag_populated,
      rag_chunks_returned: data.rag_chunks_returned,
      qa_populated: data.qa_populated,
    }
  } catch (e: any) {
    agentError.value =
      e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Request failed.'
    // Remove the user message from history since request failed
    chatHistory.value.pop()
  } finally {
    agentLoading.value = false
  }
}
</script>
