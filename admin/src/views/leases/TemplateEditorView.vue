<template>
  <!-- Full-screen overlay -->
  <div class="fixed inset-0 z-50 bg-white flex flex-col">

    <!-- ── Header (DocuSeal-style) ──────────────────────────────────────── -->
    <div class="flex items-center h-14 px-4 border-b border-gray-200 bg-white flex-shrink-0 gap-4">
      <div class="flex items-center gap-3 min-w-0 w-56 flex-shrink-0">
        <button @click="router.push('/leases')" class="p-1.5 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0">
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
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
          :class="isDirty
            ? 'bg-navy text-white hover:bg-navy/90 border border-navy'
            : 'text-gray-400 border border-gray-200 cursor-default'"
          @click="saveContent" :disabled="saving || !isDirty"
        >
          <Loader2 v-if="saving" :size="12" class="animate-spin" />
          <Save v-else :size="12" />
          {{ saving ? 'Saving…' : isDirty ? 'Save' : 'Saved' }}
        </button>
        <!-- Export dropdown -->
        <div class="relative">
          <div v-if="exportMenuOpen" class="fixed inset-0 z-40" @click="exportMenuOpen = false" />
          <div class="flex items-stretch border border-gray-300 rounded-lg overflow-hidden text-xs font-medium text-gray-700">
            <button class="flex items-center gap-1.5 px-3 py-1.5 hover:bg-gray-50 transition-colors" @click="exportPDF">
              <Download :size="12" /> Export PDF
            </button>
            <button class="px-1.5 py-1.5 border-l border-gray-300 hover:bg-gray-50 transition-colors" @click="exportMenuOpen = !exportMenuOpen">
              <ChevronDown :size="12" />
            </button>
          </div>
          <div v-if="exportMenuOpen" class="absolute right-0 top-full mt-1 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
            <button class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2" @click="exportPDF(); exportMenuOpen = false">
              <Download :size="11" class="text-red-500" /> Export as PDF
            </button>
            <button class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2" @click="generatePreview(); exportMenuOpen = false">
              <Download :size="11" class="text-blue-500" /> Export as DOCX
            </button>
          </div>
        </div>
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

      <!-- ── LEFT PANEL: AI Chat (collapsible) ───────────────────────────── -->
      <div
        class="flex-shrink-0 border-r border-gray-200 flex flex-col bg-white transition-all duration-200"
        :style="{ width: chatCollapsed ? '44px' : '260px' }"
      >
        <!-- Chat header -->
        <div class="flex items-center gap-2 px-3 py-3 border-b border-gray-200 flex-shrink-0">
          <button class="p-1 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0" @click="chatCollapsed = !chatCollapsed" :title="chatCollapsed ? 'Open AI chat' : 'Collapse'">
            <Sparkles :size="14" class="text-pink-brand" />
          </button>
          <template v-if="!chatCollapsed">
            <span class="text-sm font-semibold text-gray-800 whitespace-nowrap">AI Assistant</span>
            <span v-if="template" class="text-[10px] text-gray-400 truncate">— {{ template.name }}</span>
          </template>
        </div>
        <template v-if="!chatCollapsed">
          <!-- Messages -->
          <div ref="chatScrollEl" class="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
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
          <!-- Input -->
          <div class="border-t border-gray-200 p-2.5 flex gap-2 flex-shrink-0">
            <textarea
              v-model="chatInput"
              rows="2"
              placeholder="Ask about this template…"
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

      <!-- ── RIGHT PANEL: Recipients + Field Palette (~270px) ─────────────
           order-last pushes this after the center column in flex layout     -->
      <div class="w-[270px] flex-shrink-0 border-l border-gray-200 flex flex-col bg-white order-last">

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

        <!-- Active recipient indicator + colour strip -->
        <div
          class="px-3 py-2 border-b flex items-center gap-2 transition-colors"
          :style="{ borderColor: selectedColor + '33', backgroundColor: selectedColor + '0d' }"
        >
          <div
            class="w-2.5 h-2.5 rounded-full flex-shrink-0 transition-colors"
            :style="{ backgroundColor: selectedColor }"
          />
          <span
            class="text-[11px] font-semibold truncate transition-colors"
            :style="{ color: selectedColor }"
          >
            {{ selectedActorLabel }}
          </span>
          <span class="text-[10px] text-gray-400 ml-auto flex-shrink-0">
            {{ selectedActorIdx !== null ? 'Adding fields' : 'Select recipient' }}
          </span>
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
        <div class="flex border-b border-gray-100 flex-shrink-0">
          <button
            v-for="tab in ['Favorites', 'All Fields', 'Clauses']" :key="tab"
            class="flex-1 py-2 text-[11px] font-medium border-b-2 transition-all"
            :class="activeFieldTab !== tab ? 'border-transparent text-gray-500 hover:text-gray-700' : ''"
            :style="activeFieldTab === tab ? { borderColor: selectedColor, color: selectedColor } : {}"
            @click="activeFieldTab = tab; if(tab === 'Clauses') loadClauses()"
          >
            {{ tab }}
          </button>
        </div>

        <!-- ── FIELDS TABS (Favorites / All Fields) ── -->
        <template v-if="activeFieldTab !== 'Clauses'">
          <!-- Field type grid -->
          <div class="p-2 grid grid-cols-2 gap-1.5">
            <button
              v-for="ft in visibleFieldTypes" :key="ft.key"
              class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border text-xs font-medium text-left transition-all group/field"
              :class="selectedActorIdx !== null ? 'border-gray-200 text-gray-700 cursor-pointer' : 'border-gray-100 text-gray-400 cursor-not-allowed'"
              :style="selectedActorIdx !== null ? { '--actor-color': selectedColor } : {}"
              :draggable="selectedActorIdx !== null"
              @dragstart="startFieldTypeDrag($event, ft)"
              @mouseenter="selectedActorIdx !== null && ($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedColor + '66')"
              @mouseleave="selectedActorIdx !== null && ($event.currentTarget as HTMLElement).style.removeProperty('border-color')"
              @click="insertFieldType(ft)"
              :title="selectedActorIdx === null ? 'Select a recipient first' : `Insert ${ft.label}`"
            >
              <component
                :is="ft.icon" :size="13" class="flex-shrink-0 transition-colors"
                :style="selectedActorIdx !== null ? { color: selectedColor } : { color: '#d1d5db' }"
              />
              <span class="truncate">{{ ft.label }}</span>
            </button>
          </div>

          <!-- Personal Data -->
          <div class="border-t border-gray-100 pb-3">
            <div class="px-4 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Personal Data</div>
            <div class="px-2 grid grid-cols-2 gap-1.5">
              <button
                v-for="pd in personalDataFields" :key="pd.key"
                class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-700 transition-all text-left cursor-pointer"
                @mouseenter="($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedColor + '66')"
                @mouseleave="($event.currentTarget as HTMLElement).style.removeProperty('border-color')"
                @click="insertFieldType(pd)"
              >
                <component :is="pd.icon" :size="13" class="flex-shrink-0" :style="{ color: selectedColor }" />
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
                class="field-chip field-chip--lease"
                draggable="true"
                @dragstart="startFieldDrag($event, f)"
                @click="insertField(f)"
                :title="`Drag or click to insert {{ ${f} }}`"
              >{{ f }}</span>
            </div>
          </div>
        </template>

        <!-- ── CLAUSES TAB ── -->
        <div v-else class="flex flex-col flex-1 min-h-0 overflow-hidden">

          <!-- Clause toolbar -->
          <div class="px-2 pt-2 pb-1.5 space-y-1.5 border-b border-gray-100 flex-shrink-0">
            <!-- Generate row -->
            <div class="flex gap-1">
              <input
                v-model="clauseGenerateTopic"
                class="flex-1 text-[11px] border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-navy/30"
                placeholder="Topic e.g. POPIA consent…"
                @keydown.enter.prevent="generateClauses"
              />
              <button
                class="px-2.5 py-1.5 text-[11px] font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 flex items-center gap-1 flex-shrink-0 disabled:opacity-60"
                :disabled="clauseGenerating || !clauseGenerateTopic.trim()"
                @click="generateClauses"
              >
                <Loader2 v-if="clauseGenerating" :size="10" class="animate-spin" />
                <Sparkles v-else :size="10" />
                Generate
              </button>
            </div>
            <!-- Category + Extract row -->
            <div class="flex items-center gap-1">
              <select
                v-model="clauseCategory"
                class="flex-1 text-[10px] border border-gray-200 rounded px-1.5 py-1 focus:outline-none bg-white"
                @change="loadClauses"
              >
                <option value="">All categories</option>
                <option v-for="c in clauseCategories" :key="c.key" :value="c.key">{{ c.label }}</option>
              </select>
              <button
                class="text-[10px] px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 text-gray-600 flex items-center gap-1 flex-shrink-0"
                :disabled="clauseExtracting"
                @click="extractFromTemplate"
                title="Extract clauses from this template"
              >
                <Loader2 v-if="clauseExtracting" :size="9" class="animate-spin" />
                <Download v-else :size="9" />
                Extract
              </button>
            </div>
            <!-- Save selection -->
            <button
              class="w-full text-[10px] border border-dashed border-gray-300 rounded-lg py-1.5 text-gray-500 hover:border-navy/40 hover:text-navy/70 transition-colors flex items-center justify-center gap-1"
              @click="saveSelection"
            >
              <Bookmark :size="10" /> Save selected text as clause
            </button>
          </div>

          <!-- Generated options (shown before saving) -->
          <div v-if="generatedOptions.length" class="px-2 py-2 space-y-2 border-b border-amber-100 bg-amber-50/40 flex-shrink-0">
            <div class="text-[10px] font-semibold text-amber-700 uppercase px-1">Generated — click to save &amp; insert</div>
            <div
              v-for="(opt, i) in generatedOptions" :key="i"
              class="bg-white border border-amber-200 rounded-lg p-2 cursor-pointer hover:border-amber-400 transition-colors"
              @click="saveGeneratedClause(opt)"
            >
              <div class="flex items-center justify-between gap-1 mb-1">
                <span class="text-[11px] font-semibold text-gray-800 leading-snug">{{ opt.title }}</span>
                <span class="text-[9px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded flex-shrink-0">{{ opt.category }}</span>
              </div>
              <div class="text-[10px] text-gray-500 line-clamp-2 leading-relaxed" v-html="opt.html" />
            </div>
            <button class="w-full text-[10px] text-gray-400 hover:text-gray-600 py-0.5" @click="generatedOptions = []">Clear</button>
          </div>

          <!-- Saved clauses list -->
          <div class="flex-1 overflow-y-auto">
            <div v-if="clausesLoading" class="p-3 space-y-2 animate-pulse">
              <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 rounded-lg" />
            </div>
            <div v-else-if="!savedClauses.length" class="p-4 text-center text-[11px] text-gray-400">
              <div class="mb-1">No clauses saved yet.</div>
              <div>Generate some or save a selection from the editor.</div>
            </div>
            <div v-else class="p-2 space-y-1.5">
              <div
                v-for="clause in savedClauses" :key="clause.id"
                class="group border border-gray-200 rounded-lg p-2 hover:border-navy/30 transition-colors"
              >
                <div class="flex items-start justify-between gap-1">
                  <div class="flex-1 min-w-0">
                    <div class="text-[11px] font-semibold text-gray-800 leading-snug truncate">{{ clause.title }}</div>
                    <div class="flex items-center gap-1.5 mt-0.5">
                      <span class="text-[9px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{{ clause.category }}</span>
                      <span v-if="clause.use_count" class="text-[9px] text-gray-400">used {{ clause.use_count }}×</span>
                      <span v-if="clause.source_template_names?.length" class="text-[9px] text-gray-400 truncate">from {{ clause.source_template_names.join(', ') }}</span>
                    </div>
                  </div>
                  <div class="flex gap-1 flex-shrink-0">
                    <button
                      class="p-1 rounded text-navy hover:bg-navy/10 transition-colors"
                      @click="insertClause(clause)"
                      title="Insert into document"
                    >
                      <Plus :size="11" />
                    </button>
                    <button
                      class="p-1 rounded text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                      @click="deleteClause(clause.id)"
                      title="Delete"
                    >
                      <X :size="11" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Variables section (bottom of right panel) ────────────────── -->
        <div class="border-t border-gray-200 flex-shrink-0">
          <div class="flex items-center justify-between px-3 py-2">
            <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Detected Variables</span>
            <div class="flex items-center gap-1">
              <span class="text-[9px] text-gray-400">Tenants:</span>
              <select v-model="tenantCount" class="text-[9px] border border-gray-200 rounded px-0.5 py-0.5 bg-white focus:outline-none">
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
              </select>
            </div>
          </div>
          <div class="max-h-36 overflow-y-auto px-2 pb-2">
            <div v-if="template?.detected_variables && Object.keys(template.detected_variables).length" class="space-y-1.5">
              <details v-for="groupKey in visibleGroupKeys" :key="groupKey" open class="group/acc">
                <summary class="flex items-center justify-between cursor-pointer list-none text-[10px] font-semibold text-gray-500 py-0.5 hover:text-gray-800">
                  <span>{{ groupDisplayName(groupKey) }}</span>
                  <span class="text-gray-300 font-normal">{{ (template.detected_variables![groupKey] || []).length }}</span>
                </summary>
                <div class="flex flex-wrap gap-1 pl-1 pb-1">
                  <span
                    v-for="field in (template.detected_variables![groupKey] || [])" :key="field"
                    class="field-chip"
                    :class="groupChipClass(groupKey)"
                    draggable="true"
                    @dragstart="startFieldDrag($event, field)"
                    @click="insertField(field)" :title="`Drag or click to insert {{ ${field} }}`"
                  >{{ field }}</span>
                </div>
              </details>
            </div>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="f in discoveredFields" :key="f"
                class="field-chip field-chip--lease"
                draggable="true"
                @dragstart="startFieldDrag($event, f)"
                @click="insertField(f)" :title="`Drag or click to insert {{ ${f} }}`">{{ f }}</span>
              <div v-if="!discoveredFields.length" class="text-[10px] text-gray-300 italic">No fields detected.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── CENTER: Document canvas ──────────────────────────────────────── -->
      <div class="flex-1 flex flex-col overflow-hidden min-h-0 bg-[#e8eaed]">

        <!-- Toolbar (two rows) — hidden for read-only PDF templates -->
        <div v-if="!isPdfTemplate" class="border-b border-gray-300 bg-white flex-shrink-0">
          <!-- Row 1: history, paragraph style, font, size -->
          <div class="flex items-center gap-0.5 px-3 py-1.5 border-b border-gray-100 flex-wrap">
            <button class="toolbar-btn" @click="execCmd('undo')" title="Undo"><RotateCcw :size="13" /></button>
            <button class="toolbar-btn" @click="execCmd('redo')" title="Redo"><RotateCw :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Paragraph style -->
            <select
              class="text-xs border border-gray-200 rounded px-1.5 py-1 focus:outline-none bg-white"
              :value="tbBlock"
              @change="formatBlock(($event.target as HTMLSelectElement).value)"
            >
              <option value="p">Normal</option>
              <option value="h1">Heading 1</option>
              <option value="h2">Heading 2</option>
              <option value="h3">Heading 3</option>
            </select>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Font family -->
            <select
              class="text-xs border border-gray-200 rounded px-1.5 py-1 focus:outline-none bg-white"
              :value="tbFont"
              @change="execCmd('fontName', ($event.target as HTMLSelectElement).value)"
              title="Font"
            >
              <option value="Arial">Arial</option>
              <option value="Georgia">Georgia</option>
              <option value="Times New Roman">Times New Roman</option>
              <option value="Courier New">Courier New</option>
              <option value="Verdana">Verdana</option>
              <option value="Calibri">Calibri</option>
            </select>
            <!-- Font size -->
            <select
              class="text-xs border border-gray-200 rounded px-1.5 py-1 focus:outline-none bg-white w-16"
              :value="tbSize"
              @change="setFontSize(($event.target as HTMLSelectElement).value)"
              title="Font size"
            >
              <option value="">Size</option>
              <option value="8">8</option>
              <option value="9">9</option>
              <option value="10">10</option>
              <option value="11">11</option>
              <option value="12">12</option>
              <option value="14">14</option>
              <option value="16">16</option>
              <option value="18">18</option>
              <option value="20">20</option>
              <option value="24">24</option>
              <option value="28">28</option>
              <option value="32">32</option>
              <option value="36">36</option>
            </select>
            <div class="ml-auto flex items-center gap-2">
              <span v-if="isDirty" class="flex items-center gap-1.5 text-[11px] text-amber-600">
                <span class="w-1.5 h-1.5 rounded-full bg-amber-400" /> Unsaved
              </span>
            </div>
          </div>
          <!-- Row 2: formatting, lists, align, indent, color, table, field -->
          <div class="flex items-center gap-0.5 px-3 py-1 flex-wrap">
            <button class="toolbar-btn" :class="{ 'bg-navy/10 text-navy': tbBold }" @mousedown.prevent="execCmd('bold')" title="Bold"><Bold :size="13" /></button>
            <button class="toolbar-btn" :class="{ 'bg-navy/10 text-navy': tbItalic }" @mousedown.prevent="execCmd('italic')" title="Italic"><Italic :size="13" /></button>
            <button class="toolbar-btn" :class="{ 'bg-navy/10 text-navy': tbUnderline }" @mousedown.prevent="execCmd('underline')" title="Underline"><Underline :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <button class="toolbar-btn" @mousedown.prevent="execCmd('insertUnorderedList')" title="Bullet list"><List :size="13" /></button>
            <button class="toolbar-btn" @mousedown.prevent="execCmd('insertOrderedList')" title="Numbered list"><ListOrdered :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <button class="toolbar-btn" @mousedown.prevent="execCmd('justifyLeft')" title="Align left"><AlignLeft :size="13" /></button>
            <button class="toolbar-btn" @mousedown.prevent="execCmd('justifyCenter')" title="Align center"><AlignCenter :size="13" /></button>
            <button class="toolbar-btn" @mousedown.prevent="execCmd('justifyRight')" title="Align right"><AlignRight :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Indent / Outdent via Tab / Shift+Tab -->
            <button class="toolbar-btn" @mousedown.prevent="simulateIndent(true)" title="Decrease indent (Shift+Tab)"><IndentDecrease :size="13" /></button>
            <button class="toolbar-btn" @mousedown.prevent="simulateIndent(false)" title="Increase indent (Tab)"><IndentIncrease :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Text color -->
            <div class="relative flex items-center gap-0.5" title="Text color">
              <button
                class="toolbar-btn relative"
                @mousedown.prevent="colorPickerOpen = !colorPickerOpen"
              >
                <Palette :size="13" />
                <span class="absolute bottom-0 left-1/2 -translate-x-1/2 w-3 h-0.5 rounded-sm" :style="{ background: activeTextColor }" />
              </button>
              <!-- quick swatches -->
              <div v-if="colorPickerOpen" class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-2 w-[168px]">
                <div class="grid grid-cols-8 gap-0.5 mb-1.5">
                  <button
                    v-for="c in colorSwatches" :key="c"
                    class="w-4 h-4 rounded-sm border border-gray-200 hover:scale-110 transition-transform"
                    :style="{ background: c }"
                    @mousedown.prevent="applyColor(c)"
                  />
                </div>
                <input type="color" :value="activeTextColor" class="w-full h-6 cursor-pointer rounded border border-gray-200"
                  @input="applyColor(($event.target as HTMLInputElement).value)" />
              </div>
            </div>
            <!-- Background / cell fill color -->
            <div class="relative flex items-center gap-0.5" title="Background / cell fill color">
              <button
                class="toolbar-btn relative"
                @mousedown.prevent="bgColorPickerOpen = !bgColorPickerOpen; colorPickerOpen = false"
              >
                <PaintBucket :size="13" />
                <span class="absolute bottom-0 left-1/2 -translate-x-1/2 w-3 h-0.5 rounded-sm" :style="{ background: activeBgColor }" />
              </button>
              <div v-if="bgColorPickerOpen" class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-2 w-[168px]">
                <div class="text-[10px] text-gray-400 mb-1">Cell / highlight color</div>
                <div class="grid grid-cols-8 gap-0.5 mb-1.5">
                  <button
                    v-for="c in colorSwatches" :key="c"
                    class="w-4 h-4 rounded-sm border border-gray-200 hover:scale-110 transition-transform"
                    :style="{ background: c }"
                    @mousedown.prevent="applyBackgroundColor(c)"
                  />
                </div>
                <input type="color" :value="activeBgColor" class="w-full h-6 cursor-pointer rounded border border-gray-200"
                  @input="applyBackgroundColor(($event.target as HTMLInputElement).value)" />
              </div>
            </div>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Heading styles -->
            <div class="relative">
              <button
                class="toolbar-btn flex items-center gap-1 font-semibold text-[11px]"
                :class="headingStylesOpen ? 'text-navy bg-navy/10' : ''"
                @mousedown.prevent="headingStylesOpen = !headingStylesOpen; colorPickerOpen = false; bgColorPickerOpen = false"
                title="Heading styles"
              >H<span class="text-[9px] text-gray-400">1–3</span></button>
              <!-- Panel -->
              <div v-if="headingStylesOpen" class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl z-30 w-80 p-3">
                <div class="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2">Heading Styles</div>
                <div class="space-y-2">
                  <div v-for="lvl in headingLevels" :key="lvl.tag" class="flex items-center gap-2">
                    <!-- Level label (like TOC indent) -->
                    <span
                      class="w-8 text-[11px] font-bold flex-shrink-0 text-gray-600"
                      :style="{ marginLeft: lvl.indent + 'px' }"
                    >{{ lvl.label }}</span>
                    <!-- Font family -->
                    <select
                      v-model="lvl.fontFamily"
                      class="text-[11px] border border-gray-200 rounded px-1 py-0.5 focus:outline-none bg-white w-24 flex-shrink-0"
                    >
                      <option value="">Default</option>
                      <option v-for="f in fontFamilies" :key="f" :value="f">{{ f }}</option>
                    </select>
                    <!-- Font size -->
                    <select
                      v-model="lvl.fontSize"
                      class="text-[11px] border border-gray-200 rounded px-1 py-0.5 focus:outline-none bg-white w-14 flex-shrink-0"
                    >
                      <option value="">Auto</option>
                      <option v-for="s in [8,9,10,11,12,14,16,18,20,24,28,32,36]" :key="s" :value="String(s)">{{ s }}</option>
                    </select>
                    <!-- Bold -->
                    <button
                      class="w-6 h-6 rounded border text-[11px] font-bold flex-shrink-0 transition-colors"
                      :class="lvl.bold ? 'bg-navy text-white border-navy' : 'border-gray-200 text-gray-400'"
                      @click="lvl.bold = !lvl.bold"
                    >B</button>
                    <!-- Color -->
                    <div class="relative flex-shrink-0">
                      <button
                        class="w-6 h-6 rounded border border-gray-200 overflow-hidden"
                        :style="{ background: lvl.color || '#111827' }"
                        @click="lvl.colorOpen = !lvl.colorOpen"
                      />
                      <div v-if="lvl.colorOpen" class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-40 p-2 w-[144px]">
                        <div class="grid grid-cols-8 gap-0.5 mb-1.5">
                          <button v-for="c in colorSwatches" :key="c"
                            class="w-4 h-4 rounded-sm border border-gray-200 hover:scale-110 transition-transform"
                            :style="{ background: c }"
                            @click="lvl.color = c; lvl.colorOpen = false" />
                        </div>
                        <input type="color" :value="lvl.color" class="w-full h-6 cursor-pointer rounded"
                          @input="lvl.color = ($event.target as HTMLInputElement).value" />
                      </div>
                    </div>
                    <!-- Apply -->
                    <button
                      class="ml-auto text-[10px] px-2 py-0.5 bg-navy text-white rounded hover:bg-navy/90 flex-shrink-0"
                      @click="applyHeadingStyle(lvl)"
                    >Apply</button>
                  </div>
                </div>
                <button class="mt-3 w-full text-[11px] py-1.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-semibold"
                  @click="applyAllHeadingStyles">Apply All</button>
              </div>
            </div>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Insert table -->
            <button class="toolbar-btn" @mousedown.prevent="insertTable()" title="Insert table"><Table :size="13" /></button>
            <!-- Insert page break -->
            <button class="toolbar-btn" @mousedown.prevent="insertPageBreak()" title="Insert page break"><Scissors :size="13" /></button>
            <!-- Toggle page numbers -->
            <button
              class="toolbar-btn"
              :class="showPageNumbers ? 'text-navy bg-navy/10' : ''"
              @mousedown.prevent="showPageNumbers = !showPageNumbers"
              title="Toggle page numbers"
            ><FileDigit :size="13" /></button>
            <!-- Header/footer config -->
            <button
              class="toolbar-btn"
              :class="headerFooterPanelOpen ? 'text-navy bg-navy/10' : ''"
              @mousedown.prevent="headerFooterPanelOpen = !headerFooterPanelOpen; colorPickerOpen = false; bgColorPickerOpen = false; headingStylesOpen = false"
              title="Page header & footer"
            ><LayoutTemplate :size="13" /></button>
            <div class="w-px h-5 bg-gray-200 mx-1" />
            <!-- Insert merge field -->
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
          </div>
        </div>

        <!-- Document page (scrollable) -->
        <div class="flex-1 overflow-y-auto py-8 px-4 min-h-0 bg-[#e8eaed]" @click="showFieldPicker = false; headingStylesOpen = false">
          <!-- Loading skeleton -->
          <div v-if="loadingPreview" class="max-w-[680px] mx-auto bg-white shadow-md px-14 py-12 min-h-[961px] space-y-3 animate-pulse">
            <div class="h-5 bg-gray-200 rounded w-1/3 mx-auto mb-6" />
            <div v-for="i in 8" :key="i" class="h-3 bg-gray-100 rounded" :class="i % 3 === 0 ? 'w-4/5' : i % 2 === 0 ? 'w-full' : 'w-11/12'" />
          </div>

          <!-- PDF viewer (read-only) -->
          <div v-if="!loadingPreview && isPdfTemplate && pdfUrl" class="flex flex-col gap-2 h-full">
            <div class="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 text-xs text-amber-700 flex-shrink-0">
              <span class="font-semibold">PDF template</span> — this document is read-only. To make it editable, convert it to a DOCX and re-upload.
            </div>
            <iframe
              :src="pdfUrl"
              class="w-full flex-1 bg-white shadow-md border-0 rounded"
              style="min-height: 800px;"
              title="Template PDF preview"
            />
          </div>

          <!-- A4 document page -->
          <div class="relative max-w-[680px] mx-auto overflow-x-hidden" v-if="!loadingPreview && !isPdfTemplate">
            <!-- Page header overlay (non-editable, shown on every page) -->
            <div v-if="showHeader" class="page-header-overlay">
              <span class="page-header-left">{{ headerLeft }}</span>
              <span class="page-header-right">{{ headerRight }}</span>
            </div>
            <div
              ref="editorEl"
              contenteditable="true"
              class="w-full bg-white shadow-md px-14 min-h-[961px] focus:outline-none document-editor leading-relaxed relative"
              :class="{ 'ring-2 ring-navy/30': isDraggingField, 'show-page-numbers': showPageNumbers }"
              :style="{ paddingTop: showHeader ? '3.5rem' : '3rem', paddingBottom: showFooter ? '3.5rem' : '3rem' }"
              @input="onEditorInput"
              @keydown="onEditorKeydown"
              @dragstart="onEditorDragStart"
              @dragover.prevent="onEditorDragOver"
              @dragleave="isDraggingField = false"
              @drop.prevent="onEditorDrop"
              v-html="editorHtml"
            />
            <!-- Page number overlays (rendered outside contenteditable) -->
            <template v-if="showPageNumbers">
              <div
                v-for="(_, pi) in pageCount" :key="pi"
                class="page-number-overlay"
                :style="{ top: pageNumberTop(pi) + 'px' }"
              >Page {{ pi + 1 }} of {{ pageCount }}</div>
            </template>
            <!-- Page footer overlay -->
            <div v-if="showFooter" class="page-footer-overlay">
              <span class="page-footer-left">{{ footerLeft }}</span>
              <span class="page-footer-right">1</span>
            </div>
            <!-- Header/footer config panel -->
            <div v-if="headerFooterPanelOpen" class="absolute top-10 left-0 right-0 mx-auto w-80 bg-white border border-gray-200 rounded-xl shadow-xl z-40 p-3 text-xs" @click.stop>
              <div class="font-semibold text-gray-600 mb-2 flex items-center justify-between">
                Page Header &amp; Footer
                <button class="text-gray-400 hover:text-gray-600" @click="headerFooterPanelOpen = false">✕</button>
              </div>
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <label class="w-20 text-gray-500 flex-shrink-0">Header left</label>
                  <input v-model="headerLeft" class="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none" placeholder="Document title" />
                </div>
                <div class="flex items-center gap-2">
                  <label class="w-20 text-gray-500 flex-shrink-0">Header right</label>
                  <input v-model="headerRight" class="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none" placeholder="k." />
                </div>
                <div class="flex items-center gap-2">
                  <label class="w-20 text-gray-500 flex-shrink-0">Footer left</label>
                  <input v-model="footerLeft" class="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none" placeholder="Company name" />
                </div>
                <div class="flex items-center gap-2 pt-1">
                  <label class="flex items-center gap-1 cursor-pointer"><input type="checkbox" v-model="showHeader" class="rounded" /> Show header</label>
                  <label class="flex items-center gap-1 cursor-pointer ml-3"><input type="checkbox" v-model="showFooter" class="rounded" /> Show footer</label>
                </div>
              </div>
            </div>
          </div>

          <div class="text-center text-[11px] text-gray-400 mt-3">Page {{ pageCount > 1 ? '1–' + pageCount : '1' }} of {{ pageCount }} · Click to edit · Select a recipient then click field types to insert</div>
        </div>
      </div>

    </div>

    <!-- {{ variable autocomplete popup -->
    <Teleport to="body">
      <div
        v-if="ac.show"
        class="fixed z-[999] bg-white border border-gray-200 rounded-xl shadow-xl w-64 overflow-hidden"
        :style="{ left: ac.x + 'px', top: ac.y + 'px' }"
        @mousedown.prevent
      >
        <div class="flex border-b border-gray-100">
          <button v-for="tab in ['Recent','All']" :key="tab"
            class="flex-1 py-1.5 text-[11px] font-semibold transition-colors"
            :class="ac.tab === tab ? 'text-teal-600 border-b-2 border-teal-500' : 'text-gray-400 hover:text-gray-600'"
            @click="ac.tab = tab; ac.selectedIdx = 0">{{ tab }}
          </button>
        </div>
        <div class="max-h-52 overflow-y-auto py-1">
          <div v-if="!acFields.length" class="px-3 py-2 text-[11px] text-gray-400 italic">No matches</div>
          <button
            v-for="(f, idx) in acFields" :key="f"
            class="w-full text-left px-3 py-1.5 text-[11px] font-mono transition-colors"
            :class="idx === ac.selectedIdx ? 'bg-teal-50 text-teal-700' : 'text-gray-700 hover:bg-gray-50'"
            @click="acInsert(f)"
          >{{ f }}</button>
        </div>
      </div>
    </Teleport>

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
import { ref, computed, onMounted, onBeforeUnmount, nextTick, markRaw } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  X, FileSignature, FileText, Sparkles, Send, Download, Save, CheckCircle2,
  Braces, ChevronLeft, ChevronDown, Loader2, Bookmark, Plus,
  Bold, Italic, Underline, List, ListOrdered, AlignLeft, AlignCenter, AlignRight,
  IndentDecrease, IndentIncrease, Palette, PaintBucket, Table,
  RotateCcw, RotateCw,
  Users, User, UserCheck, Building2,
  Hash, Calendar, CheckSquare, Phone, Mail, Type, Pen, StickyNote,
  Scissors, FileDigit, LayoutTemplate,
} from 'lucide-vue-next'
import api from '../../api'

const route = useRoute()
const router = useRouter()
const templateId = computed(() => Number(route.params.id))

// ── Template data ─────────────────────────────────────────────────────────
interface TemplateInfo {
  id: number; name: string; version: string; is_active: boolean
  fields_schema: string[]; content_html: string; docx_file: string | null
  detected_variables?: Record<string, string[]>
}
interface PreviewData {
  type: 'docx' | 'pdf'; name: string; fields: string[]
  paragraphs: { style: string; text: string }[]; content_html: string
  pdf_url?: string
}

const template = ref<TemplateInfo | null>(null)
const preview  = ref<PreviewData | null>(null)
const loadingPreview = ref(true)

// ── Editor state ──────────────────────────────────────────────────────────
const editorEl  = ref<HTMLDivElement | null>(null)
const editorHtml = ref('')
const savedHtml  = ref('')

// ── Header / footer config ─────────────────────────────────────────────────
const headerLeft  = ref('')   // document title / company name top-left
const headerRight = ref('k.') // logo / brand top-right
const footerLeft  = ref('')   // company name bottom-left
const showHeader  = ref(true)
const showFooter  = ref(true)
const headerFooterPanelOpen = ref(false)
const saving     = ref(false)
const isDirty    = ref(false)
const showFieldPicker = ref(false)
const showPageNumbers = ref(false)

// Page count — one more than the number of page-break markers in the HTML
const pageCount = computed(() => {
  const matches = (editorHtml.value || '').match(/data-page-break/g)
  return matches ? matches.length + 1 : 1
})

// Y-offset (px) for the page number overlay of page `pi` (0-indexed).
// We measure the height of page-break divs in the live DOM.
function pageNumberTop(pi: number): number {
  if (!editorEl.value) return 0
  const breaks = Array.from(editorEl.value.querySelectorAll('[data-page-break]')) as HTMLElement[]
  const editorRect = editorEl.value.getBoundingClientRect()
  const scrollTop  = editorEl.value.closest('.overflow-y-auto')?.scrollTop ?? 0
  if (pi === 0) {
    // First page: near the top of the editor div
    const firstBreak = breaks[0]
    const bottom = firstBreak
      ? firstBreak.getBoundingClientRect().top - editorRect.top + scrollTop - 8
      : editorEl.value.offsetHeight - 20
    return Math.max(0, bottom - 20)
  }
  const prevBreak = breaks[pi - 1]
  const nextBreak = breaks[pi]
  const top = prevBreak.getBoundingClientRect().top - editorRect.top + scrollTop + prevBreak.offsetHeight + 4
  const bottom = nextBreak
    ? nextBreak.getBoundingClientRect().top - editorRect.top + scrollTop - 8
    : editorEl.value.offsetHeight - 20
  return Math.max(top, bottom - 20)
}

function insertPageBreak() {
  restoreEditorSelection()
  // Wrap in a paragraph so the cursor lands cleanly after the break
  const html = '<p><br></p><div data-page-break="true" contenteditable="false"></div><p><br></p>'
  document.execCommand('insertHTML', false, html)
  onEditorInput()
}

// ── Selection preservation (toolbar must not lose editor caret) ───────────
// Always track the last selection inside the editor via selectionchange so
// any toolbar action (button, dropdown, color picker) can restore it.
let _savedRange: Range | null = null
function _trackSelection() {
  const sel = window.getSelection()
  if (sel && sel.rangeCount > 0) {
    const r = sel.getRangeAt(0)
    if (editorEl.value?.contains(r.commonAncestorContainer)) {
      _savedRange = r.cloneRange()
      updateToolbarState()
    }
  }
}
function restoreEditorSelection() {
  editorEl.value?.focus()
  if (_savedRange) {
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(_savedRange)
  }
}

// ── Toolbar reflected state (updates on cursor move / click) ──────────────
const tbBlock      = ref('p')        // paragraph style dropdown
const tbFont       = ref('Arial')    // font family dropdown
const tbSize       = ref('')         // font size dropdown
const tbBold       = ref(false)
const tbItalic     = ref(false)
const tbUnderline  = ref(false)

function updateToolbarState() {
  if (!editorEl.value) return
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  const range = sel.getRangeAt(0)
  // Only reflect when cursor is inside the editor
  if (!editorEl.value.contains(range.commonAncestorContainer)) return

  // Block tag — walk up to find block element
  let node: Node | null = range.startContainer
  tbBlock.value = 'p'
  while (node && node !== editorEl.value) {
    if (node instanceof HTMLElement) {
      const t = node.tagName.toLowerCase()
      if (['h1','h2','h3','h4','p','li'].includes(t)) { tbBlock.value = t; break }
    }
    node = node.parentNode
  }

  // Font family
  const ff = document.queryCommandValue('fontName')
  if (ff) tbFont.value = ff.replace(/['"]/g, '').split(',')[0].trim()

  // Font size — prefer inline style walk over queryCommandValue (returns 1–7 sizes)
  let fsNode: Node | null = range.startContainer
  tbSize.value = ''
  while (fsNode && fsNode !== editorEl.value) {
    if (fsNode instanceof HTMLElement) {
      const fs = fsNode.style.fontSize
      if (fs) {
        const match = fs.match(/^([\d.]+)/)
        if (match) { tbSize.value = String(Math.round(parseFloat(match[1]))); break }
      }
    }
    fsNode = fsNode.parentNode
  }

  // Bold / italic / underline
  tbBold.value      = document.queryCommandState('bold')
  tbItalic.value    = document.queryCommandState('italic')
  tbUnderline.value = document.queryCommandState('underline')
}

// ── UI state ──────────────────────────────────────────────────────────────
const chatCollapsed  = ref(false)
const isDraggingField = ref(false)
const colorPickerOpen = ref(false)
const activeTextColor = ref('#111111')
const bgColorPickerOpen = ref(false)
const activeBgColor = ref('#f3f4f6')
const colorSwatches = [
  '#111111','#374151','#6b7280','#d1d5db','#ffffff',
  '#1e3a5f','#2563eb','#0ea5e9','#10b981','#84cc16',
  '#f59e0b','#ef4444','#ec4899','#8b5cf6','#f97316','#14b8a6',
]
// ── Heading styles panel ──────────────────────────────────────────────────
const headingStylesOpen = ref(false)
const fontFamilies = ['Arial','Georgia','Times New Roman','Courier New','Verdana','Calibri']

interface HeadingLevel {
  tag: string; label: string; indent: number
  fontSize: string; fontFamily: string; bold: boolean; color: string; colorOpen: boolean
}
const headingLevels = ref<HeadingLevel[]>([
  { tag: 'h1', label: 'H1', indent: 0,  fontSize: '24', fontFamily: '', bold: true,  color: '#111827', colorOpen: false },
  { tag: 'h2', label: 'H2', indent: 8,  fontSize: '18', fontFamily: '', bold: true,  color: '#1e3a5f', colorOpen: false },
  { tag: 'h3', label: 'H3', indent: 16, fontSize: '14', fontFamily: '', bold: false, color: '#374151', colorOpen: false },
])

function applyHeadingStyle(lvl: HeadingLevel) {
  if (!editorEl.value) return
  editorEl.value.querySelectorAll<HTMLElement>(lvl.tag).forEach(el => {
    if (lvl.fontSize)    el.style.fontSize   = `${lvl.fontSize}pt`
    if (lvl.fontFamily)  el.style.fontFamily  = lvl.fontFamily
    el.style.fontWeight = lvl.bold ? 'bold' : 'normal'
    if (lvl.color)       el.style.color       = lvl.color
  })
  onEditorInput()
  showToast(`${lvl.label} styles applied`)
}

function applyAllHeadingStyles() {
  headingLevels.value.forEach(applyHeadingStyle)
  headingStylesOpen.value = false
}

const showAddActor   = ref(false)
const activeFieldTab = ref('All Fields')
const selectedActorIdx = ref<number | null>(null)   // -1 = Me, 0+ = actors[]
const fieldNotice    = ref('')
const actionFeedback = ref('')

// ── Tenant count for variable panel ───────────────────────────────────────
const tenantCount = ref(1)

// ── Active actor color (drives field palette UI tinting) ──────────────────
const selectedColor = computed<string>(() => {
  if (selectedActorIdx.value === -1) return '#1e3a5f'
  if (selectedActorIdx.value !== null && selectedActorIdx.value < actors.value.length) {
    return actorColor(actors.value[selectedActorIdx.value].type, selectedActorIdx.value)
  }
  return '#9ca3af' // gray = nothing selected
})

const selectedActorLabel = computed<string>(() => {
  if (selectedActorIdx.value === -1) return 'Me (Agent)'
  if (selectedActorIdx.value !== null && selectedActorIdx.value < actors.value.length) {
    return actors.value[selectedActorIdx.value].label
  }
  return 'No recipient selected'
})

// ── Chat state ────────────────────────────────────────────────────────────
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])
const chatInput    = ref('')
const chatThinking = ref(false)
const chatScrollEl = ref<HTMLDivElement | null>(null)
// Full Claude API conversation (includes initial doc context); sent back each turn
// so Claude doesn't need to re-read the document. Persisted to localStorage per template.
const apiHistory   = ref<{ role: string; content: string }[]>([])

function _chatStorageKey() { return `tmpl_chat_${templateId.value}` }

function _loadChatHistory() {
  try {
    const raw = localStorage.getItem(_chatStorageKey())
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.apiHistory) apiHistory.value = parsed.apiHistory
      if (parsed?.messages)   chatMessages.value = parsed.messages
    }
  } catch { /* ignore */ }
}

