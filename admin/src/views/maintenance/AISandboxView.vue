<template>
  <div class="-m-6 h-[calc(100vh-3.5rem)] flex overflow-hidden">

    <!-- ── LEFT: Config Panel ───────────────────────────────── -->
    <div class="w-72 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col overflow-hidden">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center gap-2">
          <Bot :size="16" class="text-indigo-500" />
          <h2 class="text-sm font-semibold text-gray-900">AI Sandbox</h2>
        </div>
        <p class="text-[10px] text-gray-400 mt-1">Test the maintenance agent with different contexts</p>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <!-- Property selector -->
        <div>
          <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-1.5">Property</label>
          <select v-model="selectedProperty" class="input text-sm w-full">
            <option :value="null">All properties</option>
            <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <!-- Context mode -->
        <div>
          <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-1.5">Context</label>
          <div class="space-y-1.5">
            <label v-for="mode in contextModes" :key="mode.value"
              class="flex items-center gap-2 text-xs text-gray-700 cursor-pointer"
            >
              <input type="radio" v-model="contextMode" :value="mode.value"
                class="w-3.5 h-3.5 text-indigo-600 border-gray-300 focus:ring-indigo-500" />
              {{ mode.label }}
            </label>
          </div>
        </div>

        <!-- Agent capabilities -->
        <div>
          <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-1.5">Capabilities</label>
          <div class="space-y-1.5">
            <label v-for="cap in capabilities" :key="cap.key"
              class="flex items-center gap-2 text-xs text-gray-700 cursor-pointer"
            >
              <input type="checkbox" v-model="cap.enabled"
                class="w-3.5 h-3.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500" />
              {{ cap.label }}
            </label>
          </div>
        </div>

        <!-- Quick prompts -->
        <div>
          <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide block mb-1.5">Quick Prompts</label>
          <div class="space-y-1">
            <button
              v-for="prompt in quickPrompts"
              :key="prompt.text"
              @click="sendMessage(prompt.text)"
              class="w-full text-left text-xs px-3 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
            >
              {{ prompt.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Clear button -->
      <div class="p-3 border-t border-gray-100 flex-shrink-0">
        <button @click="clearChat" class="w-full text-xs text-gray-500 hover:text-red-600 py-1.5 transition-colors font-medium">
          <Trash2 :size="12" class="inline -mt-0.5 mr-1" />
          Clear conversation
        </button>
      </div>
    </div>

    <!-- ── CENTER: Chat ─────────────────────────────────────── -->
    <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-5 space-y-4">
        <!-- Welcome state -->
        <div v-if="!messages.length" class="flex flex-col items-center justify-center h-full text-center">
          <div class="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center mb-4">
            <Bot :size="28" class="text-indigo-500" />
          </div>
          <h3 class="text-sm font-semibold text-gray-700 mb-1">AI Maintenance Agent</h3>
          <p class="text-xs text-gray-400 max-w-xs leading-relaxed">
            Test the agent's ability to triage maintenance requests, match suppliers, answer tenant questions, and flag unknowns.
          </p>
          <div class="flex gap-2 mt-5 flex-wrap justify-center">
            <button
              v-for="prompt in quickPrompts.slice(0, 3)"
              :key="prompt.text"
              @click="sendMessage(prompt.text)"
              class="px-3 py-2 rounded-lg border border-gray-200 bg-white text-xs text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors shadow-sm"
            >
              {{ prompt.label }}
            </button>
          </div>
        </div>

        <!-- Message bubbles -->
        <div v-for="(msg, i) in messages" :key="i"
          class="flex gap-3"
          :class="msg.role === 'user' ? 'justify-end' : ''"
        >
          <!-- Agent avatar -->
          <div v-if="msg.role === 'assistant'" class="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Bot :size="14" class="text-indigo-600" />
          </div>

          <div
            class="max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed"
            :class="msg.role === 'user'
              ? 'bg-navy text-white rounded-br-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'"
          >
            <!-- Flagged question indicator -->
            <div v-if="msg.flagged" class="flex items-center gap-1.5 mb-1.5 text-amber-600 text-xs font-semibold">
              <AlertCircle :size="12" />
              Flagged for human review
            </div>
            <div v-html="renderMarkdown(msg.content)" class="prose-sm" />
            <div class="text-[10px] mt-1.5 opacity-50">{{ formatTime(msg.timestamp) }}</div>
          </div>

          <!-- User avatar -->
          <div v-if="msg.role === 'user'" class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center flex-shrink-0 mt-0.5">
            <User :size="14" class="text-white" />
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="thinking" class="flex gap-3">
          <div class="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
            <Bot :size="14" class="text-indigo-600" />
          </div>
          <div class="bg-white border border-gray-200 rounded-xl rounded-bl-sm px-4 py-3 shadow-sm">
            <div class="flex gap-1">
              <span class="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style="animation-delay: 0ms" />
              <span class="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style="animation-delay: 150ms" />
              <span class="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style="animation-delay: 300ms" />
            </div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="flex-shrink-0 border-t border-gray-200 bg-white p-4">
        <div class="flex gap-3 items-end">
          <textarea
            ref="inputRef"
            v-model="inputText"
            @keydown.enter.exact.prevent="sendMessage()"
            rows="1"
            placeholder="Describe a maintenance scenario or ask the agent a question…"
            class="flex-1 text-sm border border-gray-200 rounded-xl px-4 py-2.5 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400/40 focus:border-indigo-400 placeholder:text-gray-400 max-h-32"
            :style="{ height: inputHeight }"
            @input="autoResize"
          />
          <button
            @click="sendMessage()"
            :disabled="!inputText.trim() || thinking"
            class="flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-40 flex-shrink-0"
          >
            <Send :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- ── RIGHT: Insights ──────────────────────────────────── -->
    <div class="w-72 flex-shrink-0 border-l border-gray-200 bg-white flex flex-col overflow-hidden">
      <div class="px-4 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center gap-2">
          <Activity :size="16" class="text-emerald-500" />
          <h2 class="text-sm font-semibold text-gray-900">Agent Insights</h2>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <!-- Actions taken -->
        <div v-if="agentActions.length">
          <h3 class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Actions</h3>
          <div class="space-y-2">
            <div v-for="(action, i) in agentActions" :key="i"
              class="flex items-start gap-2 text-xs"
            >
              <component :is="actionIcon(action.type)" :size="12"
                class="mt-0.5 flex-shrink-0"
                :class="actionColor(action.type)" />
              <div>
                <span class="font-medium text-gray-700">{{ action.label }}</span>
                <p class="text-gray-400 mt-0.5">{{ action.detail }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Matched suppliers -->
        <div v-if="matchedSuppliers.length">
          <h3 class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Matched Suppliers</h3>
          <div class="space-y-1.5">
            <div v-for="s in matchedSuppliers" :key="s.id"
              class="flex items-center gap-2 text-xs bg-gray-50 rounded-lg px-3 py-2"
            >
              <div class="w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0">
                <Wrench :size="10" class="text-teal-600" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-medium text-gray-700 truncate">{{ s.name }}</div>
                <div class="text-gray-400">{{ s.trade }} · {{ s.score }}% match</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Flagged questions -->
        <div v-if="flaggedQuestions.length">
          <h3 class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Flagged Questions</h3>
          <div class="space-y-1.5">
            <div v-for="q in flaggedQuestions" :key="q.id"
              class="text-xs bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
            >
              <p class="text-amber-800 line-clamp-2">{{ q.question }}</p>
              <RouterLink
                :to="{ name: 'maintenance-ai-questions' }"
                class="text-amber-600 hover:text-amber-800 font-medium mt-1 inline-block"
              >
                Review →
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!agentActions.length && !matchedSuppliers.length && !flaggedQuestions.length"
          class="text-center text-gray-400 py-10"
        >
          <Activity :size="28" class="mx-auto mb-2 text-gray-300" />
          <p class="text-xs">Agent insights will appear here as the conversation progresses</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import {
  Bot, User, Send, Trash2, AlertCircle, Activity,
  Wrench, Search, CheckCircle2, HelpCircle, Zap,
} from 'lucide-vue-next'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  flagged?: boolean
}

interface AgentAction {
  type: 'triage' | 'match' | 'flag' | 'lookup' | 'dispatch'
  label: string
  detail: string
}

interface MatchedSupplier {
  id: number
  name: string
  trade: string
  score: number
}

interface FlaggedQ {
  id: number
  question: string
}

const messages = ref<Message[]>([])
const inputText = ref('')
const inputHeight = ref('auto')
const thinking = ref(false)
const selectedProperty = ref<number | null>(null)
const contextMode = ref('full')
const messagesContainer = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()
const properties = ref<{ id: number; name: string }[]>([])

const agentActions = ref<AgentAction[]>([])
const matchedSuppliers = ref<MatchedSupplier[]>([])
const flaggedQuestions = ref<FlaggedQ[]>([])

const capabilities = reactive([
  { key: 'triage', label: 'Auto-triage requests', enabled: true },
  { key: 'supplier_match', label: 'Supplier matching', enabled: true },
  { key: 'flag_questions', label: 'Flag unknowns', enabled: true },
  { key: 'dispatch', label: 'Auto-dispatch', enabled: false },
])

const contextModes = [
  { value: 'full', label: 'Full property context' },
  { value: 'minimal', label: 'Minimal context' },
  { value: 'none', label: 'No context (raw)' },
]

const quickPrompts = [
  { label: 'Triage a leak report', text: 'A tenant reports water leaking from the ceiling in unit 3B. The leak started this morning and is getting worse. Please triage this request.' },
  { label: 'Match a supplier', text: 'I need to find the best supplier for an electrical issue at Sandton Heights. The main distribution board is tripping repeatedly.' },
  { label: 'Tenant question', text: 'A tenant asks: "My geyser is making a loud banging noise. Is this an emergency? Should I turn off the water?"' },
  { label: 'Inspection follow-up', text: 'After a routine inspection at unit 12A, the following issues were found: cracked bathroom tiles, rusted gate hinges, and a broken window latch. Create maintenance requests for each.' },
  { label: 'Supplier availability', text: 'Check which plumbing suppliers are available for an urgent job this week at Rosebank Manor.' },
]

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/')
    properties.value = (data.results ?? data).map((p: any) => ({ id: p.id, name: p.name }))
  } catch { /* ignore */ }
})

