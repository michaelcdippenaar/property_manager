<template>
  <div class="flex flex-col h-[calc(100vh-4rem)] -m-6 bg-white overflow-hidden">

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <div class="flex items-center h-14 px-4 border-b border-gray-200 bg-white flex-shrink-0 gap-4">
      <div class="flex items-center gap-3 min-w-0 flex-shrink-0">
        <button @click="router.back()" class="p-1.5 rounded hover:bg-gray-100 text-gray-500">
          <ChevronLeft :size="18" />
        </button>
        <FileSignature :size="15" class="text-navy flex-shrink-0" />
        <span class="font-semibold text-gray-900 text-sm truncate">{{ store.template?.name ?? 'Template Editor' }}</span>
      </div>

      <div class="flex items-center gap-2 ml-auto">
        <span v-if="pageCount > 1" class="text-xs text-gray-400">{{ pageCount }} pages</span>
        <span class="text-xs text-gray-300">|</span>
        <span v-if="wordCount" class="text-xs text-gray-400">{{ wordCount }} words</span>
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
          :class="isDirty
            ? 'bg-navy text-white hover:bg-navy/90 border border-navy'
            : 'text-gray-400 border border-gray-200 cursor-default'"
          @click="save" :disabled="saving || !isDirty"
        >
          <Loader2 v-if="saving" :size="12" class="animate-spin" />
          <Save v-else :size="12" />
          {{ saving ? 'Saving...' : isDirty ? 'Save' : 'Saved' }}
        </button>
        <button
          class="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-navy text-white rounded-lg hover:bg-navy/90"
          @click="router.push({ path: '/leases/build', query: { template: templateId } })"
        >
          Build Lease
        </button>
      </div>
    </div>

    <!-- ── Toolbar ─────────────────────────────────────────────────────────── -->
    <div v-if="editor" class="flex items-center gap-0.5 px-4 py-1.5 border-b border-gray-100 bg-gray-50/50 flex-shrink-0 overflow-x-auto">
      <!-- Undo / Redo -->
      <ToolBtn :active="false" :disabled="!editor.can().undo()" @click="editor!.chain().focus().undo().run()" title="Undo">
        <RotateCcw :size="14" />
      </ToolBtn>
      <ToolBtn :active="false" :disabled="!editor.can().redo()" @click="editor!.chain().focus().redo().run()" title="Redo">
        <RotateCw :size="14" />
      </ToolBtn>
      <ToolSep />

      <!-- Text formatting -->
      <ToolBtn :active="editor.isActive('bold')" @click="editor!.chain().focus().toggleBold().run()" title="Bold">
        <Bold :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive('italic')" @click="editor!.chain().focus().toggleItalic().run()" title="Italic">
        <Italic :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive('underline')" @click="editor!.chain().focus().toggleUnderline().run()" title="Underline">
        <UnderlineIcon :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive('strike')" @click="editor!.chain().focus().toggleStrike().run()" title="Strikethrough">
        <Strikethrough :size="14" />
      </ToolBtn>
      <ToolSep />

      <!-- Headings -->
      <select
        class="text-xs border border-gray-200 rounded px-1.5 py-1 bg-white h-7"
        :value="currentHeading"
        @change="setHeading(($event.target as HTMLSelectElement).value)"
      >
        <option value="p">Paragraph</option>
        <option value="1">Heading 1</option>
        <option value="2">Heading 2</option>
        <option value="3">Heading 3</option>
      </select>

      <!-- Font size -->
      <select
        class="text-xs border border-gray-200 rounded px-1.5 py-1 bg-white h-7 w-16"
        :value="currentFontSize"
        @change="setFontSize(($event.target as HTMLSelectElement).value)"
      >
        <option value="">Default</option>
        <option v-for="s in fontSizes" :key="s" :value="`${s}pt`">{{ s }}pt</option>
      </select>
      <ToolSep />

      <!-- Alignment -->
      <ToolBtn :active="editor.isActive({ textAlign: 'left' })" @click="editor!.chain().focus().setTextAlign('left').run()" title="Align left">
        <AlignLeft :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive({ textAlign: 'center' })" @click="editor!.chain().focus().setTextAlign('center').run()" title="Center">
        <AlignCenter :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive({ textAlign: 'right' })" @click="editor!.chain().focus().setTextAlign('right').run()" title="Align right">
        <AlignRight :size="14" />
      </ToolBtn>
      <ToolSep />

      <!-- Lists -->
      <ToolBtn :active="editor.isActive('bulletList')" @click="editor!.chain().focus().toggleBulletList().run()" title="Bullet list">
        <List :size="14" />
      </ToolBtn>
      <ToolBtn :active="editor.isActive('orderedList')" @click="editor!.chain().focus().toggleOrderedList().run()" title="Numbered list">
        <ListOrdered :size="14" />
      </ToolBtn>
      <ToolSep />

      <!-- Table -->
      <ToolBtn :active="false" @click="insertTable" title="Insert table">
        <TableIcon :size="14" />
      </ToolBtn>

      <!-- Page break -->
      <ToolBtn :active="false" @click="editor!.chain().focus().insertPageBreak().run()" title="Page break">
        <SeparatorHorizontal :size="14" />
      </ToolBtn>
    </div>

    <!-- ── Body ────────────────────────────────────────────────────────────── -->
    <div class="flex-1 flex overflow-hidden min-h-0">

      <!-- ── LEFT PANEL: AI Chat (collapsible) ───────────────────────────── -->
      <div
        class="flex-shrink-0 border-r border-gray-200 flex flex-col bg-white transition-all duration-200"
        :style="{ width: chatCollapsed ? '44px' : '260px' }"
      >
        <!-- Chat header -->
        <div class="flex items-center gap-2 px-3 py-3 border-b border-gray-200 flex-shrink-0">
          <button class="p-1 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0" @click="chatCollapsed = !chatCollapsed" :title="chatCollapsed ? 'Open AI chat' : 'Collapse'">
            <Sparkles :size="14" class="text-pink-500" />
          </button>
          <template v-if="!chatCollapsed">
            <span class="text-sm font-semibold text-gray-800 whitespace-nowrap">AI Assistant</span>
            <span v-if="store.template" class="text-xs text-gray-400 truncate">{{ store.template.name }}</span>
          </template>
        </div>

        <template v-if="!chatCollapsed">
          <!-- Capabilities disclosure -->
          <div class="px-3 py-2 border-b border-gray-100">
            <button @click="showCapabilities = !showCapabilities"
              class="flex items-center gap-1 text-gray-400 hover:text-gray-600 w-full" style="font-size: 10px;">
              <ChevronRight :size="10" class="transition-transform flex-shrink-0" :class="showCapabilities ? 'rotate-90' : ''" />
              <span>{{ showCapabilities ? 'Hide' : 'Show' }} capabilities</span>
            </button>
            <div v-if="showCapabilities" class="mt-1.5 space-y-1.5">
              <div>
                <div class="text-gray-400 mb-0.5" style="font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Editing Tools</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="tool in editingTools" :key="tool"
                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-warning-50 border border-warning-100 text-warning-700"
                    style="font-size: 9px;">
                    <Wrench :size="8" /> {{ tool }}
                  </span>
                </div>
              </div>
              <div>
                <div class="text-gray-400 mb-0.5" style="font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Skills</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="skill in skillTools" :key="skill"
                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-purple-50 border border-purple-200 text-purple-700"
                    style="font-size: 9px;">
                    <Zap :size="8" /> {{ skill }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Messages -->
          <div ref="chatScrollEl" class="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
            <div
              v-for="(msg, i) in chatMessages" :key="i"
              class="flex gap-2"
              :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
            >
              <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center font-bold mt-0.5"
                style="font-size: 9px;"
                :class="msg.role === 'assistant' ? 'bg-navy/10 text-navy' : 'bg-gray-200 text-gray-600'">
                {{ msg.role === 'assistant' ? 'AI' : 'Me' }}
              </div>
              <div class="max-w-[85%]">
                <div class="rounded-2xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap"
                  :class="msg.role === 'user' ? 'bg-navy text-white rounded-tr-sm' : 'bg-gray-100 text-gray-800 rounded-tl-sm'">
                  {{ msg.content }}
                </div>
                <!-- Tools used -->
                <div v-if="msg.tools_used?.length" class="flex flex-wrap gap-1 mt-1 ml-0.5">
                  <span v-for="(tool, ti) in msg.tools_used" :key="ti"
                    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md"
                    :class="skillTools.includes(tool.name) ? 'bg-purple-50 border border-purple-200 text-purple-700' : 'bg-warning-50 border border-warning-100 text-warning-700'"
                    style="font-size: 9px; line-height: 1.2;">
                    <component :is="skillTools.includes(tool.name) ? Zap : Wrench" :size="8" class="flex-shrink-0" />
                    <span class="font-medium">{{ tool.name }}</span>
                    <span :class="skillTools.includes(tool.name) ? 'text-purple-500' : 'text-warning-500'">{{ tool.detail }}</span>
                  </span>
                </div>
              </div>
            </div>
            <!-- Thinking indicator -->
            <div v-if="chatThinking" class="flex gap-2">
              <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center font-bold bg-navy/10 text-navy mt-0.5" style="font-size: 9px;">AI</div>
              <div class="bg-gray-100 rounded-2xl rounded-tl-sm px-3 py-2.5 flex gap-1">
                <span v-for="j in 3" :key="j" class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" :style="`animation-delay:${(j-1)*0.15}s`" />
              </div>
            </div>
          </div>

          <!-- Input -->
          <div class="border-t border-gray-200 p-2.5 flex gap-2 flex-shrink-0">
            <textarea
              v-model="chatInput"
              rows="2"
              placeholder="Ask about this template..."
              class="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-navy/30"
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="chatThinking"
            />
            <button
              class="px-3 py-2 bg-navy text-white rounded-xl self-end hover:bg-navy/90 disabled:opacity-50 transition-colors"
              :disabled="!chatInput.trim() || chatThinking"
              @click="sendMessage"
            >
              <Send :size="13" />
            </button>
          </div>
        </template>
      </div>

      <!-- ── Editor ──────────────────────────────────────────────────────── -->
      <div class="flex-1 overflow-y-auto overflow-x-hidden min-w-0 py-6 pl-6 pr-4" style="background:#f1f3f4;">
        <div class="tiptap-page-container ml-auto mr-4 relative">
          <editor-content
            :editor="editor"
            class="tiptap-editor bg-white"
            style="box-shadow: 0 0 0 1px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);"
          />
        </div>
      </div>

      <!-- ── Right panel: Field palette ──────────────────────────────────── -->
      <div
        class="flex-shrink-0 border-l border-gray-200 bg-white overflow-y-auto transition-all duration-200"
        :style="{ width: panelCollapsed ? '44px' : '270px' }"
      >
        <!-- Panel header -->
        <div class="flex items-center gap-2 px-3 py-3 border-b border-gray-200">
          <button class="p-1 rounded hover:bg-gray-100 text-gray-500" @click="panelCollapsed = !panelCollapsed">
            <Columns3 :size="14" />
          </button>
          <span v-if="!panelCollapsed" class="text-sm font-semibold text-gray-800">Fields</span>
        </div>

        <template v-if="!panelCollapsed">
          <!-- Actor selector -->
          <div class="px-3 py-3 border-b border-gray-100">
            <div class="text-xs uppercase tracking-wider text-gray-400 mb-2">Recipient</div>
            <div class="flex flex-wrap gap-1.5">
              <div
                v-for="(actor, idx) in actors" :key="idx"
                class="flex items-center rounded-full text-xs font-medium transition-colors"
                :class="selectedActorIdx === idx
                  ? 'bg-navy text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
              >
                <button
                  @click="selectedActorIdx = idx"
                  class="px-2.5 py-1"
                >{{ actor.label }}</button>
                <button
                  v-if="actor.removable"
                  @click.stop="removeActor(idx)"
                  class="pr-1.5 pl-0.5 opacity-60 hover:opacity-100"
                  title="Remove"
                >&times;</button>
              </div>
              <!-- Add Tenant (up to 3) -->
              <button
                v-if="actors.filter(a => a.prefix.startsWith('tenant_')).length < 3"
                @click="addTenant"
                class="px-2.5 py-1 rounded-full text-xs font-medium bg-success-50 text-success-700 border border-success-200 hover:bg-success-100 transition-colors"
                title="Add tenant"
              >+ Tenant</button>
              <!-- Add Occupant (up to 4) -->
              <button
                v-if="actors.filter(a => a.prefix.startsWith('occupant_')).length < 4"
                @click="addOccupant"
                class="px-2.5 py-1 rounded-full text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100 transition-colors"
                title="Add occupant"
              >+ Occupant</button>
            </div>
          </div>

          <!-- Data fields -->
          <div class="px-3 py-3 border-b border-gray-100">
            <div class="text-xs uppercase tracking-wider text-gray-400 mb-2">Data Fields</div>
            <div class="space-y-1">
              <div
                v-for="f in dataFields" :key="f.key"
                draggable="true"
                @dragstart="onDragStartMergeField($event, f.key)"
                @click="insertMergeField(f.key)"
                class="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs font-medium cursor-grab active:cursor-grabbing transition-all text-left border"
                :class="actorFieldClasses"
              >
                <GripVertical :size="11" class="flex-shrink-0 opacity-30" />
                <component :is="f.icon" :size="13" class="flex-shrink-0" :class="actorIconClass" />
                {{ f.label }}
              </div>
            </div>
          </div>

          <!-- Signing fields -->
          <div class="px-3 py-3">
            <div class="text-xs uppercase tracking-wider text-gray-400 mb-2">Signing Fields</div>
            <div class="space-y-1">
              <div
                v-for="f in signingFields" :key="f.type"
                draggable="true"
                @dragstart="onDragStartSigningField($event, f.type)"
                @click="insertSigningField(f.type as any)"
                class="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs font-medium cursor-grab active:cursor-grabbing transition-all text-left border"
                :class="actorFieldClasses"
              >
                <GripVertical :size="11" class="flex-shrink-0 opacity-30" />
                <component :is="f.icon" :size="13" class="flex-shrink-0" :class="actorIconClass" />
                {{ f.label }}
              </div>
            </div>
          </div>

          <!-- Lease fields (quick-insert) -->
          <div class="px-3 py-3 border-t border-gray-100">
            <div class="text-xs uppercase tracking-wider text-gray-400 mb-2">Lease Terms</div>
            <div class="flex flex-wrap gap-1.5">
              <div
                v-for="f in leaseFields" :key="f"
                draggable="true"
                @dragstart="onDragStartLeaseField($event, f)"
                @click="insertMergeFieldDirect(f)"
                class="px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-grab active:cursor-grabbing bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 hover:shadow-sm transition-all"
              >
                {{ f.replace(/_/g, ' ') }}
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="toast">
      <div v-if="toastMsg" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50
        bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-xs font-medium">
        {{ toastMsg }}
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, markRaw, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorContent } from '@tiptap/vue-3'
import { useTemplateStore } from '../../stores/template'
import { useTiptapEditor } from '../../composables/useTiptapEditor'
import {
  ChevronLeft, ChevronRight, FileSignature, Save, Loader2, RotateCcw, RotateCw,
  Bold, Italic, Underline as UnderlineIcon, Strikethrough, AlignLeft, AlignCenter, AlignRight,
  List, ListOrdered, Table as TableIcon, SeparatorHorizontal,
  Columns3, User, Home, Hash, Phone, Mail, Calendar, PenTool, Type, MapPin,
  Sparkles, Send, Wrench, Zap, GripVertical, Building2, FileText, Landmark,
} from 'lucide-vue-next'
import api from '../../api'

