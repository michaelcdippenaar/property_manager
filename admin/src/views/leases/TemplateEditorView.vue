<template>
  <div class="flex flex-col h-[calc(100vh-4rem)] -m-6 bg-white overflow-hidden">

    <!-- ── Header (DocuSeal-style) ──────────────────────────────────────── -->
    <div class="flex items-center h-14 px-4 border-b border-gray-200 bg-white flex-shrink-0 gap-4">
      <div class="flex items-center gap-3 min-w-0 w-56 flex-shrink-0">
        <button @click="goBack" class="p-1.5 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0">
          <ChevronLeft :size="18" />
        </button>
        <FileSignature :size="15" class="text-navy flex-shrink-0" />
        <span class="font-semibold text-gray-900 text-sm truncate">{{ template?.name ?? 'Template Editor' }}</span>
      </div>

      <!-- Step indicator -->
      <div class="flex items-center gap-3 mx-auto">
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-full bg-navy flex items-center justify-center text-white text-micro font-bold">1</div>
          <span class="text-xs font-semibold text-navy">Add &amp; Prepare Fields</span>
        </div>
        <div class="flex items-center gap-1">
          <div v-for="i in 5" :key="i" class="w-1 h-1 rounded-full" :class="i <= 3 ? 'bg-navy' : 'bg-gray-300'" />
        </div>
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-full border-2 border-gray-300 flex items-center justify-center text-gray-400 text-micro font-bold">2</div>
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
            <button
              class="flex items-center gap-1.5 px-3 py-1.5 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="pdfExporting"
              @click="exportPDF"
            >
              <Loader2 v-if="pdfExporting" :size="12" class="animate-spin" />
              <Download v-else :size="12" />
              {{ pdfExporting ? 'Preparing…' : 'Export PDF' }}
            </button>
            <button class="px-1.5 py-1.5 border-l border-gray-300 hover:bg-gray-50 transition-colors" @click="exportMenuOpen = !exportMenuOpen">
              <ChevronDown :size="12" />
            </button>
          </div>
          <div v-if="exportMenuOpen" class="absolute right-0 top-full mt-1 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
            <button class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2" @click="exportPDF(); exportMenuOpen = false">
              <Download :size="11" class="text-danger-500" /> Export as PDF
            </button>
            <button class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2" @click="generatePreview(); exportMenuOpen = false">
              <Download :size="11" class="text-info-500" /> Export as DOCX
            </button>
            <div class="border-t border-gray-100 my-1" />
            <button class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2" @click="openDuplicateModal(); exportMenuOpen = false">
              <Copy :size="11" class="text-success-600" /> Save as New Template
            </button>
          </div>
        </div>
        <button
          class="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"
          @click="router.push('/leases/build')"
        >
          <Hammer :size="12" />
          Build Lease
        </button>
      </div>
    </div>

    <!-- ── Body ─────────────────────────────────────────────────────────── -->
    <div class="flex-1 flex overflow-hidden min-h-0 min-w-0">

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
            <span v-if="template" class="text-micro text-gray-400 truncate">— {{ template.name }}</span>
          </template>
        </div>
        <template v-if="!chatCollapsed">
          <!-- Capabilities disclosure -->
          <div class="px-3 py-2 border-b border-gray-100">
            <button @click="showCapabilities = !showCapabilities"
              class="flex items-center gap-1 text-gray-400 hover:text-gray-600 w-full"
              style="font-size: 10px;">
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
              <div>
                <div class="text-gray-400 mb-0.5" style="font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px;">External</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="skill in externalSkills" :key="skill"
                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-gray-50 border border-gray-200 text-gray-500"
                    style="font-size: 9px;">
                    <ExternalLink :size="8" /> {{ skill }}
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
              <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-micro font-bold mt-0.5"
                :class="msg.role === 'assistant' ? 'bg-navy/10 text-navy' : 'bg-gray-200 text-gray-600'">
                {{ msg.role === 'assistant' ? 'AI' : 'Me' }}
              </div>
              <div class="max-w-[85%]">
                <div class="rounded-2xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap"
                  :class="msg.role === 'user' ? 'bg-navy text-white rounded-tr-sm' : 'bg-gray-100 text-gray-800 rounded-tl-sm'">
                  {{ msg.content }}
                </div>
                <div v-if="msg.tools_used?.length" class="flex flex-wrap gap-1 mt-1 ml-0.5">
                  <span
                    v-for="(tool, ti) in msg.tools_used" :key="ti"
                    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md"
                    :class="(tool.type === 'skill' || isSkillTool(tool.name))
                      ? 'bg-purple-50 border border-purple-200 text-purple-700'
                      : 'bg-warning-50 border border-warning-100 text-warning-700'"
                    style="font-size: 9px; line-height: 1.2;"
                  >
                    <component :is="(tool.type === 'skill' || isSkillTool(tool.name)) ? Zap : Wrench" :size="8" class="flex-shrink-0" />
                    <span class="font-medium">{{ tool.name }}</span>
                    <span :class="(tool.type === 'skill' || isSkillTool(tool.name)) ? 'text-purple-500' : 'text-warning-500'">{{ tool.detail }}</span>
                  </span>
                </div>
              </div>
            </div>
            <div v-if="chatThinking" class="flex gap-2">
              <div class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-micro font-bold bg-navy/10 text-navy mt-0.5">AI</div>
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

      <!-- ── RIGHT PANEL: Field Palette (~270px, collapsible) ─────────────
           order-last pushes this after the center column in flex layout     -->
      <div
        class="flex-shrink-0 border-l border-gray-200 flex flex-col bg-white order-last transition-all duration-200"
        :style="{ width: rightCollapsed ? '44px' : '270px' }"
      >

        <!-- Right panel header with collapse toggle -->
        <div class="flex items-center gap-2 px-3 py-2 border-b border-gray-200 flex-shrink-0">
          <button
            class="p-1 rounded hover:bg-gray-100 text-gray-500 flex-shrink-0"
            @click="rightCollapsed = !rightCollapsed"
            :title="rightCollapsed ? 'Open field palette' : 'Collapse'"
          >
            <component :is="rightCollapsed ? ChevronsLeft : ChevronsRight" :size="14" />
          </button>
          <span v-if="!rightCollapsed" class="text-xs font-semibold text-gray-800 whitespace-nowrap">Field Palette</span>
        </div>

        <!-- ── Field palette (scrollable) ── -->
        <div v-if="!rightCollapsed" class="flex-1 overflow-y-auto min-h-0">

          <!-- ── Recipient selector ── -->
          <div class="px-3 py-2.5 border-b border-gray-100 space-y-2">
            <div class="text-micro font-semibold text-gray-500 uppercase tracking-wide">Recipient</div>

            <!-- Active recipient pill -->
            <div
              class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs font-medium"
              :style="{
                borderColor: selectedColor + '44',
                backgroundColor: selectedColor + '08',
                color: selectedColor
              }"
            >
              <span class="w-5 h-5 rounded-full flex items-center justify-center text-white text-micro font-bold flex-shrink-0"
                :style="{ backgroundColor: selectedColor }">
                {{ selectedActorIdx === -1 ? 'A' : selectedActorIdx !== null && selectedActorIdx < actors.length ? actorAvatar(actors[selectedActorIdx], selectedActorIdx) : '?' }}
              </span>
              <span class="truncate flex-1">{{ selectedActorLabel }}</span>
            </div>

            <!-- Actor list -->
            <div class="space-y-1">
              <!-- Me (Agent) -->
              <button
                class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors"
                :class="selectedActorIdx === -1 ? 'bg-navy/10 text-navy font-semibold' : 'text-gray-600 hover:bg-gray-50'"
                @click="selectedActorIdx = -1"
              >
                <span class="w-4 h-4 rounded-full bg-navy/80 flex items-center justify-center text-white flex-shrink-0" style="font-size: 8px; font-weight: 700;">A</span>
                <span>Me (Agent)</span>
              </button>

              <!-- Actors -->
              <button
                v-for="(actor, ai) in actors" :key="ai"
                class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors group"
                :class="selectedActorIdx === ai ? 'font-semibold' : 'text-gray-600 hover:bg-gray-50'"
                :style="selectedActorIdx === ai ? { backgroundColor: actorColor(actor.type, ai) + '15', color: actorColor(actor.type, ai) } : {}"
                @click="selectedActorIdx = ai"
              >
                <span class="w-4 h-4 rounded-full flex items-center justify-center text-white flex-shrink-0"
                  :style="{ backgroundColor: actorColor(actor.type, ai) }" style="font-size: 8px; font-weight: 700;">
                  {{ actorAvatar(actor, ai) }}
                </span>
                <span class="flex-1 text-left truncate">{{ actor.label }}</span>
                <button
                  class="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-danger-100 text-gray-400 hover:text-danger-500 transition-opacity"
                  @click.stop="removeActor(ai)"
                  title="Remove"
                >
                  <X :size="10" />
                </button>
              </button>
            </div>

            <!-- Add actor buttons -->
            <div class="flex gap-1">
              <button
                v-for="at in actorTypes" :key="at.key"
                class="flex-1 flex items-center justify-center gap-1 px-1.5 py-1.5 text-micro font-medium rounded-lg border border-dashed transition-colors"
                :class="at.btnClass"
                @click="addActor(at.key)"
                :title="`Add ${at.label}`"
              >
                <component :is="at.icon" :size="10" />
                <span>{{ at.label }}</span>
              </button>
            </div>
          </div>

          <!-- Personal Data -->
          <div class="px-4 py-2.5 text-micro font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100">
            Personal Data
          </div>
          <div class="p-2 grid grid-cols-2 gap-1.5">
            <button
              v-for="pd in personalDataFields" :key="pd.key"
              class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border text-xs font-medium text-left transition-all border-gray-200 text-gray-700 cursor-pointer"
              :style="selectedActorIdx !== null ? { borderColor: selectedColor + '44', backgroundColor: selectedColor + '08' } : {}"
              @mousedown.prevent="startFieldTypePlace(pd)"
              @mouseenter="($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedColor + '66')"
              @mouseleave="($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedActorIdx !== null ? selectedColor + '44' : '')"
              @click="insertFieldType(pd)"
              :title="`Insert ${pd.label}`"
            >
              <component :is="pd.icon" :size="13" class="flex-shrink-0 transition-colors"
                :style="{ color: selectedActorIdx !== null ? selectedColor : '#9ca3af' }" />
              <span class="truncate" :style="selectedActorIdx !== null ? { color: selectedColor } : {}">{{ pd.label }}</span>
            </button>
          </div>

          <!-- Signing Fields -->
          <div class="px-4 py-2.5 text-micro font-semibold text-gray-500 uppercase tracking-wide border-t-2 border-b border-gray-200">
            Signing
          </div>
          <div class="p-2 grid grid-cols-2 gap-1.5">
            <button
              v-for="ft in allFieldTypes" :key="ft.key"
              class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border text-xs font-medium text-left transition-all border-gray-200 text-gray-700 cursor-pointer"
              @mousedown.prevent="startFieldTypePlace(ft)"
              @mouseenter="($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedColor + '66')"
              @mouseleave="($event.currentTarget as HTMLElement).style.removeProperty('border-color')"
              @click="insertFieldType(ft)"
              :title="`Insert ${ft.label}`"
            >
              <span class="truncate">{{ ft.label }}</span>
            </button>
          </div>

          <!-- Lease Fields (grouped) -->
          <div v-for="group in leaseFieldGroups" :key="group.label">
            <div class="px-4 py-2.5 text-micro font-semibold text-gray-500 uppercase tracking-wide border-t border-b border-gray-100">
              {{ group.label }}
            </div>
            <div class="p-2 grid grid-cols-2 gap-1.5">
              <button
                v-for="f in group.fields" :key="f.key"
                class="flex items-center gap-2 px-2.5 py-2.5 rounded-lg border text-xs font-medium text-left transition-all border-gray-200 text-gray-700 cursor-pointer"
                @mousedown.prevent="startFieldPlace(f.key)"
                @mouseenter="($event.currentTarget as HTMLElement).style.setProperty('border-color', selectedColor + '66')"
                @mouseleave="($event.currentTarget as HTMLElement).style.removeProperty('border-color')"
                @click="insertField(f.key)"
                :title="`Insert {{ ${f.key} }}`"
              >
                <span class="truncate">{{ f.label }}</span>
              </button>
            </div>
          </div>

          <!-- Clauses toggle -->
          <div class="border-t border-gray-100 p-2">
            <button
              class="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-dashed transition-colors"
              :class="showClausesSection ? 'border-navy/30 text-navy bg-navy/5' : 'border-gray-300 text-gray-500 hover:border-navy/30 hover:text-navy'"
              @click="showClausesSection = !showClausesSection; if(showClausesSection) loadClauses()"
            >
              <Bookmark :size="12" />
              {{ showClausesSection ? 'Hide Clauses' : 'Clause Library' }}
            </button>
          </div>

        </div>

        <!-- ── CLAUSES SECTION (collapsible) ── -->
        <div v-if="showClausesSection && !rightCollapsed" class="flex flex-col flex-shrink-0 border-t border-gray-200 max-h-[50%] overflow-hidden">

          <!-- Clause toolbar -->
          <div class="px-2 pt-2 pb-1.5 space-y-1.5 border-b border-gray-100 flex-shrink-0">
            <!-- Generate row -->
            <div class="flex gap-1">
              <input
                v-model="clauseGenerateTopic"
                class="flex-1 text-micro border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-navy/30"
                placeholder="Topic e.g. POPIA consent…"
                @keydown.enter.prevent="generateClauses"
              />
              <button
                class="px-2.5 py-1.5 text-micro font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 flex items-center gap-1 flex-shrink-0 disabled:opacity-60"
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
                class="flex-1 text-micro border border-gray-200 rounded px-1.5 py-1 focus:outline-none bg-white"
                @change="loadClauses"
              >
                <option value="">All categories</option>
                <option v-for="c in clauseCategories" :key="c.key" :value="c.key">{{ c.label }}</option>
              </select>
              <button
                class="text-micro px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 text-gray-600 flex items-center gap-1 flex-shrink-0"
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
              class="w-full text-micro border border-dashed border-gray-300 rounded-lg py-1.5 text-gray-500 hover:border-navy/40 hover:text-navy/70 transition-colors flex items-center justify-center gap-1"
              @click="saveSelection"
            >
              <Bookmark :size="10" /> Save selected text as clause
            </button>
          </div>

          <!-- Generated options (shown before saving) -->
          <div v-if="generatedOptions.length" class="px-2 py-2 space-y-2 border-b border-warning-100 bg-warning-50/40 flex-shrink-0">
            <div class="text-micro font-semibold text-warning-700 uppercase px-1">Generated — click to save &amp; insert</div>
            <div
              v-for="(opt, i) in generatedOptions" :key="i"
              class="bg-white border border-warning-100 rounded-lg p-2 cursor-pointer hover:border-warning-500 transition-colors"
              @click="saveGeneratedClause(opt)"
            >
              <div class="flex items-center justify-between gap-1 mb-1">
                <span class="text-micro font-semibold text-gray-800 leading-snug">{{ opt.title }}</span>
                <span class="text-micro bg-warning-100 text-warning-700 px-1.5 py-0.5 rounded flex-shrink-0">{{ opt.category }}</span>
              </div>
              <div class="text-micro text-gray-500 line-clamp-2 leading-relaxed" v-html="opt.html" />
            </div>
            <button class="w-full text-micro text-gray-400 hover:text-gray-600 py-0.5" @click="generatedOptions = []">Clear</button>
          </div>

          <!-- Saved clauses list -->
          <div class="flex-1 overflow-y-auto">
            <div v-if="clausesLoading" class="p-3 space-y-2 animate-pulse">
              <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 rounded-lg" />
            </div>
            <div v-else-if="!savedClauses.length" class="p-4 text-center text-micro text-gray-400">
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
                    <div class="text-micro font-semibold text-gray-800 leading-snug truncate">{{ clause.title }}</div>
                    <div class="flex items-center gap-1.5 mt-0.5">
                      <span class="text-micro bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{{ clause.category }}</span>
                      <span v-if="clause.use_count" class="text-micro text-gray-400">used {{ clause.use_count }}×</span>
                      <span v-if="clause.source_template_names?.length" class="text-micro text-gray-400 truncate">from {{ clause.source_template_names.join(', ') }}</span>
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
                      class="p-1 rounded text-gray-300 hover:text-danger-400 opacity-0 group-hover:opacity-100 transition-all"
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
        <div v-if="!rightCollapsed" class="border-t border-gray-200 flex-shrink-0">
          <div class="flex items-center justify-between px-3 py-2">
            <span class="text-micro font-semibold text-gray-500 uppercase tracking-wide">Detected Variables</span>
            <div class="flex items-center gap-2">
              <div class="flex items-center gap-1">
                <span class="text-micro text-gray-400">Tenants:</span>
                <select v-model="tenantCount" class="text-micro border border-gray-200 rounded px-0.5 py-0.5 bg-white focus:outline-none">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                </select>
              </div>
              <div class="flex items-center gap-1">
                <span class="text-micro text-gray-400">Occupants:</span>
                <select v-model="occupantCount" class="text-micro border border-gray-200 rounded px-0.5 py-0.5 bg-white focus:outline-none">
                  <option :value="0">0</option>
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                  <option :value="4">4</option>
                </select>
              </div>
            </div>
          </div>
          <div class="max-h-36 overflow-y-auto px-2 pb-2">
            <div v-if="template?.detected_variables && Object.keys(template.detected_variables).length" class="space-y-1.5">
              <details v-for="groupKey in visibleGroupKeys" :key="groupKey" open class="group/acc">
                <summary class="flex items-center justify-between cursor-pointer list-none text-micro font-semibold text-gray-500 py-0.5 hover:text-gray-800">
                  <span>{{ groupDisplayName(groupKey) }}</span>
                  <span class="text-gray-300 font-normal">{{ (template.detected_variables![groupKey] || []).length }}</span>
                </summary>
                <div class="flex flex-wrap gap-1 pl-1 pb-1">
                  <span
                    v-for="field in (template.detected_variables![groupKey] || [])" :key="field"
                    class="field-chip"
                    :class="groupChipClass(groupKey)"
                    @mousedown.prevent="startFieldPlace(field)"
                    :title="`Click or drag to insert {{ ${field} }}`"
                  >{{ field }}</span>
                </div>
              </details>
            </div>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="f in discoveredFields" :key="f"
                class="field-chip field-chip--lease"
                @mousedown.prevent="startFieldPlace(f)"
                :title="`Click or drag to insert {{ ${f} }}`">{{ f }}</span>
              <div v-if="!discoveredFields.length" class="text-micro text-gray-300 italic">No fields detected.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── CENTER: Document canvas ──────────────────────────────────────── -->
      <div class="flex-1 flex flex-col overflow-hidden min-h-0 min-w-0 bg-gray-100">

        <!-- Toolbar — hidden for read-only PDF templates -->
        <div v-if="!isPdfTemplate" class="border-b border-gray-300 bg-white flex-shrink-0">
          <!-- Collapse toggle -->
          <div v-if="toolbarCollapsed" class="flex items-center px-3 py-1">
            <button class="text-micro text-gray-400 hover:text-navy transition-colors" @click="toolbarCollapsed = false">
              Show toolbar ▼
            </button>
            <div class="ml-auto flex items-center gap-2">
              <span v-if="isDirty" class="flex items-center gap-1.5 text-micro text-warning-600">
                <span class="w-1.5 h-1.5 rounded-full bg-warning-500" /> Unsaved
              </span>
              <button class="toolbar-btn" @click="execCmd('undo')" title="Undo"><RotateCcw :size="13" /></button>
              <button class="toolbar-btn" @click="execCmd('redo')" title="Redo"><RotateCw :size="13" /></button>
            </div>
          </div>
          <!-- Row 1: history, paragraph style, font, size -->
          <div v-show="!toolbarCollapsed" class="flex items-center gap-0.5 px-3 py-1.5 border-b border-gray-100 flex-wrap">
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
              <span v-if="isDirty" class="flex items-center gap-1.5 text-micro text-warning-600">
                <span class="w-1.5 h-1.5 rounded-full bg-warning-500" /> Unsaved
              </span>
              <button class="text-micro text-gray-400 hover:text-navy transition-colors" @click="toolbarCollapsed = true" title="Collapse toolbar">▲</button>
            </div>
          </div>
          <!-- Row 2: formatting, lists, align, indent, color, table, field -->
          <div v-show="!toolbarCollapsed" class="flex items-center gap-0.5 px-3 py-1 flex-wrap">
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
                <div class="text-micro text-gray-400 mb-1">Cell / highlight color</div>
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
                class="toolbar-btn flex items-center gap-1 font-semibold text-micro"
                :class="headingStylesOpen ? 'text-navy bg-navy/10' : ''"
                @mousedown.prevent="headingStylesOpen = !headingStylesOpen; colorPickerOpen = false; bgColorPickerOpen = false"
                title="Heading styles"
              >H<span class="text-micro text-gray-400">1–3</span></button>
              <!-- Panel -->
              <div v-if="headingStylesOpen" class="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl z-30 w-80 p-3">
                <div class="text-micro font-semibold text-gray-500 uppercase tracking-wide mb-2">Heading Styles</div>
                <div class="space-y-2">
                  <div v-for="lvl in headingLevels" :key="lvl.tag" class="flex items-center gap-2">
                    <!-- Level label (like TOC indent) -->
                    <span
                      class="w-8 text-micro font-bold flex-shrink-0 text-gray-600"
                      :style="{ marginLeft: lvl.indent + 'px' }"
                    >{{ lvl.label }}</span>
                    <!-- Font family -->
                    <select
                      v-model="lvl.fontFamily"
                      class="text-micro border border-gray-200 rounded px-1 py-0.5 focus:outline-none bg-white w-24 flex-shrink-0"
                    >
                      <option value="">Default</option>
                      <option v-for="f in fontFamilies" :key="f" :value="f">{{ f }}</option>
                    </select>
                    <!-- Font size -->
                    <select
                      v-model="lvl.fontSize"
                      class="text-micro border border-gray-200 rounded px-1 py-0.5 focus:outline-none bg-white w-14 flex-shrink-0"
                    >
                      <option value="">Auto</option>
                      <option v-for="s in [8,9,10,11,12,14,16,18,20,24,28,32,36]" :key="s" :value="String(s)">{{ s }}</option>
                    </select>
                    <!-- Bold -->
                    <button
                      class="w-6 h-6 rounded border text-micro font-bold flex-shrink-0 transition-colors"
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
                      class="ml-auto text-micro px-2 py-0.5 bg-navy text-white rounded hover:bg-navy/90 flex-shrink-0"
                      @click="applyHeadingStyle(lvl)"
                    >Apply</button>
                  </div>
                </div>
                <button class="mt-3 w-full text-micro py-1.5 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-semibold"
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
                class="flex items-center gap-1 px-2 py-1 text-xs text-warning-700 border border-warning-100 bg-warning-50 rounded hover:bg-warning-100 transition-colors font-medium"
                @click="showFieldPicker = !showFieldPicker"
              >
                <Braces :size="12" /> Insert field
              </button>
              <div v-if="showFieldPicker" class="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-2 max-h-48 overflow-y-auto">
                <div class="text-micro font-semibold text-gray-400 uppercase px-1 mb-1">Click to insert</div>
                <button
                  v-for="f in allFields" :key="f"
                  class="w-full text-left font-mono text-xs px-2 py-1 hover:bg-warning-50 rounded text-warning-700"
                  @mousedown.prevent="insertField(f)"
                >
                  &#123;&#123; {{ f }} &#125;&#125;
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Document page (scrollable) -->
        <div class="flex-1 overflow-y-auto py-8 px-4 min-h-0 bg-gray-100" @click="showFieldPicker = false; headingStylesOpen = false">
          <!-- Loading skeleton -->
          <div v-if="loadingPreview" class="max-w-[680px] mx-auto bg-white shadow-md px-14 py-12 min-h-[961px] space-y-3 animate-pulse">
            <div class="h-5 bg-gray-200 rounded w-1/3 mx-auto mb-6" />
            <div v-for="i in 8" :key="i" class="h-3 bg-gray-100 rounded" :class="i % 3 === 0 ? 'w-4/5' : i % 2 === 0 ? 'w-full' : 'w-11/12'" />
          </div>

          <!-- PDF viewer (read-only) -->
          <div v-if="!loadingPreview && isPdfTemplate && pdfUrl" class="flex flex-col gap-2 h-full">
            <div class="flex items-center gap-2 bg-warning-50 border border-warning-100 rounded-lg px-4 py-2.5 text-xs text-warning-700 flex-shrink-0">
              <span class="font-semibold">PDF template</span> — this document is read-only. To make it editable, convert it to a DOCX and re-upload.
            </div>
            <iframe
              :src="pdfUrl"
              class="w-full flex-1 bg-white shadow-md border-0 rounded"
              style="min-height: 800px;"
              title="Template PDF preview"
              data-clarity-mask="true"
            />
          </div>

          <!-- A4 document page -->
          <div class="relative max-w-[680px] mx-auto overflow-x-hidden" v-if="!loadingPreview && !isPdfTemplate">
            <div
              ref="editorEl"
              contenteditable="true"
              class="w-full bg-white shadow-md px-14 min-h-[1061px] focus:outline-none document-editor leading-relaxed relative"
              :class="{ 'ring-2 ring-navy/30': isDraggingField }"
              :style="{ paddingTop: showHeader ? '3.5rem' : '3rem', paddingBottom: '3rem' }"
              @input="onEditorInput"
              @keydown="onEditorKeydown"
              v-html="editorHtml"
            />
            <!-- Last-page footer overlay (auto-break divs handle intermediate page footers) -->
            <div
              v-if="showFooter"
              class="page-footer-bar"
              :style="{ bottom: '8px' }"
            >
              <span class="text-gray-400">{{ footerLeft }}</span>
              <span class="text-gray-500">Page {{ pageCount }} of {{ pageCount }}</span>
            </div>
            <!-- Page header overlay (non-editable, shown on every page) -->
            <div v-if="showHeader" class="page-header-overlay">
              <span class="page-header-left">{{ headerLeft }}</span>
              <span class="page-header-right">{{ headerRight }}</span>
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

          <div class="text-center text-micro text-gray-400 mt-3">Page {{ pageCount > 1 ? '1–' + pageCount : '1' }} of {{ pageCount }} · Click to edit · Select a recipient then click field types to insert</div>
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
            class="flex-1 py-1.5 text-micro font-semibold transition-colors"
            :class="ac.tab === tab ? 'text-teal-600 border-b-2 border-teal-500' : 'text-gray-400 hover:text-gray-600'"
            @click="ac.tab = tab; ac.selectedIdx = 0">{{ tab }}
          </button>
        </div>
        <div class="max-h-52 overflow-y-auto py-1">
          <div v-if="!acFields.length" class="px-3 py-2 text-micro text-gray-400 italic">No matches</div>
          <button
            v-for="(f, idx) in acFields" :key="f"
            class="w-full text-left px-3 py-1.5 text-micro font-mono transition-colors"
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

    <!-- Duplicate / Save As New Template modal -->
    <Teleport to="body">
      <div v-if="showDuplicateModal" class="fixed inset-0 z-[200] flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40" @click="showDuplicateModal = false" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 space-y-4">
          <div class="flex items-center gap-2">
            <Copy :size="16" class="text-navy" />
            <span class="font-semibold text-gray-900 text-sm">Save as New Template</span>
          </div>
          <p class="text-xs text-gray-500">
            Creates a copy of this template with all content, fields, headers and footers.
          </p>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">New Template Name</label>
            <input
              v-model="duplicateName"
              type="text"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-navy focus:ring-1 focus:ring-navy"
              placeholder="e.g. Standard Lease v2"
              @keydown.enter="duplicateTemplate"
            />
          </div>
          <div class="flex justify-end gap-2 pt-2">
            <button
              class="px-4 py-2 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
              @click="showDuplicateModal = false"
            >
              Cancel
            </button>
            <button
              class="px-4 py-2 text-xs font-semibold text-white bg-navy rounded-lg hover:bg-navy/90 disabled:opacity-50 flex items-center gap-1.5"
              :disabled="!duplicateName.trim() || duplicating"
              @click="duplicateTemplate"
            >
              <Loader2 v-if="duplicating" :size="12" class="animate-spin" />
              <Copy v-else :size="12" />
              {{ duplicating ? 'Creating…' : 'Create Template' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
export default { name: 'TemplateEditorView' }
</script>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onBeforeUnmount, nextTick, markRaw } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  X, FileSignature, FileText, Sparkles, Send, Download, Save, CheckCircle2,
  Braces, ChevronLeft, ChevronDown, Loader2, Bookmark, Plus,
  Bold, Italic, Underline, List, ListOrdered, AlignLeft, AlignCenter, AlignRight,
  IndentDecrease, IndentIncrease, Palette, PaintBucket, Table,
  RotateCcw, RotateCw,
  Users, User, UserCheck, Building2,
  Hash, Calendar, CheckSquare, Phone, Mail, Type, Pen, StickyNote,
  Scissors, FileDigit, LayoutTemplate, Hammer, Copy,
  ChevronsLeft, ChevronsRight, Wrench, Zap, ExternalLink, ChevronRight,
} from 'lucide-vue-next'
import api from '../../api'
import { useTemplateStore } from '../../stores/template'
import type { DocJson, DocField } from '../../stores/template'
import { usePageBreaks } from '../../composables/usePageBreaks'

