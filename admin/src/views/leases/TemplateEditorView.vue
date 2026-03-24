<template>
  <!-- Full-screen overlay -->
  <div class="fixed inset-0 z-50 bg-white flex flex-col">

    <!-- ── Header (DocuSeal-style) ──────────────────────────────────────── -->
    <div class="flex items-center h-14 px-4 border-b border-gray-200 bg-white flex-shrink-0 gap-4">
      <div class="flex items-center gap-3 min-w-0 w-56 flex-shrink-0">
        <button @click="$emit('close')" class="p-1.5 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0">
          <ChevronLeft :size="18" />
        </button>
        <FileSignature :size="15" class="text-navy flex-shrink-0" />
        <span class="font-semibold text-gray-900 text-sm truncate">{{ template?.name ?? 'Template Editor' }}</span>
      </div>

      <!-- Step indicator -->
      <div class="flex items-center gap-3 mx-auto">
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-full bg-navy flex items-center justify-center text-white text-[11px] font-bold">1</div>
          <span class="text-xs font-semibold text-navy">Add &amp; Prepare Fields</span>
        </div>
        <div class="flex items-center gap-1">
          <div v-for="i in 5" :key="i" class="w-1 h-1 rounded-full" :class="i <= 3 ? 'bg-navy' : 'bg-gray-300'" />
        </div>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-full border-2 border-gray-300 flex items-center justify-center text-gray-400 text-[11px] font-bold">2</div>
          <span class="text-xs text-gray-400">Set Up &amp; Send Invite</span>
        </div>
      </div>

      <!-- Right actions -->
      <div class="flex items-center gap-2 ml-auto">
        <button
          v-if="isDirty"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          @click="saveContent" :disabled="saving"
        >
          <Loader2 v-if="saving" :size="12" class="animate-spin" />
          <Save v-else :size="12" />
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          @click="generatePreview"
        >
          <Download :size="12" /> Export
        </button>
        <button
          class="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors disabled:opacity-60"
          @click="activateTemplate"
          :disabled="template?.is_active"
        >
          <CheckCircle2 :size="12" />
          {{ template?.is_active ? 'Active ✓' : 'Set Active' }}
        </button>
      </div>
    </div>

    <!-- ── Body ─────────────────────────────────────────────────────────── -->
    <div class="flex-1 flex overflow-hidden min-h-0">

      <!-- ── LEFT PANEL: Recipients + Field Palette (~270px) ────────────── -->
      <div class="w-[270px] flex-shrink-0 border-r border-gray-200 flex flex-col bg-white overflow-y-auto">

        <!-- Recipients header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <span class="text-sm font-semibold text-gray-800">Recipients: {{ actors.length }}</span>
          <button
            class="text-xs font-semibold transition-colors"
            :class="showAddActor ? 'text-gray-500' : 'text-navy hover:text-navy/70'"
            @click="showAddActor = !showAddActor"
          >
            {{ showAddActor ? 'Done' : 'Edit' }}
          </button>
        </div>

        <!-- Add actor (shown when Edit clicked or no actors) -->
        <div v-if="showAddActor || actors.length === 0" class="px-3 pt-3 pb-2 border-b border-gray-100 space-y-2">
          <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wide px-1">Add recipient</div>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              v-for="type in actorTypes" :key="type.key"
              class="flex flex-col items-center gap-1 py-2 px-1 border border-dashed rounded-lg text-[11px] font-medium transition-all"
              :class="type.btnClass"
              @click="addActor(type.key)"
            >
              <component :is="type.icon" :size="15" :class="type.iconClass" />
              + {{ type.label }}
            </button>
          </div>
        </div>

        <!-- Instruction label -->
        <div class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100 leading-relaxed">
          Select a recipient to add fields:
        </div>

        <!-- Actor list -->
        <div class="px-2 py-2 space-y-0.5 border-b border-gray-200">
          <!-- Me (property manager) -->
          <button
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
            :class="selectedActorIdx === -1 ? 'bg-navy/10' : 'hover:bg-gray-50'"
            @click="selectedActorIdx = -1"
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 text-white"
              :style="{ background: selectedActorIdx === -1 ? '#1e3a5f' : '#6b7280' }">
              Me
            </div>
            <div class="flex-1 text-left min-w-0">
              <div class="text-xs font-semibold" :class="selectedActorIdx === -1 ? 'text-navy' : 'text-gray-800'">Me (Fill Out Now)</div>
              <div class="text-[10px] text-gray-400">Agent / Property Manager</div>
            </div>
          </button>

          <!-- Dynamic actors -->
          <div
            v-for="(actor, idx) in actors" :key="idx"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors relative group cursor-pointer"
            :class="selectedActorIdx === idx ? 'bg-opacity-10' : 'hover:bg-gray-50'"
            :style="selectedActorIdx === idx ? { backgroundColor: actorColor(actor.type, idx) + '18' } : {}"
            @click="selectedActorIdx = idx"
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 text-white"
              :style="{ backgroundColor: actorColor(actor.type, idx) }">
              {{ actorAvatar(actor, idx) }}
            </div>
            <div class="flex-1 text-left min-w-0">
              <div class="text-xs font-semibold text-gray-800">{{ actor.label }}</div>
              <div class="text-[10px] text-gray-400">{{ actor.fields.length }} fields</div>
            </div>
            <button
              class="opacity-0 group-hover:opacity-100 p-1 rounded text-gray-300 hover:text-red-400 transition-all"
              @click.stop="removeActor(idx)"
              title="Remove"
            >
              <X :size="11" />
            </button>
          </div>
        </div>

        <!-- Field palette instruction -->
        <div class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100 leading-relaxed">
          Add fields for this recipient:
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-gray-100">
          <button
            v-for="tab in ['Favorites', 'All Fields']" :key="tab"
            class="flex-1 py-2 text-xs font-medium border-b-2 transition-colors"
            :class="activeFieldTab === tab ? 'border-navy text-navy' : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeFieldTab = tab"
          >
            {{ tab }}
          </button>
        </div>

        <!-- Field type grid -->
        <div class="p-2 grid grid-cols-2 gap-1.5">
          <button
            v-for="ft in visibleFieldTypes" :key="ft.key"
            class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border text-xs font-medium text-left transition-all"
            :class="selectedActorIdx !== null
              ? 'border-gray-200 text-gray-700 hover:border-navy/30 hover:bg-navy/5 cursor-pointer'
              : 'border-gray-100 text-gray-400 cursor-not-allowed'"
            @click="insertFieldType(ft)"
            :title="selectedActorIdx === null ? 'Select a recipient first' : `Insert ${ft.label}`"
          >
            <component :is="ft.icon" :size="13" class="flex-shrink-0" :class="selectedActorIdx !== null ? 'text-gray-500' : 'text-gray-300'" />
            <span class="truncate">{{ ft.label }}</span>
          </button>
        </div>

        <!-- Personal Data -->
        <div class="border-t border-gray-100 pb-3">
          <div class="px-4 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Personal Data</div>
          <div class="px-2 grid grid-cols-2 gap-1.5">
            <button
              v-for="pd in personalDataFields" :key="pd.key"
              class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-700 hover:border-navy/30 hover:bg-navy/5 transition-all text-left cursor-pointer"
              @click="insertFieldType(pd)"
            >
              <component :is="pd.icon" :size="13" class="text-gray-500 flex-shrink-0" />
              <span class="truncate">{{ pd.label }}</span>
            </button>
          </div>
        </div>

        <!-- Lease Fields (All Fields tab only) -->
        <div v-if="activeFieldTab === 'All Fields'" class="border-t border-gray-100 pb-3">
          <div class="px-4 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Lease Fields</div>
          <div class="px-3 flex flex-wrap gap-1">
            <span
              v-for="f in leaseFields" :key="f"
              class="font-mono text-[9px] bg-gray-50 text-gray-600 border border-gray-200 px-1.5 py-0.5 rounded cursor-pointer hover:bg-amber-50 hover:text-amber-700 hover:border-amber-200 transition-colors"
              @click="insertField(f)"
              :title="`Insert {{ ${f} }}`"
            >{{ f }}</span>
          </div>
        </div>
      </div>

      <!-- ── CENTER: Document canvas ──────────────────────────────────────── -->
      <div class="flex-1 flex flex-col overflow-hidden min-h-0 bg-[#e8eaed]">

        <!-- Mini toolbar -->
        <div class="flex items-center gap-0.5 px-3 py-1.5 border-b border-gray-300 bg-white flex-shrink-0 flex-wrap">
          <button class="toolbar-btn" @click="execCmd('undo')" title="Undo"><RotateCcw :size="13" /></button>
          <button class="toolbar-btn" @click="execCmd('redo')" title="Redo"><RotateCw :size="13" /></button>
          <div class="w-px h-5 bg-gray-200 mx-1" />
          <select
            class="text-xs border border-gray-200 rounded px-2 py-1 mr-1 focus:outline-none bg-white"
            @change="formatBlock(($event.target as HTMLSelectElement).value)"
          >
            <option value="p">Normal</option>
            <option value="h1">Heading 1</option>
            <option value="h2">Heading 2</option>
            <option value="h3">Heading 3</option>
          </select>
          <button class="toolbar-btn" @mousedown.prevent="execCmd('bold')"><Bold :size="13" /></button>
          <button class="toolbar-btn" @mousedown.prevent="execCmd('italic')"><Italic :size="13" /></button>
          <button class="toolbar-btn" @mousedown.prevent="execCmd('underline')"><Underline :size="13" /></button>
          <div class="w-px h-5 bg-gray-200 mx-1" />
          <button class="toolbar-btn" @mousedown.prevent="execCmd('insertUnorderedList')"><List :size="13" /></button>
          <button class="toolbar-btn" @mousedown.prevent="execCmd('insertOrderedList')"><ListOrdered :size="13" /></button>
          <div class="w-px h-5 bg-gray-200 mx-1" />
          <button class="toolbar-btn" @mousedown.prevent="execCmd('justifyLeft')"><AlignLeft :size="13" /></button>
          <button class="toolbar-btn" @mousedown.prevent="execCmd('justifyCenter')"><AlignCenter :size="13" /></button>
          <div class="w-px h-5 bg-gray-200 mx-1" />
          <div class="relative">
            <button
              class="flex items-center gap-1 px-2 py-1 text-xs text-amber-700 border border-amber-200 bg-amber-50 rounded hover:bg-amber-100 transition-colors font-medium"
              @click="showFieldPicker = !showFieldPicker"
            >
              <Braces :size="12" /> Insert field
            </button>
            <div v-if="showFieldPicker" class="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-2 max-h-48 overflow-y-auto">
              <div class="text-[10px] font-semibold text-gray-400 uppercase px-1 mb-1">Click to insert</div>
              <button
                v-for="f in allFields" :key="f"
                class="w-full text-left font-mono text-xs px-2 py-1 hover:bg-amber-50 rounded text-amber-700"
                @mousedown.prevent="insertField(f)"
              >
                &#123;&#123; {{ f }} &#125;&#125;
              </button>
            </div>
          </div>
          <div class="ml-auto flex items-center gap-2">
            <span v-if="isDirty" class="flex items-center gap-1.5 text-[11px] text-amber-600">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400" /> Unsaved
            </span>
            <button
              v-if="isDirty"
              class="px-2.5 py-1 bg-navy text-white text-xs font-medium rounded-lg hover:bg-navy/90 transition-colors"
              @click="saveContent" :disabled="saving"
            >
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>

        <!-- Document page (scrollable) -->
        <div class="flex-1 overflow-y-auto py-8 px-4 min-h-0" @click="showFieldPicker = false">
          <!-- Loading skeleton -->
          <div v-if="loadingPreview" class="max-w-[680px] mx-auto bg-white shadow-lg rounded-sm px-14 py-12 space-y-3 animate-pulse">
            <div class="h-5 bg-gray-200 rounded w-1/3 mx-auto mb-6" />
            <div v-for="i in 8" :key="i" class="h-3 bg-gray-100 rounded" :class="i % 3 === 0 ? 'w-4/5' : i % 2 === 0 ? 'w-full' : 'w-11/12'" />
          </div>

          <!-- A4 document page -->
          <div
            v-else
            ref="editorEl"
            contenteditable="true"
            class="max-w-[680px] mx-auto bg-white shadow-lg rounded-sm px-14 py-12 min-h-[900px] focus:outline-none document-editor leading-relaxed"
            @input="onEditorInput"
            v-html="editorHtml"
          />

          <div class="text-center text-[11px] text-gray-400 mt-3">Page 1 of 1 · Click to edit · Select a recipient then click field types to insert</div>
        </div>
      </div>

      <!-- ── RIGHT PANEL: Document navigator (~180px) ────────────────────── -->
      <div class="w-44 flex-shrink-0 border-l border-gray-200 flex flex-col bg-white overflow-y-auto">
        <div class="px-3 py-3 border-b border-gray-200 flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-700">Documents: 1</span>
          <button class="text-xs text-navy font-medium hover:underline">Edit</button>
        </div>

        <!-- Template card -->
        <div class="p-2.5 border-b border-gray-100">
          <div class="flex items-start justify-between gap-1 mb-2">
            <span class="text-[11px] font-semibold text-gray-700 leading-tight break-words min-w-0">{{ template?.name ?? 'Template' }}</span>
            <div class="flex gap-1 flex-shrink-0">
              <button class="p-1 rounded hover:bg-gray-100 text-gray-400"><FileText :size="11" /></button>
              <button class="p-1 rounded hover:bg-gray-100 text-gray-400"><ChevronUp :size="11" /></button>
            </div>
          </div>

          <!-- Page thumbnail -->
          <div
            class="w-full aspect-[3/4] bg-gray-50 border-2 rounded flex flex-col items-center justify-center cursor-pointer transition-colors overflow-hidden"
            :class="selectedPage === 0 ? 'border-navy' : 'border-gray-200 hover:border-navy/40'"
            @click="selectedPage = 0"
          >
            <div class="w-full h-full p-2 flex flex-col gap-1">
              <div class="h-1.5 bg-gray-300 rounded w-2/3 mx-auto" />
              <div v-for="i in 7" :key="i" class="h-1 bg-gray-200 rounded" :class="i % 3 === 0 ? 'w-3/4' : 'w-full'" />
            </div>
          </div>
          <div class="text-[10px] text-gray-400 mt-1 text-center">1 page · {{ discoveredFields.length }} fields</div>
        </div>

        <!-- Add document -->
        <div class="p-2.5 border-b border-gray-100">
          <button class="w-full border-2 border-dashed border-gray-200 rounded-lg py-4 text-[11px] text-gray-400 hover:border-navy/30 hover:text-navy/60 transition-colors flex flex-col items-center gap-1">
            <span class="text-lg font-light">+</span>
            Add additional documents
          </button>
        </div>

        <!-- Recipients summary -->
        <div class="p-2.5 flex-1">
          <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-2">Recipients</div>
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <div class="w-5 h-5 rounded-full bg-gray-400 flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0">M</div>
              <span class="text-[10px] text-gray-600 truncate">Me</span>
            </div>
            <div
              v-for="(actor, idx) in actors" :key="idx"
              class="flex items-center gap-2"
            >
              <div class="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                :style="{ backgroundColor: actorColor(actor.type, idx) }">
                {{ actorAvatar(actor, idx).charAt(0) }}
              </div>
              <span class="text-[10px] text-gray-600 truncate">{{ actor.label }}</span>
            </div>
            <div v-if="!actors.length" class="text-[10px] text-gray-300 italic">No recipients added</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Floating AI Chat button ───────────────────────────────────────── -->
    <button
      class="fixed bottom-6 right-6 w-12 h-12 bg-navy text-white rounded-full shadow-xl hover:bg-navy/90 flex items-center justify-center transition-all z-40 hover:scale-105"
      :class="chatOpen ? 'ring-4 ring-navy/20' : ''"
      @click="chatOpen = !chatOpen"
      title="AI Assistant"
    >
      <Sparkles :size="18" />
    </button>

    <!-- ── AI Chat panel (floating) ──────────────────────────────────────── -->
    <Transition name="slide-chat">
      <div
        v-if="chatOpen"
        class="fixed right-6 bottom-22 w-80 bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col z-50"
        style="height: 420px; bottom: 5.5rem;"
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 rounded-t-2xl bg-gray-50 flex-shrink-0">
          <div class="flex items-center gap-2">
            <Sparkles :size="13" class="text-pink-brand" />
            <span class="text-xs font-semibold text-gray-700">AI Assistant</span>
            <span v-if="template" class="text-[10px] text-gray-400 truncate max-w-24">— {{ template.name }}</span>
          </div>
          <button class="p-1 rounded hover:bg-gray-200 text-gray-400 transition-colors" @click="chatOpen = false">
            <X :size="13" />
          </button>
        </div>
        <div ref="chatScrollEl" class="flex-1 overflow-y-auto px-3 py-3 space-y-2.5 min-h-0">
          <div
            v-for="(msg, i) in chatMessages" :key="i"
            class="flex gap-2"
            :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
          >
            <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5"
              :class="msg.role === 'assistant' ? 'bg-navy/10 text-navy' : 'bg-gray-200 text-gray-600'">
              {{ msg.role === 'assistant' ? 'AI' : 'Me' }}
            </div>
            <div class="max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap"
              :class="msg.role === 'user' ? 'bg-navy text-white rounded-tr-sm' : 'bg-gray-100 text-gray-800 rounded-tl-sm'">
              {{ msg.content }}
            </div>
          </div>
          <div v-if="chatThinking" class="flex gap-2">
            <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold bg-navy/10 text-navy mt-0.5">AI</div>
            <div class="bg-gray-100 rounded-2xl rounded-tl-sm px-3 py-2.5 flex gap-1">
              <span v-for="j in 3" :key="j" class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" :style="`animation-delay:${(j-1)*0.15}s`" />
            </div>
          </div>
        </div>
        <div class="border-t border-gray-200 p-2.5 flex gap-2 flex-shrink-0 rounded-b-2xl">
          <textarea
            v-model="chatInput"
            rows="2"
            placeholder="Ask about this template…"
            class="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-navy/30"
            @keydown.enter.exact.prevent="sendMessage"
            :disabled="chatThinking"
          />
          <button
            class="btn-primary px-3 self-end"
            :disabled="!chatInput.trim() || chatThinking"
            @click="sendMessage"
          >
            <Send :size="13" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- Field picker backdrop -->
    <div v-if="showFieldPicker" class="fixed inset-0 z-[5]" @click="showFieldPicker = false" />

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="fieldNotice" class="fixed bottom-5 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-4 py-2 rounded-full shadow-lg z-50 whitespace-nowrap">
        {{ fieldNotice }}
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, markRaw } from 'vue'
import {
  X, FileSignature, FileText, Sparkles, Send, Download, Save, CheckCircle2,
  Braces, PenLine, ChevronLeft, ChevronUp, Loader2,
  Bold, Italic, Underline, List, ListOrdered, AlignLeft, AlignCenter,
  RotateCcw, RotateCw,
  Users, User, UserCheck, Building2,
  Hash, Calendar, CheckSquare, Phone, Mail, Type, Pen, StickyNote,
} from 'lucide-vue-next'
import api from '../../api'