// ── Setup ─────────────────────────────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const store = useTemplateStore()
const templateId = computed(() => Number(route.params.id))

const saving = ref(false)
const pageCount = ref(1)
const panelCollapsed = ref(false)
const selectedActorIdx = ref(0)
const toastMsg = ref('')
let toastTimer: ReturnType<typeof setTimeout> | null = null

// ── TipTap Editor ─────────────────────────────────────────────────────────
const { editor, isDirty, wordCount, markClean, setContent, getHTML, getJSON } = useTiptapEditor({
  placeholder: 'Start editing your lease template...',
  onUpdate: () => {
    // Auto-save could go here (debounced)
  },
})

// ── Load template ─────────────────────────────────────────────────────────
onMounted(async () => {
  await store.loadTemplate(templateId.value)
  if (store.document.v === 2 && store.document.tiptapJson) {
    // v2: load from structured TipTap JSON (preserves exact document state)
    editor.value?.commands.setContent(store.document.tiptapJson)
  } else if (store.document.html) {
    // v1 or legacy: parse HTML through TipTap's parseHTML rules
    const html = convertLegacyHtml(store.document.html, store.document.fields)
    setContent(html)
  }
  // Poll page count from pagination-plus DOM (it renders .rm-page-break elements)
  nextTick(() => {
    const updatePageCount = () => {
      const paginationEl = document.querySelector('[data-rm-pagination]')
      if (paginationEl) {
        pageCount.value = Math.max(1, paginationEl.children.length)
      }
    }
    const observer = new MutationObserver(updatePageCount)
    const tiptapEl = document.querySelector('.tiptap-editor .tiptap')
    if (tiptapEl) {
      observer.observe(tiptapEl, { childList: true, subtree: true })
      updatePageCount()
    }
  })
})