const route = useRoute()
const router = useRouter()
const templateId = computed(() => Number(route.params.id))
const store = useTemplateStore()

function goBack() {
  router.push('/leases/templates')
}

// ── Template data (from Pinia store) ──────────────────────────────────────
const template = computed(() => store.template)
const preview  = computed(() => store.preview)
const loadingPreview = ref(true)

// ── Editor state ──────────────────────────────────────────────────────────
const editorEl  = ref<HTMLDivElement | null>(null)
const editorHtml = ref('')
const savedHtml  = ref('')

// ── Header / footer config ─────────────────────────────────────────────────
const headerLeft  = computed({ get: () => store.headerHtml, set: v => { store.headerHtml = v } })
const headerRight = ref('k.') // logo / brand top-right
const footerLeft  = computed({ get: () => store.footerHtml, set: v => { store.footerHtml = v } })
const showHeader  = ref(true)
const showFooter  = ref(true)
const headerFooterPanelOpen = ref(false)
const saving     = computed(() => store.saving)
const isDirty    = ref(false)
const showFieldPicker = ref(false)
const showPageNumbers = ref(false)

// Page breaks — shared composable
const { pageCount, schedule: schedulePageBreaks, isUpdating: isPageBreakUpdating, destroy: destroyPageBreaks } = usePageBreaks(editorEl, {
  footerLeft,
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
const chatCollapsed  = ref(window.innerWidth < 1200)
const toolbarCollapsed = ref(false)
const isDraggingField = ref(false)
// "Place mode": user mousedowns on a field button, moves over editor, releases to place
const placingField = ref<string | null>(null)
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
const rightCollapsed = ref(false)
const showClausesSection = ref(false)
const selectedActorIdx = ref<number | null>(null)   // -1 = Me, 0+ = actors[]
const fieldNotice    = ref('')
const actionFeedback = ref('')

// ── Tenant / occupant count for variable panel ────────────────────────────
const tenantCount   = ref(1)
const occupantCount = ref(1)

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
const chatMessages = ref<{ role: 'user' | 'assistant'; content: string; tools_used?: { name: string; detail: string; type?: string }[] }[]>([])
const showCapabilities = ref(false)
const editingTools = ['edit_lines', 'update_all', 'apply_formatting', 'insert_toc', 'renumber_sections', 'add_comment', 'highlight_fields']
const skillTools = ['check_rha_compliance', 'format_sa_standard']
const externalSkills = ['parse-lease-contract']
function isSkillTool(name: string): boolean { return skillTools.includes(name) }
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
    iconClass: 'text-info-500',
    btnClass: 'border-info-100 text-info-600 hover:border-info-500 hover:bg-info-50',
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
    return [
      'landlord_name', 'landlord_registration_no', 'landlord_vat_no',
      'landlord_representative', 'landlord_representative_id',
      'landlord_title', 'landlord_contact', 'landlord_email',
      'landlord_physical_address',
      'landlord_signature', 'landlord_initials', 'landlord_date_signed',
    ]
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
  { key: 'text',      label: 'Text',          icon: markRaw(StickyNote),  favorite: true },
  { key: 'number',    label: 'Number',        icon: markRaw(Hash),        favorite: false },
  { key: 'date',      label: 'Date',          icon: markRaw(Calendar),    favorite: true },
  { key: 'checkbox',  label: 'Checkbox',      icon: markRaw(CheckSquare), favorite: false },
]

const _defaultPersonalDataFields = [
  { key: 'name',      label: 'Full Name',    icon: markRaw(User) },
  { key: 'id',        label: 'ID Number',    icon: markRaw(Hash) },
  { key: 'phone',     label: 'Phone Number', icon: markRaw(Phone) },
  { key: 'email',     label: 'Email',        icon: markRaw(Mail) },
  { key: 'signature', label: 'Signature',    icon: markRaw(Pen),  block: true },
  { key: 'initials',  label: 'Initials',     icon: markRaw(Type), block: true },
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
]

const personalDataFields = computed(() => {
  if (selectedActorIdx.value !== null && selectedActorIdx.value >= 0 && selectedActorIdx.value < actors.value.length) {
    if (actors.value[selectedActorIdx.value].type === 'landlord') return _landlordDataFields
  }
  return _defaultPersonalDataFields
})

// Field keys that render as block placeholders (signature boxes) instead of inline chips
const BLOCK_FIELD_TYPES = new Set(['signature', 'initials'])

const visibleFieldTypes = computed(() => allFieldTypes)

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

const leaseFieldGroups = [
  {
    label: 'Property',
    fields: [
      { key: 'property_address', label: 'Address' },
      { key: 'unit_number', label: 'Unit Number' },
      { key: 'city', label: 'City' },
      { key: 'province', label: 'Province' },
    ],
  },
  {
    label: 'Lease Dates',
    fields: [
      { key: 'lease_start', label: 'Start Date' },
      { key: 'lease_end', label: 'End Date' },
      { key: 'notice_period_days', label: 'Notice Period' },
    ],
  },
  {
    label: 'Financial',
    fields: [
      { key: 'monthly_rent', label: 'Monthly Rent' },
      { key: 'deposit', label: 'Deposit' },
      { key: 'escalation_percent', label: 'Escalation %' },
      { key: 'payment_reference', label: 'Payment Ref' },
      { key: 'receipt_number', label: 'Receipt' },
    ],
  },
  {
    label: 'Rules & Utilities',
    fields: [
      { key: 'max_occupants', label: 'Max Occupants' },
      { key: 'pets_allowed', label: 'Pets Allowed' },
      { key: 'water_included', label: 'Water Included' },
      { key: 'electricity_prepaid', label: 'Electricity Prepaid' },
    ],
  },
  {
    label: 'Document',
    fields: [
      { key: 'page_number', label: 'Page Number' },
      { key: 'total_pages', label: 'Total Pages' },
    ],
  },
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
  await loadTemplate()
  await loadPreview()
  // Restore persisted chat history; if none, show greeting
  _loadChatHistory()
  if (!chatMessages.value.length) {
    chatMessages.value = [{
      role: 'assistant',
      content: template.value
        ? `Hi! I can help you work on "${template.value.name}".\n\nI can: edit clauses, format text, check RHA compliance, restructure to standard SA format, manage merge fields, and more.\n\nTap "Show capabilities" above to see all my tools and skills.`
        : 'Hi! I can help you improve this lease template. Tap "Show capabilities" above to see what I can do.',
    }]
  }
})