function _saveChatHistory() {
  try {
    localStorage.setItem(_chatStorageKey(), JSON.stringify({
      apiHistory: apiHistory.value,
      messages:   chatMessages.value,
    }))
  } catch { /* ignore */ }
}

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
  'page_number', 'total_pages',
]

// ── Computed ──────────────────────────────────────────────────────────────
const isPdfTemplate = computed(() => preview.value?.type === 'pdf' && !editorHtml.value)
const pdfUrl = computed(() => preview.value?.pdf_url ?? null)

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
  document.addEventListener('selectionchange', _trackSelection)
  await Promise.all([loadTemplate(), loadPreview()])
  // Restore persisted chat history; if none, show greeting
  _loadChatHistory()
  if (!chatMessages.value.length) {
    chatMessages.value = [{
      role: 'assistant',
      content: template.value
        ? `Hi! I can help you work on "${template.value.name}". I can explain clauses, suggest additions, generate new clause text, or advise on signing fields. What would you like to do?`
        : 'Hi! I can help you improve this lease template. What would you like to work on?',
    }]
  }
})

async function loadTemplate() {
  try {
    const { data } = await api.get(`/leases/templates/${templateId.value}/`)
    template.value = data
  } catch { /* ignore */ }
}

async function loadPreview() {
  loadingPreview.value = true
  try {
    const { data } = await api.get(`/leases/templates/${templateId.value}/preview/`)
    preview.value = data
    // Restore header/footer config
    if (data.header_html) headerLeft.value = data.header_html
    else if (template.value?.name) headerLeft.value = template.value.name
    if (data.footer_html) footerLeft.value = data.footer_html
    if (data.content_html) {
      editorHtml.value = data.content_html
      savedHtml.value  = data.content_html
    } else if (data.paragraphs?.length) {
      // Build HTML from DOCX paragraphs and immediately persist it so the AI can see it
      const html = buildHtmlFromParagraphs(data.paragraphs)
      editorHtml.value = html
      savedHtml.value  = html
      isDirty.value    = false
      await api.patch(`/leases/templates/${templateId.value}/`, { content_html: html })
      if (template.value) template.value.content_html = html
    }
  } catch { /* ignore */ }
  finally { loadingPreview.value = false }
}