async function sendMessage(text?: string) {
  const content = text || inputText.value.trim()
  if (!content) return

  messages.value.push({ role: 'user', content, timestamp: new Date() })
  inputText.value = ''
  inputHeight.value = 'auto'
  thinking.value = true
  scrollToBottom()

  try {
    const { data } = await api.post('/maintenance/ai-sandbox/', {
      message: content,
      property_id: selectedProperty.value,
      context_mode: contextMode.value,
      capabilities: capabilities.filter(c => c.enabled).map(c => c.key),
      history: messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content })),
    })

    messages.value.push({
      role: 'assistant',
      content: data.response || data.message || 'No response from agent.',
      timestamp: new Date(),
      flagged: data.flagged_question,
    })

    // Update insights
    if (data.actions) agentActions.value.push(...data.actions)
    if (data.matched_suppliers) matchedSuppliers.value = data.matched_suppliers
    if (data.flagged_questions) flaggedQuestions.value.push(...data.flagged_questions)

  } catch (e: any) {
    // If endpoint doesn't exist yet, simulate response
    const simulated = simulateResponse(content)
    messages.value.push({
      role: 'assistant',
      content: simulated.response,
      timestamp: new Date(),
      flagged: simulated.flagged,
    })
    if (simulated.actions) agentActions.value.push(...simulated.actions)
    if (simulated.suppliers) matchedSuppliers.value = simulated.suppliers
  } finally {
    thinking.value = false
    scrollToBottom()
  }
}