// Re-inject page breaks when KeepAlive reactivates the component
onActivated(() => {
  nextTick(() => schedulePageBreaks())
})

async function loadTemplate() {
  await store.loadTemplate(templateId.value)
}

async function loadPreview() {
  loadingPreview.value = true
  try {
    // If store already has content_html (from loadTemplate), use it directly
    if (store.document.html) {
      const sec38 = store.document.html.match(/38\.\d[^<]{0,60}/g)
      console.log('[LOAD] store.document fields:', store.document.fields.length, 'html length:', store.document.html.length)
      console.log('[LOAD] section 38 snippets:', sec38)
      editorHtml.value = decodeDocument(store.document)
      return
    }

    // Otherwise try the DOCX preview endpoint
    const data = await store.loadPreview(templateId.value)
    if (data?.paragraphs?.length) {
      // Build HTML from DOCX paragraphs and immediately persist
      const html = buildHtmlFromParagraphs(data.paragraphs)
      editorHtml.value = html
      store.updateHtml(html)
      isDirty.value = false
      await store.save()
    } else {
      // No content — starter template
      const name = template.value?.name ?? 'Lease Agreement'
      const starter = `<h1 style="text-align:center">${name}</h1><p><br></p><p>Start editing your lease template here. Use the toolbar above to format text, and the field palette on the right to insert merge fields.</p><p><br></p>`
      editorHtml.value = starter
      savedHtml.value  = ''
      isDirty.value    = true
    }
  } catch { /* ignore */ }
  finally {
    loadingPreview.value = false
    nextTick(() => {
      _hydrateFieldChips()
      savedHtml.value = getCleanHtml()
      isDirty.value = false
      schedulePageBreaks()
    })
  }
}