const props = defineProps<{ templateId: number }>()
const emit = defineEmits<{ (e: 'close'): void }>()

// ── Template data ─────────────────────────────────────────────────────────
interface TemplateInfo {
  id: number; name: string; version: string; is_active: boolean
  fields_schema: string[]; content_html: string; docx_file: string | null
}
interface PreviewData {
  type: 'docx' | 'pdf'; name: string; fields: string[]
  paragraphs: { style: string; text: string }[]; content_html: string
}

const template = ref<TemplateInfo | null>(null)
const preview  = ref<PreviewData | null>(null)
const loadingPreview = ref(true)

// ── Editor state ──────────────────────────────────────────────────────────
const editorEl  = ref<HTMLDivElement | null>(null)
const editorHtml = ref('')
const savedHtml  = ref('')
const saving     = ref(false)
const isDirty    = ref(false)
const showFieldPicker = ref(false)

// ── UI state ──────────────────────────────────────────────────────────────
const chatOpen       = ref(false)
const showAddActor   = ref(false)
const activeFieldTab = ref('All Fields')
const selectedPage   = ref(0)
const selectedActorIdx = ref<number | null>(null)   // -1 = Me, 0+ = actors[]
const fieldNotice    = ref('')
const actionFeedback = ref('')

// ── Chat state ────────────────────────────────────────────────────────────
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])
const chatInput    = ref('')
const chatThinking = ref(false)
const chatScrollEl = ref<HTMLDivElement | null>(null)