onBeforeUnmount(() => {
  store.$reset()
})

// ── Save ──────────────────────────────────────────────────────────────────
async function save() {
  if (!editor.value) return
  saving.value = true
  try {
    const html = getHTML()
    const json = getJSON()

    // Store as v2 JSON envelope for the backend
    const payload = JSON.stringify({ v: 2, html, tiptapJson: json, fields: extractFieldsFromJson(json) })
    store.document = { v: 1, html, fields: extractFieldsFromJson(json) }
    store.template!.content_html = payload

    const { data } = await (await import('../../api')).default.patch(
      `/leases/templates/${templateId.value}/`,
      { content_html: payload, header_html: store.headerHtml, footer_html: store.footerHtml },
    )

    markClean()
    showToast('Saved')
  } catch (e) {
    console.error('[TipTap] Save failed:', e)
    showToast('Save failed')
  } finally {
    saving.value = false
  }
}

// Ctrl+S shortcut
function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault()
    save()
  }
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

// ── Toolbar helpers ───────────────────────────────────────────────────────
const fontSizes = [8, 9, 10, 10.5, 11, 12, 14, 16, 18, 20, 24, 28]

const currentHeading = computed(() => {
  if (!editor.value) return 'p'
  for (const level of [1, 2, 3] as const) {
    if (editor.value.isActive('heading', { level })) return String(level)
  }
  return 'p'
})