// Clear editor state when leaving so next visit loads fresh from DB
onBeforeUnmount(() => {
  destroyPageBreaks()
  document.removeEventListener('selectionchange', _trackSelection)
  store.$reset()
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

  // Enter → create a proper <p> instead of browser default <div>
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return

    const range = sel.getRangeAt(0)
    range.deleteContents()

    // Find the block-level parent element
    let block: HTMLElement | null = range.startContainer as HTMLElement
    if (block.nodeType === Node.TEXT_NODE) block = block.parentElement
    while (block && block !== editorEl.value && !['P','H1','H2','H3','H4','LI','DIV'].includes(block.tagName)) {
      block = block.parentElement
    }

    // Split the current block at the caret position
    if (block && block !== editorEl.value && block.parentNode) {
      // Extract content after caret into a new <p>
      const afterRange = document.createRange()
      afterRange.setStart(range.startContainer, range.startOffset)
      afterRange.setEndAfter(block.lastChild || block)
      const afterFrag = afterRange.extractContents()

      const newP = document.createElement('p')
      newP.appendChild(afterFrag)
      // Clean up: remove any stale <br> tags, then add one if truly empty
      if (!newP.textContent?.trim() && !newP.querySelector('[data-field], [data-merge-field]')) {
        newP.innerHTML = ''
        newP.appendChild(document.createElement('br'))
      }
      // Ensure the original block has content too
      if (!block.textContent?.trim() && !block.querySelector('[data-field], [data-merge-field]')) {
        block.innerHTML = ''
        block.appendChild(document.createElement('br'))
      }

      block.parentNode.insertBefore(newP, block.nextSibling)

      // Place caret at start of new paragraph
      const newRange = document.createRange()
      newRange.setStart(newP, 0)
      newRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(newRange)
    } else {
      // Fallback: insert a <p> with <br>
      const newP = document.createElement('p')
      newP.appendChild(document.createElement('br'))
      range.insertNode(newP)
      const newRange = document.createRange()
      newRange.setStart(newP, 0)
      newRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(newRange)
    }

    onEditorInput()
    return
  }

  // Backspace / Delete → remove merge field chips adjacent to caret
  if (e.key === 'Backspace' || e.key === 'Delete') {
    const sel = window.getSelection()
    if (sel && sel.isCollapsed && sel.rangeCount > 0) {
      const range = sel.getRangeAt(0)
      const container = range.startContainer
      const offset = range.startOffset

      let target: Element | null = null

      if (e.key === 'Backspace') {
        // Check element immediately before caret
        if (container.nodeType === Node.ELEMENT_NODE) {
          const child = (container as Element).childNodes[offset - 1]
          if (child instanceof HTMLElement && (child.hasAttribute('data-field') || child.hasAttribute('data-merge-field'))) {
            target = child
          }
        } else if (container.nodeType === Node.TEXT_NODE && offset === 0) {
          const prev = container.previousSibling
          if (prev instanceof HTMLElement && (prev.hasAttribute('data-field') || prev.hasAttribute('data-merge-field'))) {
            target = prev
          }
        }
      } else {
        // Delete key — check element immediately after caret
        if (container.nodeType === Node.ELEMENT_NODE) {
          const child = (container as Element).childNodes[offset]
          if (child instanceof HTMLElement && (child.hasAttribute('data-field') || child.hasAttribute('data-merge-field'))) {
            target = child
          }
        } else if (container.nodeType === Node.TEXT_NODE && offset === (container.textContent?.length ?? 0)) {
          const next = container.nextSibling
          if (next instanceof HTMLElement && (next.hasAttribute('data-field') || next.hasAttribute('data-merge-field'))) {
            target = next
          }
        }
      }

      if (target) {
        e.preventDefault()
        target.remove()
        onEditorInput()
        return
      }
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

// ── A4 page break injection (uses shared composable) ─────────────────────

// ── Document Encoder/Decoder (types from store) ──────────────────────────

function encodeDocument(): DocJson {
  if (!editorEl.value) return { v: 1, html: '', fields: [] }
  const clone = editorEl.value.cloneNode(true) as HTMLElement
  clone.querySelectorAll('[data-auto-page-break]').forEach(el => el.remove())

  const fields: DocField[] = []

  // Handle both data-field (editor-created) and data-merge-field (backend/legacy) elements
  clone.querySelectorAll('[data-field], [data-merge-field]').forEach(el => {
    const name = el.getAttribute('data-field') || el.getAttribute('data-merge-field') || ''
    const fieldTypeAttr = el.getAttribute('data-field-type')

    if (fieldTypeAttr) {
      // Block field — extract full metadata
      const s = (el as HTMLElement).style
      fields.push({
        name,
        type: fieldTypeAttr,
        party: (el as HTMLElement).dataset.party || _deriveParty(name),
        position: {
          top: s.top || '0px',
          left: s.left || '0px',
          width: s.width || '240px',
          height: s.height || '70px',
        },
      })
    } else {
      // Inline field — derive type from suffix
      const suffix = name.replace(/^.*_/, '').toLowerCase()
      const typeMap: Record<string, string> = {
        date: 'date', email: 'email', phone: 'text', number: 'number',
        signature: 'signature', initials: 'initials',
      }
      fields.push({ name, type: typeMap[suffix] || 'text' })
    }

    // Replace element with {{ref}} text marker
    el.replaceWith(document.createTextNode(`{{${name}}}`))
  })

  let html = clone.innerHTML.replace(/\u200B/g, '')

  // Deduplicate block fields — keep the one with a real position (not 0px,0px)
  const seen = new Map<string, number>()
  const deduped: DocField[] = []
  for (const f of fields) {
    const existing = seen.get(f.name)
    if (existing !== undefined && f.position) {
      const prev = deduped[existing]
      // Prefer the entry with a real position over the default 0px,0px
      if (prev.position?.top === '0px' && prev.position?.left === '0px' && f.position.top !== '0px') {
        deduped[existing] = f
      }
      continue  // skip duplicate
    }
    if (existing !== undefined) continue  // skip duplicate without position
    seen.set(f.name, deduped.length)
    deduped.push(f)
  }

  // Remove duplicate {{ref}} markers in HTML (keep only first occurrence per block field name)
  const blockNames = new Set(deduped.filter(f => f.position).map(f => f.name))
  for (const name of blockNames) {
    let first = true
    html = html.replace(new RegExp(`\\{\\{${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\}\\}`, 'g'), (m) => {
      if (first) { first = false; return m }
      return ''  // remove duplicates
    })
  }

  return { v: 1, html, fields: deduped }
}

function decodeDocument(doc: DocJson): string {
  // Build a lookup of block fields by name for position injection
  const blockFields = new Map<string, DocField>()
  for (const f of doc.fields) {
    if (f.position) blockFields.set(f.name, f)
  }

  // Track which block fields have already been placed (prevent duplicates)
  const placedBlocks = new Set<string>()

  // Replace {{ref}} markers with the right HTML elements
  return doc.html.replace(/\{\{([^}]+?)\}\}/g, (_, name) => {
    const trimmed = name.trim()
    const bf = blockFields.get(trimmed)
    if (bf) {
      // Only place each block field once — skip duplicates
      if (placedBlocks.has(trimmed)) return ''
      placedBlocks.add(trimmed)
      const p = bf.position!
      return `<div data-field="${trimmed}" data-field-type="${bf.type}" data-party="${bf.party || ''}" style="top:${p.top};left:${p.left};width:${p.width};height:${p.height}">${trimmed}</div>`
    }
    return `<span data-field="${trimmed}">${trimmed}</span>`
  })
}

// For dirty checking — quick encode without field extraction
function getCleanHtml(): string {
  return encodeDocument().html
}


// ── Editor ────────────────────────────────────────────────────────────────
let _dirtyTimer: ReturnType<typeof setTimeout> | null = null
function onEditorInput() {
  if (isPageBreakUpdating()) return  // skip events fired by page-break injection
  // Mark dirty immediately (cheap), but defer the full DOM-clone comparison
  if (!isDirty.value) isDirty.value = true
  if (_dirtyTimer) clearTimeout(_dirtyTimer)
  _dirtyTimer = setTimeout(() => {
    isDirty.value = getCleanHtml() !== savedHtml.value
  }, 500)
  _checkAutocomplete()
  schedulePageBreaks()
}

async function saveContent() {
  if (!editorEl.value) return
  // Update store with current editor state, then persist
  const doc = encodeDocument()
  // DEBUG: log what's being saved
  const sec38 = doc.html.match(/38\.\d[^<]{0,60}/g)
  console.log('[SAVE] encodeDocument fields:', doc.fields.length, 'html length:', doc.html.length)
  console.log('[SAVE] section 38 snippets:', sec38)
  store.updateDocument(doc)
  const result = await store.save()
  if (result) {
    savedHtml.value = getCleanHtml()
    isDirty.value = false
    // Build save message
    const parts: string[] = []
    const compliance = (result as any)?.compliance
    if (compliance) {
      const { pass_count, total_checks, sections_missing, clauses_missing } = compliance
      if (pass_count === total_checks) {
        parts.push(`RHA compliant (${pass_count}/${total_checks})`)
      } else {
        const missing = [...(sections_missing || []), ...(clauses_missing || [])]
        parts.push(`RHA: ${pass_count}/${total_checks}. Missing: ${missing.slice(0, 3).join(', ')}`)
      }
    }
    showToast(parts.length ? `Saved — ${parts.join(' | ')}` : 'Saved')
  } else {
    showToast('Save failed')
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

// ── Place-mode field insertion ────────────────────────────────────────────
// Mousedown on a field button → move mouse over editor → release to place chip.
// No HTML5 drag API — just mouse events + caretRangeFromPoint.

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

function _caretRangeFromXY(x: number, y: number): Range | null {
  if ((document as any).caretRangeFromPoint) {
    return (document as any).caretRangeFromPoint(x, y)
  }
  if ((document as any).caretPositionFromPoint) {
    const pos = (document as any).caretPositionFromPoint(x, y)
    if (pos) {
      const r = document.createRange()
      r.setStart(pos.offsetNode, pos.offset)
      return r
    }
  }
  return null
}

function startFieldPlace(fieldName: string) {
  placingField.value = fieldName
  isDraggingField.value = true
  document.body.style.cursor = 'crosshair'

  const fieldType = fieldName.replace(/^.*_/, '')
  const isBlock = BLOCK_FIELD_TYPES.has(fieldType)

  // Floating ghost that follows the cursor
  const ghost = document.createElement('div')
  ghost.textContent = isBlock ? `✍ ${fieldName}` : `{{ ${fieldName} }}`
  ghost.style.cssText = `
    position:fixed; z-index:9999; pointer-events:none;
    font:500 11px ui-monospace,monospace; white-space:nowrap;
    padding:${isBlock ? '8px 16px' : '2px 10px'};
    border-radius:${isBlock ? '6px' : '9999px'};
    border:${isBlock ? '2px dashed #fbbf24' : 'none'};
    background:${isBlock ? '#fffbeb' : '#0d9488'}; color:${isBlock ? '#b45309' : '#fff'};
    opacity:0.9; transform:translate(12px, 12px);
  `
  document.body.appendChild(ghost)

  function onMouseMove(e: MouseEvent) {
    ghost.style.left = `${e.clientX}px`
    ghost.style.top = `${e.clientY}px`

    // Show caret at mouse position for inline fields
    if (!isBlock && editorEl.value) {
      const rect = editorEl.value.getBoundingClientRect()
      if (e.clientX >= rect.left && e.clientX <= rect.right &&
          e.clientY >= rect.top && e.clientY <= rect.bottom) {
        const range = _caretRangeFromXY(e.clientX, e.clientY)
        if (range) {
          const sel = window.getSelection()!
          sel.removeAllRanges()
          sel.addRange(range)
        }
      }
    }
  }

  function onMouseUp(e: MouseEvent) {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    document.body.style.cursor = ''
    ghost.remove()
    isDraggingField.value = false

    const field = placingField.value
    placingField.value = null
    if (!field || !editorEl.value) return

    // Check if mouse is over the editor
    const rect = editorEl.value.getBoundingClientRect()
    if (e.clientX < rect.left || e.clientX > rect.right ||
        e.clientY < rect.top || e.clientY > rect.bottom) return

    // Resolve caret position and insert chip
    const range = _caretRangeFromXY(e.clientX, e.clientY)
    if (!range) return

    const chip = _createFieldChip(field)
    const isBlock = chip.tagName === 'DIV'

    if (isBlock) {
      // Block fields (signature/initials): absolutely positioned at mouse coordinates
      const editorRect = editorEl.value!.getBoundingClientRect()
      const scrollTop = editorEl.value!.scrollTop || 0
      const scrollLeft = editorEl.value!.scrollLeft || 0
      chip.style.top = `${e.clientY - editorRect.top + scrollTop}px`
      chip.style.left = `${e.clientX - editorRect.left + scrollLeft}px`
      editorEl.value!.appendChild(chip)
      _makeBlockDraggable(chip as HTMLDivElement)
    } else {
      // Inline fields: insert at exact caret position
      const zwsBefore = document.createTextNode('\u200B')
      const zwsAfter = document.createTextNode('\u200B')

      range.collapse(true)
      range.insertNode(zwsAfter)
      range.insertNode(chip)
      range.insertNode(zwsBefore)

      const afterRange = document.createRange()
      afterRange.setStartAfter(zwsAfter)
      afterRange.collapse(true)
      const sel = window.getSelection()!
      sel.removeAllRanges()
      sel.addRange(afterRange)
    }

    recentFields.value = [field, ...recentFields.value.filter(f => f !== field)].slice(0, 15)
    onEditorInput()
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function startFieldTypePlace(ft: { key: string }) {
  const fieldName = _fieldNameForType(ft)
  if (fieldName) startFieldPlace(fieldName)
}

/** Make a block field (signature/initials) movable, resizable, and deletable. */
function _makeBlockDraggable(box: HTMLDivElement) {
  // Add delete button
  const delBtn = document.createElement('button')
  delBtn.className = 'block-field-delete'
  delBtn.textContent = '✕'
  delBtn.contentEditable = 'false'
  delBtn.addEventListener('mousedown', (e) => {
    e.preventDefault()
    e.stopPropagation()
    box.remove()
    onEditorInput()
  })
  box.appendChild(delBtn)

  box.addEventListener('mousedown', (e: MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!editorEl.value) return

    const boxRect = box.getBoundingClientRect()
    const isResize = (e.clientX > boxRect.right - 16) && (e.clientY > boxRect.bottom - 16)

    const startX = e.clientX
    const startY = e.clientY

    if (isResize) {
      // Resize mode
      const startW = box.offsetWidth
      const startH = box.offsetHeight
      document.body.style.cursor = 'nwse-resize'

      function onMove(ev: MouseEvent) {
        box.style.width = `${Math.max(80, startW + (ev.clientX - startX))}px`
        box.style.height = `${Math.max(30, startH + (ev.clientY - startY))}px`
      }
      function onUp() {
        document.removeEventListener('mousemove', onMove)
        document.removeEventListener('mouseup', onUp)
        document.body.style.cursor = ''
        onEditorInput()
      }
      document.addEventListener('mousemove', onMove)
      document.addEventListener('mouseup', onUp)
    } else {
      // Move mode
      const startTop = parseInt(box.style.top || '0', 10)
      const startLeft = parseInt(box.style.left || '0', 10)

      function onMove(ev: MouseEvent) {
        box.style.top = `${startTop + (ev.clientY - startY)}px`
        box.style.left = `${startLeft + (ev.clientX - startX)}px`
      }
      function onUp() {
        document.removeEventListener('mousemove', onMove)
        document.removeEventListener('mouseup', onUp)
        onEditorInput()
      }
      document.addEventListener('mousemove', onMove)
      document.addEventListener('mouseup', onUp)
    }
  })
}

/** Build a minimal inline field chip: <span data-field="x">x</span>
 *  CSS handles all visual rendering via ::before pseudo-element. */
function _createFieldChip(fieldName: string): HTMLElement {
  // Detect if this is a block-type field (signature, initials)
  const fieldType = fieldName.replace(/^.*_/, '')  // e.g. tenant_1_signature → signature
  if (BLOCK_FIELD_TYPES.has(fieldType)) {
    return _createBlockFieldChip(fieldName, fieldType)
  }
  const chip = document.createElement('span')
  chip.contentEditable = 'false'
  chip.dataset.field = fieldName
  chip.dataset.party = _deriveFieldParty(fieldName)
  chip.textContent = fieldName
  // Click to select the chip so Backspace/Delete removes it
  chip.addEventListener('click', (e) => {
    e.stopPropagation()
    const sel = window.getSelection()
    if (sel) {
      const r = document.createRange()
      r.selectNode(chip)
      sel.removeAllRanges()
      sel.addRange(r)
    }
  })
  return chip
}

/** Build an absolutely-positioned field placeholder (signature/initials box).
 *  Position is set via style.top / style.left relative to the editor. */
function _deriveParty(fieldName: string): string {
  // "landlord_signature" → "Landlord", "tenant_initials" → "Tenant", "witness_signature" → "Witness"
  const prefix = fieldName.replace(/_(signature|initials)$/i, '')
  return prefix.charAt(0).toUpperCase() + prefix.slice(1).replace(/_/g, ' ')
}

function _deriveFieldParty(fieldName: string): string {
  const lower = fieldName.toLowerCase()
  if (lower.startsWith('landlord')) return 'landlord'
  if (/^tenant\d?_/.test(lower) || lower === 'tenant_name') return 'tenant'
  if (lower.startsWith('occupant')) return 'occupant'
  if (lower.startsWith('witness')) return 'witness'
  if (/^(property|unit|address|city|suburb|area_code|province|postal)/.test(lower)) return 'property'
  if (/^(lease|start_date|end_date|notice|early_termination)/.test(lower)) return 'lease'
  if (/^(rent|monthly|deposit|escalation|payment|bank|account|branch)/.test(lower)) return 'financial'
  return 'general'
}

function _createBlockFieldChip(fieldName: string, fieldType: string): HTMLDivElement {
  const box = document.createElement('div')
  box.contentEditable = 'false'
  box.dataset.field = fieldName
  box.dataset.fieldType = fieldType
  box.dataset.party = _deriveParty(fieldName)
  box.textContent = fieldName
  // Default position and size — caller sets top/left
  box.style.top = '0px'
  box.style.left = '0px'
  if (fieldType === 'signature') {
    box.style.width = '240px'
    box.style.height = '70px'
  } else {
    box.style.width = '120px'
    box.style.height = '44px'
  }
  return box
}

/** Re-apply runtime attributes to field elements after loading HTML from backend. */
function _hydrateFieldChips() {
  if (!editorEl.value) return

  // Walk text nodes to find {{ref}} markers and replace with interactive elements
  const walker = document.createTreeWalker(editorEl.value, NodeFilter.SHOW_TEXT)
  const replacements: { node: Text; matches: RegExpExecArray[] }[] = []
  // Regex: {{fieldName}} or {{fieldName|top:0px;left:0px;width:240px;height:70px}}
  const refPattern = /\{\{([^|}]+?)(?:\|([^}]+?))?\}\}/g

  let textNode: Text | null
  while ((textNode = walker.nextNode() as Text | null)) {
    const text = textNode.textContent || ''
    const matches: RegExpExecArray[] = []
    let match: RegExpExecArray | null
    refPattern.lastIndex = 0
    while ((match = refPattern.exec(text))) {
      matches.push({ ...match } as any)
      // Copy match properties since exec reuses the array
      matches[matches.length - 1] = Object.assign([], match, { index: match.index, input: match.input })
    }
    if (matches.length) replacements.push({ node: textNode, matches })
  }

  for (const { node, matches } of replacements) {
    const frag = document.createDocumentFragment()
    let lastIdx = 0
    const text = node.textContent || ''

    for (const m of matches) {
      // Text before the match
      if (m.index > lastIdx) frag.appendChild(document.createTextNode(text.slice(lastIdx, m.index)))

      const fieldName = m[1].trim()
      const meta = m[2] // e.g. "type:signature;party:Landlord;top:0px;left:0px;width:240px;height:70px"

      // Parse metadata into key-value map
      const metaMap: Record<string, string> = {}
      if (meta) {
        meta.split(';').forEach(pair => {
          const idx = pair.indexOf(':')
          if (idx > 0) metaMap[pair.slice(0, idx).trim()] = pair.slice(idx + 1).trim()
        })
      }

      const fieldType = metaMap.type || fieldName.replace(/^.*_/, '')

      if (BLOCK_FIELD_TYPES.has(fieldType)) {
        const box = _createBlockFieldChip(fieldName, fieldType)
        // Apply saved party
        if (metaMap.party) box.dataset.party = metaMap.party
        // Apply saved position/size
        if (metaMap.top) box.style.top = metaMap.top
        if (metaMap.left) box.style.left = metaMap.left
        if (metaMap.width) box.style.width = metaMap.width
        if (metaMap.height) box.style.height = metaMap.height
        _makeBlockDraggable(box)
        frag.appendChild(box)
      } else {
        const chip = _createFieldChip(fieldName)
        frag.appendChild(chip)
      }
      lastIdx = m.index + m[0].length
    }
    // Remaining text after last match
    if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.slice(lastIdx)))
    node.replaceWith(frag)
  }

  // Also hydrate any pre-existing [data-field] elements (e.g. from AI document updates)
  editorEl.value.querySelectorAll('[data-field]').forEach(el => {
    ;(el as HTMLElement).contentEditable = 'false'
    const field = el.getAttribute('data-field') || ''
    if (el.textContent !== field) el.textContent = field
    // Assign party color if not already set
    if (!el.getAttribute('data-party')) {
      el.setAttribute('data-party', _deriveFieldParty(field))
    }
    const fieldType = field.replace(/^.*_/, '')
    if (BLOCK_FIELD_TYPES.has(fieldType)) {
      if (!el.getAttribute('data-field-type')) el.setAttribute('data-field-type', fieldType)
      _makeBlockDraggable(el as HTMLDivElement)
    }
  })

  // Hydrate pre-existing [data-merge-field] elements (from saved HTML)
  editorEl.value.querySelectorAll('[data-merge-field]').forEach(el => {
    const field = el.getAttribute('data-merge-field') || el.getAttribute('data-field') || ''
    if (!el.getAttribute('data-party') && field) {
      el.setAttribute('data-party', _deriveFieldParty(field))
    }
  })
}

function insertField(fieldName: string) {
  showFieldPicker.value = false
  ac.value.show = false
  recentFields.value = [fieldName, ...recentFields.value.filter(f => f !== fieldName)].slice(0, 15)

  const editor = editorEl.value
  if (!editor) return
  restoreEditorSelection()

  const chip = _createFieldChip(fieldName)
  const isBlock = chip.tagName === 'DIV'

  if (isBlock) {
    // Block field: absolutely positioned — place near the current selection
    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0) {
      const caretRect = sel.getRangeAt(0).getBoundingClientRect()
      const editorRect = editor.getBoundingClientRect()
      const scrollTop = editor.scrollTop || 0
      chip.style.top = `${caretRect.top - editorRect.top + scrollTop + 20}px`
      chip.style.left = `${caretRect.left - editorRect.left}px`
    }
    editor.appendChild(chip)
    _makeBlockDraggable(chip as HTMLDivElement)
  } else {
    // Inline field: insert at caret
    const zwsBefore = document.createTextNode('\u200B')
    const zwsAfter = document.createTextNode('\u200B')

    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0) {
      const range = sel.getRangeAt(0)
      range.deleteContents()
      range.insertNode(zwsAfter)
      range.insertNode(chip)
      range.insertNode(zwsBefore)
      const afterRange = document.createRange()
      afterRange.setStartAfter(zwsAfter)
      afterRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(afterRange)
    } else {
      editor.appendChild(zwsBefore)
      editor.appendChild(chip)
      editor.appendChild(zwsAfter)
    }
  }

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
    // Leave {{refs}} as plain text — _hydrateFieldChips() will convert them to interactive elements
    const highlighted = text
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
const ALL_GROUP_KEYS = [
  'landlord', 'property',
  'tenant_1', 'tenant_2', 'tenant_3',
  'occupant_1', 'occupant_2', 'occupant_3', 'occupant_4',
  'lease_terms', 'other',
]