// ── Actor system ──────────────────────────────────────────────────────────
type ActorType = 'landlord' | 'tenant' | 'occupant'

interface Actor {
  type: ActorType
  number: number
  label: string
  fields: string[]
  expanded: boolean
}

const ACTOR_COLORS: Record<string, string[]> = {
  landlord: ['#1e3a5f'],
  tenant:   ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b'],
  occupant: ['#10b981', '#f97316', '#ec4899'],
}

function actorColor(type: ActorType, idx: number): string {
  const palette = ACTOR_COLORS[type]
  const sameType = actors.value.filter(a => a.type === type)
  const pos = sameType.findIndex((_, i) => {
    const globalIdx = actors.value.indexOf(sameType[i])
    return globalIdx === idx
  })
  return palette[Math.max(pos, 0) % palette.length]
}

function actorAvatar(actor: Actor, idx: number): string {
  if (actor.type === 'landlord') return 'L'
  if (actor.type === 'tenant') return `R${actor.number}`
  return `O${actor.number}`
}

const actorTypes = [
  {
    key: 'landlord' as ActorType,
    label: 'Landlord',
    icon: markRaw(Building2),
    iconClass: 'text-navy',
    btnClass: 'border-navy/30 text-navy hover:border-navy hover:bg-navy/5',
  },
  {
    key: 'tenant' as ActorType,
    label: 'Tenant',
    icon: markRaw(User),
    iconClass: 'text-blue-500',
    btnClass: 'border-blue-200 text-blue-600 hover:border-blue-400 hover:bg-blue-50',
  },
  {
    key: 'occupant' as ActorType,
    label: 'Occupant',
    icon: markRaw(UserCheck),
    iconClass: 'text-purple-500',
    btnClass: 'border-purple-200 text-purple-600 hover:border-purple-400 hover:bg-purple-50',
  },
]