// Clear editor state when leaving so next visit loads fresh from DB
onBeforeUnmount(() => {
  document.removeEventListener('selectionchange', _trackSelection)
  editorHtml.value = ''
  savedHtml.value  = ''
  isDirty.value    = false
  apiHistory.value = []   // reset so next session re-reads the document
})

// Warn before navigating away with unsaved changes
onBeforeRouteLeave(() => {
  if (isDirty.value) {
    return window.confirm('You have unsaved changes. Leave without saving?')
  }
})

// ── {{ autocomplete ───────────────────────────────────────────────────────
const ac = ref({ show: false, query: '', x: 0, y: 0, selectedIdx: 0, tab: 'Recent' })
const recentFields = ref<string[]>([])

const acFields = computed(() => {
  const q = ac.value.query.toLowerCase()
  const pool = ac.value.tab === 'Recent' && recentFields.value.length
    ? recentFields.value
    : allFields.value
  return q ? pool.filter(f => f.toLowerCase().includes(q)) : pool
})

function _checkAutocomplete() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) { ac.value.show = false; return }
  const range = sel.getRangeAt(0)
  if (!range.collapsed || range.startContainer.nodeType !== Node.TEXT_NODE) {
    ac.value.show = false; return
  }
  const text = (range.startContainer.textContent ?? '').slice(0, range.startOffset)
  const match = text.match(/\{\{(\w*)$/)
  if (!match) { ac.value.show = false; return }

  const rect = range.getBoundingClientRect()
  ac.value = { show: true, query: match[1], x: rect.left, y: rect.bottom + 6, selectedIdx: 0, tab: ac.value.tab }
}

function acInsert(fieldName: string) {
  // Delete the {{ query text, then insert the field chip
  const sel = window.getSelection()
  if (sel && sel.rangeCount > 0) {
    const range = sel.getRangeAt(0)
    const node = range.startContainer as Text
    const offset = range.startOffset
    const text = node.textContent ?? ''
    const matchStart = text.lastIndexOf('{{', offset)
    if (matchStart !== -1) {
      node.deleteData(matchStart, offset - matchStart)
      range.setStart(node, matchStart)
      range.collapse(true)
      sel.removeAllRanges()
      sel.addRange(range)
    }
  }
  // Track as recent
  recentFields.value = [fieldName, ...recentFields.value.filter(f => f !== fieldName)].slice(0, 15)
  ac.value.show = false
  insertField(fieldName)
}

function onEditorKeydown(e: KeyboardEvent) {
  // Autocomplete keyboard navigation
  if (ac.value.show) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      ac.value.selectedIdx = Math.min(ac.value.selectedIdx + 1, acFields.value.length - 1)
      return
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      ac.value.selectedIdx = Math.max(ac.value.selectedIdx - 1, 0)
      return
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      const f = acFields.value[ac.value.selectedIdx]
      if (f) acInsert(f)
      return
    } else if (e.key === 'Escape') {
      ac.value.show = false
      return
    }
  }

  // Tab → indent / Shift+Tab → outdent current block
  if (e.key === 'Tab') {
    e.preventDefault()
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return
    let node: Node | null = sel.getRangeAt(0).startContainer
    while (node && node !== editorEl.value) {
      if (node instanceof HTMLElement && ['P','H1','H2','H3','H4','LI'].includes(node.tagName)) {
        const cur = parseInt(node.style.marginLeft || '0', 10)
        const next = e.shiftKey ? Math.max(0, cur - 24) : cur + 24
        node.style.marginLeft = next > 0 ? `${next}px` : ''
        onEditorInput()
        return
      }
      node = node.parentNode
    }
  }
}