const currentFontSize = computed(() => {
  if (!editor.value) return ''
  const attrs = editor.value.getAttributes('textStyle')
  return attrs.fontSize || ''
})

function setHeading(val: string) {
  if (!editor.value) return
  if (val === 'p') {
    editor.value.chain().focus().setParagraph().run()
  } else {
    editor.value.chain().focus().toggleHeading({ level: Number(val) as 1 | 2 | 3 }).run()
  }
}

function setFontSize(val: string) {
  if (!editor.value) return
  if (!val) {
    editor.value.chain().focus().unsetFontSize().run()
  } else {
    editor.value.chain().focus().setFontSize(val).run()
  }
}

function insertTable() {
  editor.value?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
}

// ── Field insertion ───────────────────────────────────────────────────────
type ActorEntry = { label: string; prefix: string; removable?: boolean }

const actors = ref<ActorEntry[]>([
  { label: 'Landlord',  prefix: 'landlord' },
  { label: 'Tenant 1',  prefix: 'tenant_1',  removable: true },
  { label: 'Agent',     prefix: 'agent' },
])

function addTenant() {
  const count = actors.value.filter(a => a.prefix.startsWith('tenant_')).length + 1
  if (count > 3) return
  actors.value.push({ label: `Tenant ${count}`, prefix: `tenant_${count}`, removable: true })
  selectedActorIdx.value = actors.value.length - 1
}