const actorTypeMap = {
  landlord: actorTypes[0],
  tenant:   actorTypes[1],
  occupant: actorTypes[2],
}

function actorPrefix(actor: Actor): string {
  if (actor.type === 'landlord') return 'landlord'
  if (actor.type === 'tenant')   return `tenant_${actor.number}`
  return `occupant_${actor.number}`
}

function actorFields(type: ActorType, n: number): string[] {
  if (type === 'landlord') {
    return ['landlord_name', 'landlord_id', 'landlord_phone', 'landlord_email', 'landlord_address', 'landlord_signature']
  }
  if (type === 'tenant') {
    const p = `tenant_${n}`
    return [`${p}_name`, `${p}_id`, `${p}_phone`, `${p}_email`, `${p}_signature`, `${p}_initials`, `${p}_date_signed`]
  }
  const p = `occupant_${n}`
  return [`${p}_name`, `${p}_id`, `${p}_relationship`, `${p}_signature`]
}

const actors = ref<Actor[]>([])

function addActor(type: ActorType) {
  const count = actors.value.filter(a => a.type === type).length + 1
  if (type === 'landlord' && count > 1) { showToast('Only one Landlord can be added'); return }
  const label = type === 'landlord' ? 'Landlord / Owner' : `${actorTypeMap[type].label} ${count}`
  actors.value.push({ type, number: count, label, fields: actorFields(type, count), expanded: true })
  selectedActorIdx.value = actors.value.length - 1
  showAddActor.value = false
}

