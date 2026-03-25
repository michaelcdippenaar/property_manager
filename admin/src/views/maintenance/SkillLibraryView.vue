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
        <span v-if="ragStatus" class="text-xs text-gray-500">
          RAG chunks: <strong>{{ ragStatus.chunks ?? '—' }}</strong>
          <span v-if="ragStatus.web_fetch_enabled" class="ml-2 text-indigo-600">· web fetch on</span>
        </span>
      </div>
      <p class="text-xs text-gray-500">
        Run <code class="bg-gray-100 px-1 rounded">python manage.py ingest_contract_documents</code> on the server to
        (re)build the vector index. Set <code class="bg-gray-100 px-1 rounded">ANTHROPIC_WEB_FETCH_ENABLED=true</code>
        for internet access (ask-before-fetch rules apply in the model).
      </p>
      <textarea
        v-model="agentMsg"
        rows="4"
        class="input w-full text-sm"
        placeholder="Ask about a lease clause, house rules, or maintenance context…"
        :disabled="agentLoading"
      />
      <div class="flex gap-2">
        <button type="button" class="btn-primary text-sm" :disabled="agentLoading || !agentMsg.trim()" @click="runAgent">
          {{ agentLoading ? 'Thinking…' : 'Ask agent' }}
        </button>
      </div>
      <div v-if="agentMeta" class="text-xs text-gray-400">
        RAG hits in prompt: {{ agentMeta.rag_populated ? 'yes' : 'no' }}
        <span v-if="agentMeta.rag_chunks_returned">({{ agentMeta.rag_chunks_returned }} excerpts)</span>
      </div>
      <div
        v-if="agentReply"
        class="text-sm text-gray-800 whitespace-pre-wrap border border-gray-100 rounded-lg p-3 bg-gray-50 max-h-[min(60vh,480px)] overflow-y-auto"
      >
        {{ agentReply }}
      </div>
      <div v-if="agentError" class="text-sm text-red-600">{{ agentError }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const skills = ref<any[]>([])
const skillsLoading = ref(false)
const skillsError = ref('')

const ragStatus = ref<any>(null)
const agentMsg = ref('')
const agentReply = ref('')
const agentError = ref('')
const agentLoading = ref(false)
const agentMeta = ref<{ rag_populated?: boolean; rag_chunks_returned?: number } | null>(null)

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

async function runAgent() {
  agentError.value = ''
  agentReply.value = ''
  agentMeta.value = null
  agentLoading.value = true
  try {
    const { data } = await api.post('/maintenance/agent-assist/chat/', {
      message: agentMsg.value.trim(),
    })
    agentReply.value = data.reply ?? ''
    agentMeta.value = {
      rag_populated: data.rag_populated,
      rag_chunks_returned: data.rag_chunks_returned,
    }
  } catch (e: any) {
    agentError.value =
      e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Request failed.'
  } finally {
    agentLoading.value = false
  }
}
</script>