function addOccupant() {
  const count = actors.value.filter(a => a.prefix.startsWith('occupant_')).length + 1
  if (count > 4) return
  actors.value.push({ label: `Occupant ${count}`, prefix: `occupant_${count}`, removable: true })
  selectedActorIdx.value = actors.value.length - 1
}

function removeActor(idx: number) {
  if (!actors.value[idx]?.removable) return
  actors.value.splice(idx, 1)
  // Re-number tenants and occupants
  let tc = 0, oc = 0
  actors.value.forEach(a => {
    if (a.prefix.startsWith('tenant_')) { tc++; a.prefix = `tenant_${tc}`; a.label = `Tenant ${tc}` }
    if (a.prefix.startsWith('occupant_')) { oc++; a.prefix = `occupant_${oc}`; a.label = `Occupant ${oc}` }
  })
  if (selectedActorIdx.value >= actors.value.length) selectedActorIdx.value = actors.value.length - 1
}

const _defaultDataFields = [
  { key: 'name', label: 'Full Name', icon: markRaw(User) },
  { key: 'id', label: 'ID Number', icon: markRaw(Hash) },
  { key: 'phone', label: 'Phone', icon: markRaw(Phone) },
  { key: 'email', label: 'Email', icon: markRaw(Mail) },
]

const _landlordDataFields = [
  { key: 'name',               label: 'Entity Name',       icon: markRaw(Building2) },
  { key: 'registration_no',    label: 'Registration No',   icon: markRaw(Hash) },
  { key: 'vat_no',             label: 'VAT No',            icon: markRaw(Hash) },
  { key: 'representative',     label: 'Representative',    icon: markRaw(User) },
  { key: 'representative_id',  label: 'Rep. ID Number',    icon: markRaw(Hash) },
  { key: 'title',              label: 'Title',             icon: markRaw(FileText) },
  { key: 'contact',            label: 'Contact No',        icon: markRaw(Phone) },
  { key: 'email',              label: 'Email',             icon: markRaw(Mail) },
  { key: 'physical_address',   label: 'Physical Address',  icon: markRaw(Building2) },
  { key: 'bank_name',          label: 'Bank Name',         icon: markRaw(Landmark) },
  { key: 'bank_branch_code',   label: 'Branch Code',       icon: markRaw(Hash) },
  { key: 'bank_account_no',    label: 'Account No',        icon: markRaw(Hash) },
  { key: 'bank_account_holder',label: 'Account Holder',    icon: markRaw(User) },
  { key: 'bank_account_type',  label: 'Account Type',      icon: markRaw(FileText) },
]