function removeActor(idx: number) {
  actors.value.splice(idx, 1)
  const byType: Record<string, number> = {}
  actors.value.forEach(a => {
    byType[a.type] = (byType[a.type] ?? 0) + 1
    const n = byType[a.type]
    a.number = n
    a.label  = a.type === 'landlord' ? 'Landlord / Owner' : `${actorTypeMap[a.type].label} ${n}`
    a.fields = actorFields(a.type, n)
  })
  if (selectedActorIdx.value !== null && selectedActorIdx.value >= actors.value.length) {
    selectedActorIdx.value = actors.value.length - 1
  }
}

// ── Field type palette ────────────────────────────────────────────────────
const allFieldTypes = [
  { key: 'signature', label: 'Signature',    icon: markRaw(Pen),         favorite: true },
  { key: 'initials',  label: 'Initials',      icon: markRaw(Type),        favorite: true },
  { key: 'text',      label: 'Text',          icon: markRaw(StickyNote),  favorite: true },
  { key: 'number',    label: 'Number',        icon: markRaw(Hash),        favorite: false },
  { key: 'date',      label: 'Date',          icon: markRaw(Calendar),    favorite: true },
  { key: 'checkbox',  label: 'Checkbox',      icon: markRaw(CheckSquare), favorite: false },
]

