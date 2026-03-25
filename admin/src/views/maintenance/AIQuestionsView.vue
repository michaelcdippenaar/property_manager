<template>
  <!-- Full-height split pane — needs to break out of the default p-6 scroll container -->
  <div class="-m-6 h-[calc(100vh-3.5rem)] flex overflow-hidden">

    <!-- ── LEFT LIST ──────────────────────────────────────────── -->
    <div class="w-80 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col overflow-hidden">

      <!-- Header + filter -->
      <div class="px-4 pt-4 pb-2 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center gap-2 mb-3">
          <HelpCircle :size="16" class="text-violet-500" />
          <h2 class="text-sm font-semibold text-gray-900">AI Questions</h2>
          <span
            v-if="pendingCount"
            class="ml-auto text-xs font-semibold bg-violet-100 text-violet-700 rounded-full px-2 py-0.5"
          >{{ pendingCount }}</span>
        </div>
        <!-- Status filter pills -->
        <div class="flex gap-1">
          <button
            v-for="f in statusFilters"
            :key="f.value"
            @click="activeStatus = f.value; loadQuestions()"
            class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
            :class="activeStatus === f.value
              ? 'bg-navy text-white'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
          >{{ f.label }}</button>
        </div>
      </div>

      <!-- Question list -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="listLoading" class="p-4 space-y-3">
          <div v-for="i in 5" :key="i" class="animate-pulse space-y-1.5">
            <div class="h-3 bg-gray-100 rounded w-1/3" />
            <div class="h-3.5 bg-gray-100 rounded w-full" />
            <div class="h-3 bg-gray-100 rounded w-4/5" />
          </div>
        </div>

        <div v-else-if="!questions.length" class="p-6 text-center text-gray-400 text-sm">
          <CheckCircle2 :size="28" class="mx-auto mb-2 text-gray-300" />
          No questions for this filter
        </div>

        <button
          v-for="q in questions"
          :key="q.id"
          @click="selectQuestion(q)"
          class="w-full text-left px-4 py-3.5 border-b border-gray-100 transition-colors hover:bg-gray-50"
          :class="selected?.id === q.id ? 'bg-violet-50 border-l-2 border-l-violet-500 pl-3.5' : ''"
        >
          <!-- Category badge + status dot -->
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
              :class="categoryStyle(q.category)"
            >{{ q.category }}</span>
            <span class="ml-auto w-2 h-2 rounded-full flex-shrink-0"
              :class="statusDot(q.status)"
            />
          </div>
          <!-- Question text (3 lines) -->
          <p class="text-xs text-gray-800 leading-relaxed line-clamp-3 mb-1.5">{{ q.question }}</p>
          <!-- Meta -->
          <div class="flex items-center gap-1 text-[10px] text-gray-400">
            <span v-if="q.property_name" class="truncate max-w-[100px]">{{ q.property_name }}</span>
            <span v-if="q.property_name">·</span>
            <span class="truncate">{{ formatDate(q.created_at) }}</span>
          </div>
        </button>
      </div>
    </div>

    <!-- ── RIGHT PANEL ─────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">

      <!-- Empty state -->
      <div v-if="!selected" class="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
        <HelpCircle :size="40" class="text-gray-300" />
        <p class="text-sm font-medium text-gray-500">Select a question to review</p>
        <p class="text-xs text-gray-400">The AI flagged these for human input</p>
      </div>

      <template v-else>
        <!-- Context strip (amber) -->
        <div class="flex-shrink-0 bg-amber-50 border-b border-amber-200 px-5 py-3">
          <div class="flex items-start gap-3">
            <AlertCircle :size="15" class="text-amber-500 mt-0.5 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs font-semibold text-amber-800">
                  {{ selected.context_source || 'AI flagged question' }}
                </span>
                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide"
                  :class="categoryStyle(selected.category)"
                >{{ selected.category }}</span>
                <span v-if="selected.property_name" class="text-[10px] text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded">
                  {{ selected.property_name }}
                </span>
              </div>
              <p class="text-xs text-amber-700 mt-0.5">
                Raised {{ formatDate(selected.created_at) }}
                <span v-if="selected.answered_by_name"> · Answered by {{ selected.answered_by_name }}</span>
              </p>
            </div>
            <!-- Dismiss button for pending -->
            <button
              v-if="selected.status === 'pending'"
              @click="dismiss"
              :disabled="actionLoading"
              class="text-xs text-amber-600 hover:text-amber-800 font-medium transition-colors flex-shrink-0 disabled:opacity-50"
            >Dismiss</button>
          </div>
        </div>

        <!-- Scrollable body -->
        <div class="flex-1 overflow-y-auto p-5 space-y-4">

          <!-- Full question -->
          <div class="bg-white rounded-xl border border-amber-200 p-4 shadow-sm">
            <p class="text-xs font-semibold text-amber-700 mb-1.5 uppercase tracking-wide">Question from AI</p>
            <p class="text-sm text-gray-800 leading-relaxed">{{ selected.question }}</p>
          </div>

          <!-- Answered state -->
          <div v-if="selected.status === 'answered'" class="bg-emerald-50 rounded-xl border border-emerald-200 p-4">
            <div class="flex items-center gap-2 mb-1.5">
              <CheckCircle2 :size="14" class="text-emerald-600" />
              <p class="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Answer</p>
              <span v-if="selected.added_to_context"
                class="ml-auto text-[10px] bg-emerald-100 text-emerald-700 font-semibold px-2 py-0.5 rounded-full">
                Added to AI context
              </span>
            </div>
            <p class="text-sm text-gray-800 leading-relaxed">{{ selected.answer }}</p>
          </div>

          <!-- Dismissed state -->
          <div v-if="selected.status === 'dismissed'"
            class="bg-gray-100 rounded-xl border border-gray-200 p-4 text-center text-sm text-gray-500"
          >
            This question was dismissed.
          </div>

          <!-- Answer form (pending only) -->
          <div v-if="selected.status === 'pending'" class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-2">Your Answer</label>
            <textarea
              v-model="answerText"
              rows="5"
              placeholder="Type your answer here — it will be added to the AI's knowledge base for this property…"
              class="w-full text-sm text-gray-800 border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-violet-400/40 focus:border-violet-400 placeholder:text-gray-400"
            />
            <p v-if="answerError" class="text-xs text-red-600 mt-1">{{ answerError }}</p>
            <div class="flex justify-end mt-3">
              <button
                @click="submitAnswer"
                :disabled="!answerText.trim() || actionLoading"
                class="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-40"
              >
                <Send :size="13" />
                {{ actionLoading ? 'Submitting…' : 'Submit Answer' }}
              </button>
            </div>
          </div>

        </div>
      </template>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { HelpCircle, AlertCircle, CheckCircle2, Send } from 'lucide-vue-next'