const _occupantDataFields = [
  { key: 'name',         label: 'Full Name',    icon: markRaw(User) },
  { key: 'id',           label: 'ID Number',    icon: markRaw(Hash) },
  { key: 'relationship', label: 'Relationship', icon: markRaw(User) },
]

const dataFields = computed(() => {
  const prefix = actors.value[selectedActorIdx.value]?.prefix ?? ''
  if (prefix === 'landlord') return _landlordDataFields
  if (prefix.startsWith('occupant_')) return _occupantDataFields
  return _defaultDataFields
})

const signingFields = [
  { type: 'signature', label: 'Signature', icon: markRaw(PenTool) },
  { type: 'initials', label: 'Initials', icon: markRaw(Type) },
  { type: 'date', label: 'Date Signed', icon: markRaw(Calendar) },
  { type: 'signed_at', label: 'Signed At', icon: markRaw(MapPin) },
]

const leaseFields = [
  'property_address', 'property_description', 'unit_number', 'city', 'province',
  'lease_start', 'lease_end', 'monthly_rent', 'monthly_rent_words', 'deposit', 'deposit_words',
  'notice_period_days', 'payment_reference', 'max_occupants',
]

// ── Actor-based field panel colors ───────────────────────────────────────
const actorFieldClasses = computed(() => {
  const prefix = actors.value[selectedActorIdx.value]?.prefix ?? ''
  if (prefix.startsWith('tenant_'))   return 'bg-success-50 text-success-700 border-success-100 hover:bg-success-100 hover:shadow-sm'
  if (prefix.startsWith('occupant_')) return 'bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-100 hover:shadow-sm'
  return {
    landlord: 'bg-info-50 text-info-700 border-info-100 hover:bg-info-100 hover:shadow-sm',
    agent:    'bg-cyan-50 text-cyan-700 border-cyan-200 hover:bg-cyan-100 hover:shadow-sm',
  }[prefix] ?? 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100 hover:shadow-sm'
})

const actorIconClass = computed(() => {
  const prefix = actors.value[selectedActorIdx.value]?.prefix ?? ''
  if (prefix.startsWith('tenant_'))   return 'text-success-500'
  if (prefix.startsWith('occupant_')) return 'text-teal-500'
  return {
    landlord: 'text-info-500',
    agent:    'text-cyan-500',
  }[prefix] ?? 'text-gray-400'
})