const personalDataFields = [
  { key: 'name',   label: 'Full Name',    icon: markRaw(User) },
  { key: 'phone',  label: 'Phone Number', icon: markRaw(Phone) },
  { key: 'email',  label: 'Email',        icon: markRaw(Mail) },
]

const visibleFieldTypes = computed(() =>
  activeFieldTab.value === 'Favorites'
    ? allFieldTypes.filter(f => f.favorite)
    : allFieldTypes
)

function insertFieldType(ft: { key: string }) {
  let fieldName: string

  if (selectedActorIdx.value === -1) {
    // "Me" = property manager
    const keyMap: Record<string, string> = {
      signature: 'agent_signature', initials: 'agent_initials', text: 'agent_text',
      number: 'agent_number', date: 'agent_date', checkbox: 'agent_checkbox',
      name: 'agent_name', phone: 'agent_phone', email: 'agent_email',
    }
    fieldName = keyMap[ft.key] ?? `agent_${ft.key}`

  } else if (selectedActorIdx.value !== null && selectedActorIdx.value < actors.value.length) {
    const actor = actors.value[selectedActorIdx.value]
    const pfx = actorPrefix(actor)
    const keyMap: Record<string, string> = {
      signature: `${pfx}_signature`, initials: `${pfx}_initials`, text: `${pfx}_text`,
      number: `${pfx}_number`, date: `${pfx}_date_signed`, checkbox: `${pfx}_checkbox`,
      name: `${pfx}_name`, phone: `${pfx}_phone`, email: `${pfx}_email`,
    }
    fieldName = keyMap[ft.key] ?? `${pfx}_${ft.key}`

  } else {
    showToast('Select a recipient first')
    return
  }

  insertField(fieldName)
}