function simulateResponse(input: string) {
  const lower = input.toLowerCase()
  const result: any = { response: '', flagged: false, actions: [], suppliers: [] }

  if (lower.includes('leak') || lower.includes('water') || lower.includes('plumb')) {
    result.response = `**Triage Assessment: URGENT**\n\nThis appears to be a water leak which requires immediate attention to prevent property damage.\n\n**Recommended actions:**\n1. Advise tenant to turn off the main water supply if accessible\n2. Dispatch an emergency plumber\n3. Document with photos for insurance\n\n**Priority:** Urgent\n**Trade needed:** Plumbing\n**Estimated response time:** Within 2 hours`
    result.actions = [
      { type: 'triage', label: 'Auto-triaged as Urgent', detail: 'Water leak detected — property damage risk' },
      { type: 'match', label: 'Searching suppliers', detail: 'Looking for available plumbers in area' },
    ]
    result.suppliers = [
      { id: 1, name: 'QuickFix Plumbing', trade: 'Plumbing', score: 94 },
      { id: 2, name: 'SA Plumb Solutions', trade: 'Plumbing', score: 87 },
      { id: 3, name: 'Metro Maintenance', trade: 'General', score: 72 },
    ]
  } else if (lower.includes('electric') || lower.includes('board') || lower.includes('tripping')) {
    result.response = `**Triage Assessment: HIGH**\n\nRepeated DB board tripping indicates a potential electrical fault that could be hazardous.\n\n**Recommended actions:**\n1. Advise tenant to avoid resetting the board repeatedly\n2. Check if specific circuits are affected\n3. Dispatch a qualified electrician (CoC required)\n\n**Priority:** High\n**Trade needed:** Electrical\n**Safety note:** Ensure supplier has valid CoC certification`
    result.actions = [
      { type: 'triage', label: 'Auto-triaged as High', detail: 'Electrical fault — safety hazard' },
      { type: 'match', label: 'Searching electricians', detail: 'Filtering for CoC-certified suppliers' },
    ]
    result.suppliers = [
      { id: 4, name: 'Spark Electrical', trade: 'Electrical', score: 91 },
      { id: 5, name: 'PowerSafe Solutions', trade: 'Electrical', score: 85 },
    ]
  } else if (lower.includes('geyser') || lower.includes('banging')) {
    result.response = `**Tenant Response:**\n\nThe banging noise from your geyser is likely caused by sediment build-up or a faulty pressure valve. While not an immediate emergency, it should be inspected soon.\n\n**What to do now:**\n- You don't need to turn off the water\n- Turn the geyser temperature down if possible\n- Avoid using excessive hot water until inspected\n\n**I'll schedule a plumber inspection within 48 hours.**`
    result.actions = [
      { type: 'triage', label: 'Triaged as Medium', detail: 'Geyser noise — not emergency but needs inspection' },
    ]
    result.flagged = true
    result.actions.push({
      type: 'flag', label: 'Question flagged', detail: 'Is this property\'s geyser still under warranty?'
    })
  } else if (lower.includes('inspection') || lower.includes('tiles') || lower.includes('cracked')) {
    result.response = `**Creating 3 maintenance requests from inspection:**\n\n1. **Cracked bathroom tiles** — Priority: Low, Trade: General Maintenance\n2. **Rusted gate hinges** — Priority: Low, Trade: General Maintenance  \n3. **Broken window latch** — Priority: Medium, Trade: Carpentry (security concern)\n\nAll requests have been created and linked to Unit 12A. The window latch has been flagged as medium priority due to the security implications.`
    result.actions = [
      { type: 'dispatch', label: 'Created 3 requests', detail: 'From inspection findings at unit 12A' },
      { type: 'triage', label: 'Auto-prioritised', detail: 'Window latch elevated to Medium (security)' },
    ]
  } else {
    result.response = `I understand your request. Let me analyze this.\n\nBased on the information provided, I'd recommend the following approach:\n\n1. **Log the request** in the maintenance system\n2. **Assess priority** based on urgency and impact\n3. **Match suppliers** if a trade is identified\n\nCould you provide more specific details about the issue so I can give a more targeted recommendation?`
    result.actions = [
      { type: 'lookup', label: 'Analyzing request', detail: 'Gathering context from property data' },
    ]
  }

  return result
}

function clearChat() {
  messages.value = []
  agentActions.value = []
  matchedSuppliers.value = []
  flaggedQuestions.value = []
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function autoResize() {
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 128) + 'px'
    }
  })
}

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n(\d+)\. /g, '<br/>$1. ')
    .replace(/\n- /g, '<br/>• ')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}

function actionIcon(type: string) {
  const map: Record<string, any> = {
    triage: Zap, match: Search, flag: HelpCircle, lookup: Search, dispatch: CheckCircle2,
  }
  return map[type] ?? Zap
}

function actionColor(type: string): string {
  const map: Record<string, string> = {
    triage: 'text-amber-500', match: 'text-blue-500', flag: 'text-violet-500',
    lookup: 'text-gray-500', dispatch: 'text-emerald-500',
  }
  return map[type] ?? 'text-gray-500'
}
</script>