// ── Drag from panel into editor ─────────────────────────────────────────
function onDragStartMergeField(event: DragEvent, fieldSuffix: string) {
  const actor = actors.value[selectedActorIdx.value]
  const fieldName = `${actor.prefix}_${fieldSuffix}`
  event.dataTransfer?.setData('application/tiptap-merge-field', JSON.stringify({
    fieldName,
    category: _deriveCategory(fieldName),
    label: `${actor.label} ${fieldSuffix.replace(/_/g, ' ')}`,
  }))
  event.dataTransfer!.effectAllowed = 'copy'
}

function onDragStartSigningField(event: DragEvent, type: string) {
  const actor = actors.value[selectedActorIdx.value]
  const labelType = type === 'signed_at' ? 'Signed At' : type.charAt(0).toUpperCase() + type.slice(1)
  event.dataTransfer?.setData('application/tiptap-signing-field', JSON.stringify({
    fieldType: type,
    signerRole: actor.prefix,
    label: `${labelType} — ${actor.label}`,
  }))
  event.dataTransfer!.effectAllowed = 'copy'
}

function onDragStartLeaseField(event: DragEvent, fieldName: string) {
  event.dataTransfer?.setData('application/tiptap-merge-field', JSON.stringify({
    fieldName,
    category: _deriveCategory(fieldName),
  }))
  event.dataTransfer!.effectAllowed = 'copy'
}

function insertMergeField(fieldSuffix: string) {
  if (!editor.value) return
  const actor = actors.value[selectedActorIdx.value]
  const fieldName = `${actor.prefix}_${fieldSuffix}`
  editor.value.chain().focus().insertMergeField({
    fieldName,
    category: _deriveCategory(fieldName),
    label: `${actor.label} ${fieldSuffix.replace(/_/g, ' ')}`,
  }).run()
}

function insertMergeFieldDirect(fieldName: string) {
  if (!editor.value) return
  editor.value.chain().focus().insertMergeField({
    fieldName,
    category: _deriveCategory(fieldName),
  }).run()
}

function insertSigningField(type: 'signature' | 'initials' | 'date' | 'signed_at') {
  if (!editor.value) return
  const actor = actors.value[selectedActorIdx.value]
  const labelType = type === 'signed_at' ? 'Signed At' : type.charAt(0).toUpperCase() + type.slice(1)
  editor.value.chain().focus().insertSignatureBlock({
    fieldType: type,
    signerRole: actor.prefix,
    label: `${labelType} — ${actor.label}`,
  }).run()
}

function _deriveCategory(name: string): string {
  const n = name.toLowerCase()
  if (n.startsWith('landlord')) return 'landlord'
  if (n.startsWith('tenant')) return 'tenant'
  if (n.startsWith('property') || n.startsWith('unit') || n.startsWith('city') || n.startsWith('province')) return 'property'
  if (n.startsWith('agent')) return 'agent'
  return 'lease'
}

// ── Legacy HTML conversion ────────────────────────────────────────────────
function convertLegacyHtml(html: string, fields: any[]): string {
  // Convert {{fieldName}} markers to proper TipTap-parseable HTML
  // Block fields (signature/initials) → <div data-type="signature-block" ...>
  // Inline fields → <span data-type="merge-field" ...>
  const blockFieldNames = new Set(
    fields.filter(f => f.type === 'signature' || f.type === 'initials').map(f => f.name)
  )
  const fieldMap = new Map(fields.map(f => [f.name, f]))

  return html.replace(/\{\{([^}]+?)\}\}/g, (_, name) => {
    const trimmed = name.trim()
    const field = fieldMap.get(trimmed)

    if (blockFieldNames.has(trimmed)) {
      const type = field?.type || 'signature'
      const party = field?.party || 'landlord'
      return `<div data-type="signature-block" data-field-name="${trimmed}" data-field-type="${type}" data-signer-role="${party}">${trimmed}</div>`
    }

    return `<span data-type="merge-field" data-field-name="${trimmed}">${trimmed}</span>`
  })
}