// ── Static lease fields ───────────────────────────────────────────────────
const leaseFields = [
  'property_address', 'unit_number', 'city', 'province',
  'lease_start', 'lease_end', 'monthly_rent', 'deposit',
  'escalation_percent', 'notice_period_days', 'max_occupants',
  'pets_allowed', 'water_included', 'electricity_prepaid', 'payment_reference',
]

// ── Computed ──────────────────────────────────────────────────────────────
const discoveredFields = computed<string[]>(() => {
  const s = template.value?.fields_schema ?? []
  const p = preview.value?.fields ?? []
  return [...new Set([...s, ...p])].sort()
})

const allActorFields = computed<string[]>(() => actors.value.flatMap(a => a.fields))

const allFields = computed<string[]>(() =>
  [...new Set([...allActorFields.value, ...leaseFields, ...discoveredFields.value])].sort()
)

// ── Lifecycle ─────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadTemplate(), loadPreview()])
  chatMessages.value = [{
    role: 'assistant',
    content: template.value
      ? `Hi! I can help you work on "${template.value.name}". I can explain clauses, suggest additions, generate new clause text, or advise on signing fields. What would you like to do?`
      : 'Hi! I can help you improve this lease template. What would you like to work on?',
  }]
})

async function loadTemplate() {
  try {
    const { data } = await api.get(`/leases/templates/${props.templateId}/`)
    template.value = data
  } catch { /* ignore */ }
}

async function loadPreview() {
  loadingPreview.value = true
  try {
    const { data } = await api.get(`/leases/templates/${props.templateId}/preview/`)
    preview.value = data
    if (data.content_html) {
      editorHtml.value = data.content_html
      savedHtml.value  = data.content_html
    } else if (data.paragraphs?.length) {
      editorHtml.value = buildHtmlFromParagraphs(data.paragraphs)
      savedHtml.value  = ''
    }
  } catch { /* ignore */ }
  finally { loadingPreview.value = false }
}

// ── Editor ────────────────────────────────────────────────────────────────
function onEditorInput() {
  isDirty.value = (editorEl.value?.innerHTML ?? '') !== savedHtml.value
}

async function saveContent() {
  if (!editorEl.value) return
  saving.value = true
  const html = editorEl.value.innerHTML
  try {
    await api.patch(`/leases/templates/${props.templateId}/`, { content_html: html })
    savedHtml.value = html
    isDirty.value   = false
    if (template.value) template.value.content_html = html
    showToast('Saved')
  } catch {
    showToast('Save failed')
  } finally {
    saving.value = false
  }
}

function execCmd(cmd: string, value?: string) {
  editorEl.value?.focus()
  document.execCommand(cmd, false, value)
  onEditorInput()
}

function formatBlock(tag: string) {
  execCmd('formatBlock', tag)
}

function insertField(fieldName: string) {
  showFieldPicker.value = false
  editorEl.value?.focus()
  const color = selectedActorIdx.value !== null && selectedActorIdx.value >= 0 && selectedActorIdx.value < actors.value.length
    ? actorColor(actors.value[selectedActorIdx.value].type, selectedActorIdx.value)
    : '#b45309'
  const html = `<span class="tmpl-field" contenteditable="false" data-field="${fieldName}" style="display:inline-flex;align-items:center;font-family:monospace;font-size:11px;background:${color}18;color:${color};border:1px solid ${color}44;padding:1px 7px;border-radius:4px;margin:0 2px;cursor:default;">{&thinsp;{&thinsp;${fieldName}&thinsp;}&thinsp;}</span>&nbsp;`
  document.execCommand('insertHTML', false, html)
  onEditorInput()
}

