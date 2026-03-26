<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-lg font-semibold text-gray-800">Agent Questions</h2>
      <div class="flex gap-2">
        <select v-model="statusFilter" class="input text-sm w-36" @change="loadQuestions">
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="answered">Answered</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>
    </div>

    <p class="text-sm text-gray-500">
      Questions the AI could not answer from existing context. Answering a question adds it to the
      AI's knowledge base (RAG) so it can answer similar questions in future.
    </p>

    <div v-if="loading" class="text-sm text-gray-400">Loading…</div>
    <div v-else-if="error" class="text-sm text-red-600">{{ error }}</div>
    <div v-else-if="questions.length === 0" class="text-sm text-gray-400 py-8 text-center">
      No questions{{ statusFilter ? ` with status "${statusFilter}"` : '' }}.
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="q in questions"
        :key="q.id"
        class="card p-4 space-y-3"
        :class="{
          'border-l-4 border-amber-400': q.status === 'pending',
          'border-l-4 border-green-400': q.status === 'answered',
          'border-l-4 border-gray-300': q.status === 'dismissed',
        }"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-800">{{ q.question }}</div>
            <div class="text-xs text-gray-400 mt-1 space-x-3">
              <span>Category: {{ q.category }}</span>
              <span v-if="q.context_source">Source: {{ q.context_source }}</span>
              <span>{{ formatDate(q.created_at) }}</span>
            </div>
          </div>
          <span
            class="text-xs px-2 py-0.5 rounded-full font-medium"
            :class="{
              'bg-amber-100 text-amber-700': q.status === 'pending',
              'bg-green-100 text-green-700': q.status === 'answered',
              'bg-gray-100 text-gray-500': q.status === 'dismissed',
            }"
          >
            {{ q.status }}
          </span>
        </div>

        <!-- Answer display (if answered) -->
        <div v-if="q.status === 'answered' && q.answer" class="bg-green-50 rounded-lg p-3 text-sm text-gray-700">
          <div class="text-xs text-green-600 font-semibold mb-1">
            Answer{{ q.answered_by_name ? ` by ${q.answered_by_name}` : '' }}
            <span v-if="q.added_to_context" class="ml-2 text-indigo-600">· Added to AI knowledge</span>
          </div>
          {{ q.answer }}
        </div>

        <!-- Answer form (if pending) -->
        <div v-if="q.status === 'pending'" class="space-y-2">
          <textarea
            v-model="answerDrafts[q.id]"
            rows="3"
            class="input w-full text-sm"
            placeholder="Type your answer… This will be added to the AI's knowledge base."
            :disabled="submitting[q.id]"
          />
          <div class="flex gap-2">
            <button
              type="button"
              class="btn-primary text-sm"
              :disabled="submitting[q.id] || !(answerDrafts[q.id] || '').trim()"
              @click="submitAnswer(q)"
            >
              {{ submitting[q.id] ? 'Saving…' : 'Answer & Add to AI' }}
            </button>
            <button
              type="button"
              class="btn text-sm text-gray-500 hover:text-gray-700"
              :disabled="submitting[q.id]"
              @click="dismissQuestion(q)"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '../../api'

interface AgentQuestion {
  id: number
  question: string
  answer: string
  category: string
  status: string
  context_source: string
  answered_by_name?: string
  added_to_context: boolean
  created_at: string
}

const questions = ref<AgentQuestion[]>([])
const loading = ref(false)
const error = ref('')
const statusFilter = ref('pending')
const answerDrafts = reactive<Record<number, string>>({})
const submitting = reactive<Record<number, boolean>>({})

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function loadQuestions() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string> = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/maintenance/agent-questions/', { params })
    questions.value = Array.isArray(data) ? data : data.results ?? []
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? 'Could not load questions.'
  } finally {
    loading.value = false
  }
}

async function submitAnswer(q: AgentQuestion) {
  const answer = (answerDrafts[q.id] || '').trim()
  if (!answer) return
  submitting[q.id] = true
  try {
    const { data } = await api.post(`/maintenance/agent-questions/${q.id}/answer/`, { answer })
    // Update in-place
    Object.assign(q, data)
  } catch (e: any) {
    error.value = e?.response?.data?.error ?? 'Failed to submit answer.'
  } finally {
    submitting[q.id] = false
  }
}

async function dismissQuestion(q: AgentQuestion) {
  submitting[q.id] = true
  try {
    const { data } = await api.post(`/maintenance/agent-questions/${q.id}/dismiss/`)
    Object.assign(q, data)
  } catch (e: any) {
    error.value = e?.response?.data?.error ?? 'Failed to dismiss.'
  } finally {
    submitting[q.id] = false
  }
}

onMounted(loadQuestions)
</script>