function extractFieldsFromJson(json: any): any[] {
  const fields: any[] = []
  function walk(node: any) {
    if (node.type === 'mergeField') {
      fields.push({ name: node.attrs.fieldName, type: 'text', party: node.attrs.category })
    } else if (node.type === 'signatureBlock') {
      fields.push({
        name: node.attrs.fieldName,
        type: node.attrs.fieldType,
        party: node.attrs.signerRole,
      })
    }
    if (node.content) node.content.forEach(walk)
  }
  if (json) walk(json)
  return fields
}

// ── AI Chat ───────────────────────────────────────────────────────────────
const chatCollapsed = ref(false)
const showCapabilities = ref(false)
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string; tools_used?: { name: string; detail: string }[] }[]>([])
const chatInput = ref('')
const chatThinking = ref(false)
const chatScrollEl = ref<HTMLDivElement | null>(null)
const apiHistory = ref<{ role: string; content: string }[]>([])

const editingTools = ['edit_lines', 'update_all', 'apply_formatting', 'insert_toc', 'renumber_sections', 'add_comment', 'highlight_fields']
const skillTools = ['check_rha_compliance', 'format_sa_standard']

function _chatStorageKey() { return `tmpl_chat_${templateId.value}` }

function _loadChatHistory() {
  try {
    const raw = localStorage.getItem(_chatStorageKey())
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.apiHistory) apiHistory.value = parsed.apiHistory
      if (parsed?.messages) chatMessages.value = parsed.messages
    }
  } catch { /* ignore */ }
}

function _saveChatHistory() {
  try {
    localStorage.setItem(_chatStorageKey(), JSON.stringify({
      apiHistory: apiHistory.value,
      messages: chatMessages.value,
    }))
  } catch { /* ignore */ }
}

function scrollChat() {
  nextTick(() => {
    if (chatScrollEl.value) chatScrollEl.value.scrollTop = chatScrollEl.value.scrollHeight
  })
}

async function sendMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatThinking.value) return

  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatThinking.value = true
  scrollChat()

  try {
    const { data } = await api.post(`/leases/templates/${templateId.value}/ai-chat/`, {
      api_history: apiHistory.value,
      message: msg,
    })

    if (data.api_history) apiHistory.value = data.api_history
    chatMessages.value.push({
      role: 'assistant',
      content: data.reply,
      tools_used: data.tools_used || undefined,
    })
    _saveChatHistory()

    // Handle document updates from AI
    if (data.document_update?.html && editor.value) {
      // TipTap: use setContent instead of innerHTML manipulation
      editor.value.commands.setContent(data.document_update.html)
      markClean()
      showToast(`Document updated: ${data.document_update.summary}`)
    }
  } catch (err: any) {
    const detail = err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Unknown error'
    console.error('[AI chat error]', err?.response?.status, detail)
    chatMessages.value.push({ role: 'assistant', content: `Sorry, something went wrong: ${detail}` })
  } finally {
    chatThinking.value = false
    scrollChat()
  }
}

// Load chat history on mount, show greeting if empty
onMounted(() => {
  _loadChatHistory()
  if (!chatMessages.value.length) {
    chatMessages.value = [{
      role: 'assistant',
      content: store.template
        ? `Hi! I can help you work on "${store.template.name}".\n\nI can: edit clauses, format text, check RHA compliance, restructure to standard SA format, manage merge fields, and more.\n\nTap "Show capabilities" above to see all my tools and skills.`
        : 'Hi! I can help you improve this lease template. Tap "Show capabilities" above to see what I can do.',
    }]
  }
})

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(msg: string) {
  toastMsg.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2500)
}

// ── Toolbar sub-components ────────────────────────────────────────────────
</script>

<script lang="ts">
import { defineComponent, h } from 'vue'

const ToolBtn = defineComponent({
  props: { active: Boolean, disabled: Boolean, title: String },
  setup(props, { slots }) {
    return () => h('button', {
      class: [
        'p-1.5 rounded transition-colors',
        props.active ? 'bg-navy/10 text-navy' : 'text-gray-500 hover:bg-gray-100',
        props.disabled ? 'opacity-30 cursor-not-allowed' : '',
      ],
      disabled: props.disabled,
      title: props.title,
    }, slots.default?.())
  },
})

const ToolSep = defineComponent({
  setup() {
    return () => h('div', { class: 'w-px h-5 bg-gray-200 mx-1' })
  },
})

export default {}
</script>

<style>
@import '../../styles/tiptap-editor.css';

/* Toast animation */
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