// ── HTML builder ──────────────────────────────────────────────────────────
function buildHtmlFromParagraphs(paras: { style: string; text: string }[]): string {
  return paras.map(p => {
    const s    = (p.style || '').toLowerCase()
    const text = p.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    const highlighted = text.replace(/\{\{\s*(.+?)\s*\}\}/g, (_, field) =>
      `<span class="tmpl-field" contenteditable="false" data-field="${field}" style="display:inline-flex;align-items:center;font-family:monospace;font-size:11px;background:#fffbeb;color:#b45309;border:1px solid #fcd34d;padding:1px 6px;border-radius:4px;margin:0 2px;cursor:default;">{{ ${field} }}</span>`
    )
    if (s.includes('heading 1') || s.includes('title')) return `<h1>${highlighted}</h1>`
    if (s.includes('heading 2')) return `<h2>${highlighted}</h2>`
    if (s.includes('heading 3')) return `<h3>${highlighted}</h3>`
    return `<p>${highlighted}</p>`
  }).join('\n')
}

function copyField(fieldName: string) {
  navigator.clipboard?.writeText(`{{ ${fieldName} }}`).catch(() => {})
  showToast(`Copied {{ ${fieldName} }}`)
}

// ── Chat ──────────────────────────────────────────────────────────────────
async function sendMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatThinking.value) return

  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatThinking.value = true
  scrollChat()

  const history = chatMessages.value.slice(0, -1)
  const firstUser = history.findIndex(h => h.role === 'user')
  const historyForApi = firstUser >= 0 ? history.slice(firstUser) : []

  try {
    const { data } = await api.post(`/leases/templates/${props.templateId}/ai-chat/`, {
      messages: historyForApi,
      message: msg,
    })
    chatMessages.value.push({ role: 'assistant', content: data.reply })
  } catch {
    chatMessages.value.push({ role: 'assistant', content: 'Sorry, something went wrong. Please try again.' })
  } finally {
    chatThinking.value = false
    scrollChat()
  }
}

function scrollChat() {
  nextTick(() => {
    if (chatScrollEl.value) chatScrollEl.value.scrollTop = chatScrollEl.value.scrollHeight
  })
}

// ── Actions ───────────────────────────────────────────────────────────────
function generatePreview() {
  if (!template.value) return
  api.post('/leases/generate/', { template_id: props.templateId, context: {} }, { responseType: 'blob' })
    .then(({ data }) => {
      const url = URL.createObjectURL(new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 5000)
    })
    .catch(() => showToast('Export failed — DOCX templates only'))
}

async function activateTemplate() {
  if (!template.value || template.value.is_active) return
  try {
    await api.patch(`/leases/templates/${props.templateId}/`, { is_active: true })
    if (template.value) template.value.is_active = true
    showToast('Template set as active')
  } catch {
    showToast('Failed to activate')
  }
}

function showToast(msg: string) {
  fieldNotice.value = msg
  setTimeout(() => { fieldNotice.value = '' }, 2500)
}
</script>

<style scoped>
/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s, transform 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translate(-50%, 8px); }

.slide-chat-enter-active, .slide-chat-leave-active { transition: opacity 0.2s, transform 0.2s; }
.slide-chat-enter-from, .slide-chat-leave-to { opacity: 0; transform: translateY(12px) scale(0.97); }

/* Toolbar button */
.toolbar-btn {
  @apply p-1.5 rounded hover:bg-gray-100 text-gray-600 hover:text-gray-900 transition-colors;
}

/* Document typography */
.document-editor :deep(h1) { font-size: 1.15rem; font-weight: 700; margin: 1.25rem 0 0.4rem; }
.document-editor :deep(h2) { font-size: 1rem;    font-weight: 600; margin: 1rem 0 0.3rem; }
.document-editor :deep(h3) { font-size: 0.9rem;  font-weight: 500; margin: 0.75rem 0 0.25rem; }
.document-editor :deep(p)  { font-size: 0.875rem; margin: 0.3rem 0; }
.document-editor :deep(ul) { list-style-type: disc;    padding-left: 1.5rem; font-size: 0.875rem; }
.document-editor :deep(ol) { list-style-type: decimal; padding-left: 1.5rem; font-size: 0.875rem; }
.document-editor :deep(table) { border-collapse: collapse; width: 100%; margin: 0.5rem 0; font-size: 0.875rem; }
.document-editor :deep(td), .document-editor :deep(th) { border: 1px solid #e5e7eb; padding: 0.375rem 0.5rem; }
.document-editor :deep(th) { background: #f9fafb; font-weight: 600; }
</style>