function simulateIndent(outdent: boolean) {
  restoreEditorSelection()
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  let node: Node | null = sel.getRangeAt(0).startContainer
  while (node && node !== editorEl.value) {
    if (node instanceof HTMLElement && ['P','H1','H2','H3','H4','LI'].includes(node.tagName)) {
      const cur = parseInt(node.style.marginLeft || '0', 10)
      const next = outdent ? Math.max(0, cur - 24) : cur + 24
      node.style.marginLeft = next > 0 ? `${next}px` : ''
      onEditorInput()
      return
    }
    node = node.parentNode
  }
}

// ── Editor ────────────────────────────────────────────────────────────────
function onEditorInput() {
  isDirty.value = (editorEl.value?.innerHTML ?? '') !== savedHtml.value
  _checkAutocomplete()
}

async function saveContent() {
  if (!editorEl.value) return
  saving.value = true
  const html = editorEl.value.innerHTML
  try {
    await api.patch(`/leases/templates/${templateId.value}/`, {
      content_html: html,
      header_html: headerLeft.value,
      footer_html: footerLeft.value,
    })
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
  restoreEditorSelection()
  document.execCommand(cmd, false, value)
  onEditorInput()
}

function formatBlock(tag: string) {
  execCmd('formatBlock', tag)
}

function setFontSize(pt: string) {
  if (!pt) return
  restoreEditorSelection()
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  const range = sel.getRangeAt(0)
  if (range.collapsed) {
    // No selection — apply to current block element
    let node: Node | null = range.startContainer
    while (node && node !== editorEl.value) {
      if (node instanceof HTMLElement && ['P','H1','H2','H3','H4','LI'].includes(node.tagName)) {
        node.style.fontSize = `${pt}pt`
        onEditorInput()
        return
      }
      node = node.parentNode
    }
    return
  }
  try {
    const span = document.createElement('span')
    span.style.fontSize = `${pt}pt`
    range.surroundContents(span)
  } catch {
    // surroundContents fails if range crosses elements; fall back to execCommand
    document.execCommand('styleWithCSS', false, 'true')
    document.execCommand('fontSize', false, '3') // placeholder
    // Replace browser <font> tags with proper span
    editorEl.value?.querySelectorAll('font[size="3"]').forEach(el => {
      const s = document.createElement('span')
      s.style.fontSize = `${pt}pt`
      s.innerHTML = (el as HTMLElement).innerHTML
      el.replaceWith(s)
    })
  }
  onEditorInput()
}

function applyColor(color: string) {
  activeTextColor.value = color
  colorPickerOpen.value = false
  execCmd('foreColor', color)
}

function applyBackgroundColor(color: string) {
  activeBgColor.value = color
  bgColorPickerOpen.value = false
  restoreEditorSelection()
  // Walk up from selection to find table cell → apply background to cell
  const sel = window.getSelection()
  if (sel && sel.rangeCount > 0) {
    let node: Node | null = sel.getRangeAt(0).startContainer
    while (node && node !== editorEl.value) {
      if (node instanceof HTMLElement && (node.tagName === 'TD' || node.tagName === 'TH')) {
        node.style.backgroundColor = color
        onEditorInput()
        return
      }
      node = node.parentNode
    }
  }
  // Fallback: highlight selected text
  document.execCommand('hiliteColor', false, color)
  onEditorInput()
}

function insertTable() {
  const rows = 3, cols = 3
  const cellStyle = 'border:1px solid #d1d5db;padding:6px 8px;min-width:60px;'
  const header = `<tr>${Array(cols).fill(`<th style="${cellStyle}background:#f3f4f6;font-weight:600">Heading</th>`).join('')}</tr>`
  const row = `<tr>${Array(cols).fill(`<td style="${cellStyle}"> </td>`).join('')}</tr>`
  const body = Array(rows - 1).fill(row).join('')
  const tableHtml = `<table style="border-collapse:collapse;width:100%;margin:8px 0"><thead>${header}</thead><tbody>${body}</tbody></table><p><br></p>`
  editorEl.value?.focus()
  document.execCommand('insertHTML', false, tableHtml)
  onEditorInput()
}

// ── Drag-and-drop field insertion ─────────────────────────────────────────
// Tracks a chip being moved within the editor (null = drag from sidebar)
let _draggedChipEl: HTMLElement | null = null

function onEditorDragStart(event: DragEvent) {
  // Delegate: only handle drags that start on a .tmpl-field chip
  const chip = (event.target as HTMLElement).closest('[data-field]') as HTMLElement | null
  if (!chip) return
  _draggedChipEl = chip
  const fieldName = chip.dataset.field!
  event.dataTransfer!.effectAllowed = 'move'
  event.dataTransfer!.setData('text/x-field', fieldName)
  event.dataTransfer!.setData('text/x-chip-move', '1')
  // Teal pill ghost
  const ghost = document.createElement('span')
  ghost.textContent = `{{ ${fieldName} }}`
  ghost.style.cssText = 'position:fixed;top:-999px;background:#0d9488;color:#fff;padding:2px 10px;border-radius:9999px;font:500 11px monospace'
  document.body.appendChild(ghost)
  event.dataTransfer!.setDragImage(ghost, ghost.offsetWidth / 2, 12)
  setTimeout(() => ghost.remove(), 0)
}

function _fieldNameForType(ft: { key: string }): string | null {
  if (selectedActorIdx.value === -1) {
    const keyMap: Record<string, string> = {
      signature: 'agent_signature', initials: 'agent_initials', text: 'agent_text',
      number: 'agent_number', date: 'agent_date', checkbox: 'agent_checkbox',
      name: 'agent_name', phone: 'agent_phone', email: 'agent_email',
    }
    return keyMap[ft.key] ?? `agent_${ft.key}`
  } else if (selectedActorIdx.value !== null && selectedActorIdx.value < actors.value.length) {
    const actor = actors.value[selectedActorIdx.value]
    const pfx = actorPrefix(actor)
    const keyMap: Record<string, string> = {
      signature: `${pfx}_signature`, initials: `${pfx}_initials`, text: `${pfx}_text`,
      number: `${pfx}_number`, date: `${pfx}_date_signed`, checkbox: `${pfx}_checkbox`,
      name: `${pfx}_name`, phone: `${pfx}_phone`, email: `${pfx}_email`,
    }
    return keyMap[ft.key] ?? `${pfx}_${ft.key}`
  }
  return null
}

function startFieldTypeDrag(event: DragEvent, ft: { key: string }) {
  const fieldName = _fieldNameForType(ft)
  if (!fieldName) { event.preventDefault(); return }
  startFieldDrag(event, fieldName)
}

function startFieldDrag(event: DragEvent, fieldName: string) {
  isDraggingField.value = true
  event.dataTransfer!.effectAllowed = 'copy'
  event.dataTransfer!.setData('text/x-field', fieldName)
  // Ghost label
  const ghost = document.createElement('span')
  ghost.textContent = `{{ ${fieldName} }}`
  ghost.style.cssText = 'position:fixed;top:-999px;background:#0d9488;color:#fff;padding:2px 10px;border-radius:9999px;font:500 11px monospace'
  document.body.appendChild(ghost)
  event.dataTransfer!.setDragImage(ghost, ghost.offsetWidth / 2, 12)
  setTimeout(() => ghost.remove(), 0)
}

function onEditorDragOver(event: DragEvent) {
  isDraggingField.value = true
  event.dataTransfer!.dropEffect = 'copy'
}

function onEditorDrop(event: DragEvent) {
  isDraggingField.value = false
  const fieldName = event.dataTransfer?.getData('text/x-field')
  if (!fieldName) return

  const isMove = event.dataTransfer?.getData('text/x-chip-move') === '1'
  const sourceChip = isMove ? _draggedChipEl : null
  _draggedChipEl = null

  // Place caret at exact drop coordinates
  let range: Range | null = null
  if ((document as any).caretRangeFromPoint) {
    range = (document as any).caretRangeFromPoint(event.clientX, event.clientY)
  } else if ((document as any).caretPositionFromPoint) {
    const pos = (document as any).caretPositionFromPoint(event.clientX, event.clientY)
    if (pos) {
      range = document.createRange()
      range.setStart(pos.offsetNode, pos.offset)
    }
  }

  // Don't allow dropping onto itself
  if (sourceChip && range && sourceChip.contains(range.startContainer)) return

  // Insert new chip at drop position first, then remove source
  if (range) {
    const sel = window.getSelection()!
    sel.removeAllRanges()
    sel.addRange(range)
  }
  insertField(fieldName)

  // Remove the original chip (it was a move, not a copy)
  if (sourceChip && sourceChip.parentNode) {
    // Also clean up any trailing &nbsp; that was inserted alongside it
    const next = sourceChip.nextSibling
    sourceChip.remove()
    if (next && next.nodeType === Node.TEXT_NODE && next.textContent === '\u00a0') {
      next.remove()
    }
    onEditorInput()
  }
}

function insertField(fieldName: string) {
  showFieldPicker.value = false
  ac.value.show = false
  recentFields.value = [fieldName, ...recentFields.value.filter(f => f !== fieldName)].slice(0, 15)
  editorEl.value?.focus()
  const color = selectedActorIdx.value !== null && selectedActorIdx.value >= 0 && selectedActorIdx.value < actors.value.length
    ? actorColor(actors.value[selectedActorIdx.value].type, selectedActorIdx.value)
    : '#b45309'
  const html = `<span class="tmpl-field" contenteditable="false" draggable="true" data-field="${fieldName}" style="display:inline-block;vertical-align:baseline;font-family:monospace;font-size:11px;line-height:1.4;background:${color}18;color:${color};border:1px solid ${color}44;padding:0 6px;border-radius:4px;margin:0 1px;cursor:grab;white-space:nowrap;">{&thinsp;{&thinsp;${fieldName}&thinsp;}&thinsp;}</span>`
  document.execCommand('insertHTML', false, html)
  onEditorInput()
}

// ── HTML builder ──────────────────────────────────────────────────────────
interface DocxParagraph {
  style: string
  text: string
  font_size_pt?: number
  font_family?: string
  bold?: boolean
  italic?: boolean
  color?: string
  text_align?: string
}

function buildHtmlFromParagraphs(paras: DocxParagraph[]): string {
  return paras.map(p => {
    const s    = (p.style || '').toLowerCase()
    const text = p.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    const highlighted = text.replace(/\{\{\s*(.+?)\s*\}\}/g, (_, field) =>
      `<span class="tmpl-field" contenteditable="false" data-field="${field}" style="display:inline-block;vertical-align:baseline;font-family:monospace;font-size:11px;line-height:1.4;background:#fffbeb;color:#b45309;border:1px solid #fcd34d;padding:0 6px;border-radius:4px;margin:0 1px;white-space:nowrap;cursor:default;">{{ ${field} }}</span>`
    )
    // Build inline style from DOCX run-level formatting
    const css: string[] = []
    if (p.font_size_pt) css.push(`font-size:${p.font_size_pt}pt`)
    if (p.font_family)  css.push(`font-family:${p.font_family}`)
    if (p.bold)         css.push('font-weight:bold')
    if (p.italic)       css.push('font-style:italic')
    if (p.color)        css.push(`color:${p.color}`)
    if (p.text_align)   css.push(`text-align:${p.text_align}`)
    const styleAttr = css.length ? ` style="${css.join(';')}"` : ''

    if (s.includes('heading 1') || s.includes('title')) return `<h1${styleAttr}>${highlighted}</h1>`
    if (s.includes('heading 2')) return `<h2${styleAttr}>${highlighted}</h2>`
    if (s.includes('heading 3')) return `<h3${styleAttr}>${highlighted}</h3>`
    return `<p${styleAttr}>${highlighted}</p>`
  }).join('\n')
}

function copyField(fieldName: string) {
  navigator.clipboard?.writeText(`{{ ${fieldName} }}`).catch(() => {})
  showToast(`Copied {{ ${fieldName} }}`)
}

// ── Flash merge field chips in the editor ─────────────────────────────────
function flashFields(fieldNames: string[]) {
  if (!fieldNames.length) return
  nextTick(() => {
    const editorEl2 = document.querySelector('.document-editor')
    if (!editorEl2) return
    fieldNames.forEach(name => {
      editorEl2.querySelectorAll(`[data-field="${name}"]`).forEach(el => {
        el.classList.add('tmpl-field-flash')
        setTimeout(() => el.classList.remove('tmpl-field-flash'), 2000)
      })
    })
    // Scroll first match into view
    const first = editorEl2.querySelector(`[data-field="${fieldNames[0]}"]`)
    first?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

// ── Detected variable group helpers ───────────────────────────────────────
const ALL_GROUP_KEYS = ['landlord', 'property', 'tenant_1', 'tenant_2', 'tenant_3', 'lease_terms', 'other']

const visibleGroupKeys = computed(() => {
  const dv = template.value?.detected_variables
  if (!dv) return []
  return ALL_GROUP_KEYS.filter(key => {
    if (!dv[key] || dv[key].length === 0) return false
    if (key === 'tenant_2' && tenantCount.value < 2) return false
    if (key === 'tenant_3' && tenantCount.value < 3) return false
    return true
  })
})

function groupDisplayName(key: string): string {
  const map: Record<string, string> = {
    landlord: 'Landlord', property: 'Property',
    tenant_1: 'Tenant 1', tenant_2: 'Tenant 2', tenant_3: 'Tenant 3',
    lease_terms: 'Lease Terms', other: 'Other',
  }
  return map[key] ?? key
}

function groupChipClass(key: string): string {
  // Solid filled pill colors per group
  const map: Record<string, string> = {
    landlord:    'field-chip--navy',
    property:    'field-chip--emerald',
    tenant_1:    'field-chip--blue',
    tenant_2:    'field-chip--violet',
    tenant_3:    'field-chip--pink',
    lease_terms: 'field-chip--amber',
    other:       'field-chip--gray',
  }
  return map[key] ?? 'field-chip--gray'
}

// ── Chat ──────────────────────────────────────────────────────────────────
async function sendMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatThinking.value) return

  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatThinking.value = true
  scrollChat()

  try {
    const { data } = await api.post(`/leases/templates/${templateId.value}/ai-chat/`, {
      api_history: apiHistory.value,   // empty on first message; full history thereafter
      message: msg,
    })
    // Store updated history so next call skips re-sending the document
    if (data.api_history) apiHistory.value = data.api_history
    chatMessages.value.push({ role: 'assistant', content: data.reply })
    _saveChatHistory()   // persist chat + api_history to localStorage

    // Handle document_update (update_document / add_comment / insert_toc / renumber_sections)
    if (data.document_update?.html && editorEl.value) {
      editorEl.value.innerHTML = data.document_update.html
      editorHtml.value = data.document_update.html
      savedHtml.value  = data.document_update.html
      isDirty.value    = false
      if (template.value) template.value.content_html = data.document_update.html
      showToast(`Document updated: ${data.document_update.summary}`)
      // Refresh template so detected_variables reflect new content
      await loadTemplate()
    }

    // Handle field_highlight (highlight_fields tool)
    if (data.field_highlight?.field_names?.length) {
      flashFields(data.field_highlight.field_names)
      if (data.field_highlight.message) {
        showToast(data.field_highlight.message)
      }
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

function scrollChat() {
  nextTick(() => {
    if (chatScrollEl.value) chatScrollEl.value.scrollTop = chatScrollEl.value.scrollHeight
  })
}

// ── Actions ───────────────────────────────────────────────────────────────
const exportMenuOpen = ref(false)

function exportPDF() {
  if (!template.value) return
  api.get(`/leases/templates/${templateId.value}/export.pdf/`, { responseType: 'blob' })
    .then(({ data }) => {
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${template.value!.name || 'template'}.pdf`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 5000)
    })
    .catch(() => showToast('PDF export failed — save your content first'))
}

function generatePreview() {
  if (!template.value) return
  api.post('/leases/generate/', { template_id: templateId.value, context: {} }, { responseType: 'blob' })
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
    await api.patch(`/leases/templates/${templateId.value}/`, { is_active: true })
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

// ── Clause library ────────────────────────────────────────────────────────
const savedClauses      = ref<any[]>([])
const clausesLoading    = ref(false)
const clauseGenerating  = ref(false)
const clauseExtracting  = ref(false)
const clauseGenerateTopic = ref('')
const clauseCategory    = ref('')
const generatedOptions  = ref<any[]>([])

const clauseCategories = [
  { key: 'parties',    label: 'Parties' },
  { key: 'premises',   label: 'Premises' },
  { key: 'financial',  label: 'Financial' },
  { key: 'utilities',  label: 'Utilities' },
  { key: 'legal',      label: 'Legal / Compliance' },
  { key: 'signatures', label: 'Signatures' },
  { key: 'general',    label: 'General' },
]

async function loadClauses() {
  clausesLoading.value = true
  try {
    const params: Record<string, string> = {}
    if (clauseCategory.value) params.category = clauseCategory.value
    const { data } = await api.get('/leases/clauses/', { params })
    savedClauses.value = data.results ?? data
  } catch { /* ignore */ }
  finally { clausesLoading.value = false }
}

async function generateClauses() {
  const topic = clauseGenerateTopic.value.trim()
  if (!topic) return
  clauseGenerating.value = true
  try {
    const { data } = await api.post('/leases/clauses/generate/', {
      topic,
      category: clauseCategory.value || undefined,
      count: 3,
    })
    generatedOptions.value = data.options ?? []
  } catch { showToast('Generation failed') }
  finally { clauseGenerating.value = false }
}

async function saveGeneratedClause(opt: { title: string; category: string; html: string }) {
  try {
    await api.post('/leases/clauses/', {
      title: opt.title,
      category: opt.category || 'general',
      html: opt.html,
      source_template_id: templateId.value,
    })
    generatedOptions.value = generatedOptions.value.filter(o => o !== opt)
    insertClauseHtml(opt.html)
    await loadClauses()
    showToast('Clause saved & inserted')
  } catch { showToast('Save failed') }
}

function saveSelection() {
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed) { showToast('Select some text first'); return }
  const range = sel.getRangeAt(0)
  const div = document.createElement('div')
  div.appendChild(range.cloneContents())
  const html = div.innerHTML.trim()
  if (!html) { showToast('Nothing selected'); return }
  const title = prompt('Clause title?', sel.toString().slice(0, 60).trim())
  if (!title) return
  api.post('/leases/clauses/', {
    title,
    category: clauseCategory.value || 'general',
    html,
    source_template_id: templateId.value,
  })
    .then(() => { loadClauses(); showToast('Clause saved') })
    .catch(() => showToast('Save failed'))
}

async function insertClause(clause: { id: number; html: string }) {
  insertClauseHtml(clause.html)
  try { await api.post(`/leases/clauses/${clause.id}/use/`) } catch { /* ignore */ }
  await loadClauses()
}

function insertClauseHtml(html: string) {
  editorEl.value?.focus()
  document.execCommand('insertHTML', false, html)
  onEditorInput()
}

async function deleteClause(id: number) {
  if (!confirm('Delete this clause?')) return
  try {
    await api.delete(`/leases/clauses/${id}/`)
    savedClauses.value = savedClauses.value.filter(c => c.id !== id)
    showToast('Deleted')
  } catch { showToast('Delete failed') }
}

async function extractFromTemplate() {
  clauseExtracting.value = true
  try {
    const { data } = await api.post('/leases/clauses/extract/', { template_id: templateId.value })
    generatedOptions.value = data.clauses ?? []
    showToast(`Extracted ${generatedOptions.value.length} clause(s) from "${data.template_name}"`)
  } catch { showToast('Extraction failed') }
  finally { clauseExtracting.value = false }
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

/* In-document merge field chips */
.document-editor :deep(span[data-merge-field]),
.document-editor :deep(span[data-field]) {
  display: inline-block;
  vertical-align: baseline;
  font-size: 0.72rem;
  font-family: ui-monospace, monospace;
  font-weight: 500;
  line-height: 1.4;
  padding: 0 6px;
  border-radius: 4px;
  white-space: nowrap;
  user-select: none;
  margin: 0 1px;
}

/* Page break — simulates the gap between two A4 sheets.
   Uses a pseudo-element that bleeds outside the white card via
   position:absolute so it never affects content layout width. */
.document-editor :deep([data-page-break]) {
  display: block;
  height: 0;          /* takes no space in content flow */
  position: relative;
  margin: 0;
  cursor: default;
  user-select: none;
  pointer-events: none;
}
/* Full-bleed gray band — grows left/right beyond padding via absolute pos */
.document-editor :deep([data-page-break])::before {
  content: '— page break —';
  position: absolute;
  top: 0;
  left: -3.5rem;   /* px-14 = 3.5rem */
  right: -3.5rem;
  height: 44px;
  margin-top: -22px;   /* center vertically around the zero-height div */
  background: #e8eaed;
  border-top: 1px solid #c8cdd5;
  border-bottom: 1px solid #c8cdd5;
  box-shadow: 0 -3px 8px rgba(0,0,0,0.10), 0 3px 8px rgba(0,0,0,0.10);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: #9ca3af;
  font-family: ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0.12em;
  white-space: nowrap;
  z-index: 1;
}
/* Spacer paragraphs before/after keep cursor away from the break */
.document-editor :deep([data-page-break]) + p:empty,
.document-editor :deep(p:empty + [data-page-break]) {
  height: 1.5rem;
}

/* Page header overlay */
.page-header-overlay {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3rem;
  padding: 0 3.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  pointer-events: none;
  user-select: none;
  z-index: 2;
}
.page-header-left  { font-size: 9px; color: #6b7280; font-family: ui-sans-serif, system-ui; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
.page-header-right { font-size: 16px; font-weight: 800; color: #1e3a5f; font-family: Georgia, serif; letter-spacing: -0.5px; }

/* Page footer overlay */
.page-footer-overlay {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2.8rem;
  padding: 0 3.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #e5e7eb;
  background: #fff;
  pointer-events: none;
  user-select: none;
  z-index: 2;
}
.page-footer-left  { font-size: 8px; color: #9ca3af; font-family: ui-sans-serif, system-ui; }
.page-footer-right { font-size: 8px; color: #9ca3af; font-family: ui-sans-serif, system-ui; }

/* Page number overlay (rendered outside contenteditable) */
.page-number-overlay {
  position: absolute;
  right: 2.5rem;
  font-size: 10px;
  color: #9ca3af;
  font-family: ui-sans-serif, system-ui, sans-serif;
  pointer-events: none;
  user-select: none;
}

/* Comment block */
.document-editor :deep(div[data-block-comment]) {
  background: #fefce8;
  border-left: 3px solid #eab308;
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 0 6px 6px 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 12px;
  color: #713f12;
  font-style: italic;
}
</style>

<style>
/* ── Field chip pill (shared across all chip locations) ─────────────────── */
.field-chip {
  display: inline-flex;
  align-items: center;
  font-family: ui-monospace, monospace;
  font-size: 10px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 9999px;
  white-space: nowrap;
  cursor: pointer;
  transition: filter 0.12s, transform 0.1s;
  line-height: 1.4;
  /* default: teal */
  background: #0d9488;
  color: #fff;
}
.field-chip:hover { filter: brightness(1.12); transform: translateY(-1px); }
.field-chip:active { transform: scale(0.96); }

/* Colour variants */
.field-chip--lease   { background: #0d9488; color: #fff; }   /* teal    */
.field-chip--navy    { background: #1e3a5f; color: #fff; }   /* navy    */
.field-chip--emerald { background: #059669; color: #fff; }   /* emerald */
.field-chip--blue    { background: #2563eb; color: #fff; }   /* blue    */
.field-chip--violet  { background: #7c3aed; color: #fff; }   /* violet  */
.field-chip--pink    { background: #db2777; color: #fff; }   /* pink    */
.field-chip--amber   { background: #d97706; color: #fff; }   /* amber   */
.field-chip--gray    { background: #6b7280; color: #fff; }   /* gray    */

/* Flash highlight animation for merge field chips */
@keyframes chipFlash {
  0%, 100% { background: #fffbeb; border-color: #fcd34d; }
  30%, 70% { background: #fef08a; border-color: #facc15; box-shadow: 0 0 0 3px #fde047; }
}
.tmpl-field-flash {
  animation: chipFlash 2s ease-in-out;
}
</style>