interface AgentQuestion {
  id: number
  question: string
  answer: string
  category: string
  status: string
  context_source: string
  property: number | null
  property_name: string
  answered_by: number | null
  answered_by_name: string
  answered_at: string | null
  added_to_context: boolean
  created_at: string
  updated_at: string
}

const questions = ref<AgentQuestion[]>([])
const selected = ref<AgentQuestion | null>(null)
const listLoading = ref(true)
const actionLoading = ref(false)
const answerText = ref('')
const answerError = ref('')
const activeStatus = ref('pending')

const statusFilters = [
  { label: 'Pending', value: 'pending' },
  { label: 'Answered', value: 'answered' },
  { label: 'Dismissed', value: 'dismissed' },
  { label: 'All', value: '' },
]

const pendingCount = computed(() =>
  activeStatus.value === 'pending' ? questions.value.length : undefined
)

onMounted(() => loadQuestions())

async function loadQuestions() {
  listLoading.value = true
  selected.value = null
  try {
    const params: Record<string, string> = {}
    if (activeStatus.value) params.status = activeStatus.value
    const { data } = await api.get('/maintenance/agent-questions/', { params })
    questions.value = data.results ?? data
  } catch {
    questions.value = []
  } finally {
    listLoading.value = false
  }
}

function selectQuestion(q: AgentQuestion) {
  selected.value = q
  answerText.value = q.answer || ''
  answerError.value = ''
}

async function submitAnswer() {
  if (!selected.value || !answerText.value.trim()) return
  answerError.value = ''
  actionLoading.value = true
  try {
    const { data } = await api.post(
      `/maintenance/agent-questions/${selected.value.id}/answer/`,
      { answer: answerText.value.trim() }
    )
    // Update in list and selected
    selected.value = data
    const idx = questions.value.findIndex((q) => q.id === data.id)
    if (idx !== -1) questions.value[idx] = data
    // If filtering by pending, remove from list
    if (activeStatus.value === 'pending') {
      questions.value = questions.value.filter((q) => q.id !== data.id)
      selected.value = null
    }
  } catch (e: any) {
    answerError.value = e?.response?.data?.error || 'Failed to submit answer.'
  } finally {
    actionLoading.value = false
  }
}

async function dismiss() {
  if (!selected.value) return
  actionLoading.value = true
  try {
    const { data } = await api.post(
      `/maintenance/agent-questions/${selected.value.id}/dismiss/`
    )
    selected.value = data
    const idx = questions.value.findIndex((q) => q.id === data.id)
    if (idx !== -1) questions.value[idx] = data
    if (activeStatus.value === 'pending') {
      questions.value = questions.value.filter((q) => q.id !== data.id)
      selected.value = null
    }
  } finally {
    actionLoading.value = false
  }
}

function categoryStyle(cat: string): string {
  const map: Record<string, string> = {
    property:    'bg-blue-100 text-blue-700',
    lease:       'bg-purple-100 text-purple-700',
    maintenance: 'bg-orange-100 text-orange-700',
    tenant:      'bg-pink-100 text-pink-700',
    supplier:    'bg-teal-100 text-teal-700',
    policy:      'bg-gray-200 text-gray-700',
    other:       'bg-gray-100 text-gray-600',
  }
  return map[cat] ?? 'bg-gray-100 text-gray-600'
}

function statusDot(s: string): string {
  return s === 'pending' ? 'bg-amber-400' : s === 'answered' ? 'bg-emerald-400' : 'bg-gray-300'
}

function formatDate(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>