const visibleGroupKeys = computed(() => {
  const dv = template.value?.detected_variables
  if (!dv) return []
  return ALL_GROUP_KEYS.filter(key => {
    if (!dv[key] || dv[key].length === 0) return false
    if (key === 'tenant_2'   && tenantCount.value < 2)   return false
    if (key === 'tenant_3'   && tenantCount.value < 3)   return false
    if (key === 'occupant_1' && occupantCount.value < 1) return false
    if (key === 'occupant_2' && occupantCount.value < 2) return false
    if (key === 'occupant_3' && occupantCount.value < 3) return false
    if (key === 'occupant_4' && occupantCount.value < 4) return false
    return true
  })
})

function groupDisplayName(key: string): string {
  const map: Record<string, string> = {
    landlord:   'Landlord',    property:   'Property',
    tenant_1:   'Tenant 1',   tenant_2:   'Tenant 2',   tenant_3:   'Tenant 3',
    occupant_1: 'Occupant 1', occupant_2: 'Occupant 2',
    occupant_3: 'Occupant 3', occupant_4: 'Occupant 4',
    lease_terms: 'Lease Terms', other: 'Other',
  }
  return map[key] ?? key
}

function groupChipClass(key: string): string {
  const map: Record<string, string> = {
    landlord:    'field-chip--navy',
    property:    'field-chip--emerald',
    tenant_1:    'field-chip--blue',
    tenant_2:    'field-chip--violet',
    tenant_3:    'field-chip--pink',
    occupant_1:  'field-chip--teal',
    occupant_2:  'field-chip--teal',
    occupant_3:  'field-chip--teal',
    occupant_4:  'field-chip--teal',
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
    chatMessages.value.push({ role: 'assistant', content: data.reply, tools_used: data.tools_used || undefined })
    _saveChatHistory()   // persist chat + api_history to localStorage

    // Handle document_update (update_document / add_comment / insert_toc / renumber_sections)
    if (data.document_update?.html && editorEl.value) {
      editorEl.value.innerHTML = data.document_update.html
      editorHtml.value = data.document_update.html
      savedHtml.value  = data.document_update.html
      isDirty.value    = false
      store.updateHtml(data.document_update.html)
      showToast(`Document updated: ${data.document_update.summary}`)
      nextTick(() => { _hydrateFieldChips(); schedulePageBreaks() })
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
const pdfExporting = ref(false)

function exportPDF() {
  if (!template.value || pdfExporting.value) return
  pdfExporting.value = true
  api.get(`/leases/templates/${templateId.value}/export.pdf/`, { responseType: 'blob' })
    .then(({ data, status, headers }) => {
      // 202 Accepted — Gotenberg was unavailable; job queued for background retry
      const contentType = (headers as any)['content-type'] || ''
      if (status === 202 || contentType.includes('application/json')) {
        const reader = new FileReader()
        reader.onload = () => {
          try {
            const json = JSON.parse(reader.result as string)
            showToast(
              json.message ||
              'Preparing your document — we\'ll email you when ready.',
              'info',
            )
          } catch {
            showToast('Preparing your document — we\'ll email you when ready.', 'info')
          }
          // Navigate to the render queue so the operator can monitor progress
          router.push('/leases/render-jobs')
        }
        reader.readAsText(data instanceof Blob ? data : new Blob([data]))
        return
      }
      // 200 — PDF bytes returned directly
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `${template.value!.name || 'template'}.pdf`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 5000)
    })
    .catch((err: any) => {
      // Axios may surface the 202 as an "error" if the Content-Type is JSON
      const responseData = err?.response?.data
      if (err?.response?.status === 202 && responseData) {
        const parse = (d: any): any => {
          if (typeof d === 'object') return d
          try { return JSON.parse(d) } catch { return null }
        }
        const json = parse(responseData)
        if (json?.queued) {
          showToast(
            json.message || 'Preparing your document — we\'ll email you when ready.',
            'info',
          )
          router.push('/leases/render-jobs')
          return
        }
      }
      showToast('PDF export failed — save your content first')
    })
    .finally(() => { pdfExporting.value = false })
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

// ── Duplicate / Save As New Template ─────────────────────────────────────
const showDuplicateModal = ref(false)
const duplicateName = ref('')
const duplicating = ref(false)

function openDuplicateModal() {
  duplicateName.value = `${template.value?.name ?? 'Template'} (copy)`
  showDuplicateModal.value = true
}

async function duplicateTemplate() {
  const name = duplicateName.value.trim()
  if (!name || !template.value) return

  // Save current content first so the duplicate gets latest changes
  if (isDirty.value) {
    await saveContent()
  }

  duplicating.value = true
  try {
    const { data } = await api.post('/leases/templates/', {
      name,
      duplicate_from: template.value.id,
    })
    showDuplicateModal.value = false
    showToast(`Template "${name}" created`)
    router.push(`/leases/templates/${data.id}`)
  } catch (e: any) {
    showToast(e?.response?.data?.error ?? 'Failed to duplicate template')
  } finally {
    duplicating.value = false
  }
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function showToast(msg: string, _type?: string) {
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

/* In-document merge field chips — rendered purely via CSS.
   HTML stores only <span data-field="field_name">field_name</span>.
   The raw text is hidden; ::before renders the visual chip. */
.document-editor :deep(span[data-merge-field]),
.document-editor :deep(span[data-field]) {
  display: inline;
  font-size: 0;
  line-height: 0;
  vertical-align: baseline;
  white-space: nowrap;
}
.document-editor :deep(span[data-merge-field])::before,
.document-editor :deep(span[data-field])::before {
  content: '{{ ' attr(data-field) ' }}';
  font-size: 0.72rem;
  font-family: ui-monospace, monospace;
  font-weight: 500;
  line-height: 1.4;
  padding: 1px 6px;
  border-radius: 4px;
  margin: 0 1px;
  white-space: nowrap;
  /* Default: navy (general/unassigned) */
  background: #2B2D6E18;
  color: #2B2D6E;
  border: 1px solid #2B2D6E44;
  cursor: grab;
}
/* Party-colored merge field chips */
.document-editor :deep(span[data-party="landlord"])::before {
  background: #1e3a5f18; color: #1e3a5f; border-color: #1e3a5f44;
}
.document-editor :deep(span[data-party="tenant"])::before {
  background: #3b82f618; color: #3b82f6; border-color: #3b82f644;
}
.document-editor :deep(span[data-party="occupant"])::before {
  background: #10b98118; color: #10b981; border-color: #10b98144;
}
.document-editor :deep(span[data-party="witness"])::before {
  background: #8b5cf618; color: #8b5cf6; border-color: #8b5cf644;
}
.document-editor :deep(span[data-party="property"])::before {
  background: #f59e0b18; color: #b45309; border-color: #f59e0b44;
}
.document-editor :deep(span[data-party="financial"])::before {
  background: #10b98118; color: #047857; border-color: #10b98144;
}
.document-editor :deep(span[data-party="lease"])::before {
  background: #6366f118; color: #4f46e5; border-color: #6366f144;
}

/* Block-level field placeholders (signature, initials) — absolutely positioned, resizable */
.document-editor :deep(div[data-field-type]) {
  position: absolute;
  font-size: 0;
  line-height: 0;
  user-select: none;
  z-index: 2;
  cursor: move;
  background: #fffbeb;
  border: 2px dashed #fbbf24;
  border-radius: 6px;
  box-sizing: border-box;
}
.document-editor :deep(div[data-field-type])::before {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  gap: 6px;
  font-size: 0.72rem;
  font-family: ui-monospace, monospace;
  font-weight: 500;
  line-height: 1;
  color: #b45309;
  text-align: center;
  white-space: nowrap;
}
/* Resize handle in bottom-right corner */
.document-editor :deep(div[data-field-type])::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: 0;
  width: 14px;
  height: 14px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, #fbbf24 50%);
  border-radius: 0 0 4px 0;
}
.document-editor :deep(div[data-field-type="signature"])::before {
  content: '✍  ' attr(data-party) ' Signature';
}
.document-editor :deep(div[data-field-type="initials"])::before {
  content: '✎  ' attr(data-party) ' Initials';
}
/* Delete button on block fields */
.document-editor :deep(.block-field-delete) {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  line-height: 18px;
  text-align: center;
  border: 2px solid #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: auto;
  padding: 0;
  z-index: 5;
}
.document-editor :deep(div[data-field-type]:hover .block-field-delete) {
  opacity: 1;
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

/* Page footer bar — last page footer positioned at bottom of editor */
.page-footer-bar {
  position: absolute;
  left: 3.5rem;
  right: 3.5rem;
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  font-family: ui-sans-serif, system-ui, sans-serif;
  color: #9ca3af;
  pointer-events: none;
  user-select: none;
  z-index: 2;
}

/* A4 auto page break — injected by updatePageBreaks() */
.document-editor :deep([data-auto-page-break]) {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin: 0 -3.5rem;
  padding: 0 3.5rem 4px;
  background:
    linear-gradient(to bottom, #fff 0%, #fff calc(100% - 16px), #e8eaed calc(100% - 16px), #e8eaed 100%);
  border-bottom: none;
  position: relative;
  user-select: none;
  pointer-events: none;
  cursor: default;
  box-sizing: border-box;
}
/* Top shadow line at the bottom of each page */
.document-editor :deep([data-auto-page-break])::before {
  content: '';
  position: absolute;
  left: 0; right: 0;
  bottom: 16px;
  height: 1px;
  background: #e5e7eb;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
/* Bottom edge: subtle line at top of next page */
.document-editor :deep([data-auto-page-break])::after {
  content: '';
  position: absolute;
  left: 0; right: 0;
  bottom: 0;
  height: 1px;
  background: #e5e7eb;
  box-shadow: 0 -1px 3px rgba(0,0,0,0.06);
}
/* Footer text inside the break */
.document-editor :deep([data-auto-page-break]) .apb-left,
.document-editor :deep([data-auto-page-break]) .apb-right {
  font-size: 8px;
  color: #9ca3af;
  font-family: ui-sans-serif, system-ui, sans-serif;
  position: relative;
  z-index: 1;
  bottom: 18px; /* sit just above the gap */
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
.field-chip--teal    { background: #0d9488; color: #fff; }   /* teal (occupants) */
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
