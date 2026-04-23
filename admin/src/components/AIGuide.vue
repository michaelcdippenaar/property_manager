<template>
  <!-- Feature-flagged: only renders when VITE_ENABLE_AI_GUIDE=true -->
  <template v-if="enabled">
    <!-- Highlight overlay: pulse ring on the target element -->
    <Teleport to="body">
      <div
        v-if="guide.highlightedSelector && highlightRect"
        class="ai-guide-highlight"
        :style="{
          top: `${highlightRect.top - 4}px`,
          left: `${highlightRect.left - 4}px`,
          width: `${highlightRect.width + 8}px`,
          height: `${highlightRect.height + 8}px`,
        }"
        aria-hidden="true"
      />
    </Teleport>

    <!-- Floating Action Button -->
    <Teleport to="body">
      <button
        class="ai-guide-fab"
        :class="{ 'ai-guide-fab--open': guide.isOpen }"
        aria-label="Open AI guide"
        title="Ask the guide"
        @click="guide.toggle()"
      >
        <component :is="guide.isOpen ? X : Sparkles" :size="22" />
      </button>
    </Teleport>

    <!-- Slide-in panel -->
    <Teleport to="body">
      <Transition
        enter-active-class="ai-guide-slide-enter-active"
        enter-from-class="ai-guide-slide-enter-from"
        enter-to-class="ai-guide-slide-enter-to"
        leave-active-class="ai-guide-slide-leave-active"
        leave-from-class="ai-guide-slide-leave-from"
        leave-to-class="ai-guide-slide-leave-to"
      >
        <div
          v-if="guide.isOpen"
          class="ai-guide-panel"
          role="dialog"
          aria-label="AI guide panel"
          aria-modal="true"
        >
          <!-- Panel header -->
          <div class="ai-guide-panel__header">
            <div class="flex items-center gap-2 min-w-0">
              <div class="ai-guide-panel__avatar">
                <Sparkles :size="14" />
              </div>
              <div class="min-w-0">
                <div class="text-sm font-semibold text-gray-900 leading-tight">Klikk Guide</div>
                <div class="text-[11px] text-gray-500">
                  {{ portalRole === 'owner' ? 'Owner portal' : 'Agent portal' }} assistant
                </div>
              </div>
            </div>

            <!-- Mode toggle -->
            <div class="flex items-center gap-1.5 ml-auto mr-2 flex-shrink-0">
              <button
                class="ai-guide-mode-btn"
                :class="{ 'ai-guide-mode-btn--active': guide.mode === 'walkthrough' }"
                title="Walk-through mode: highlights the next step"
                @click="guide.setMode('walkthrough')"
              >
                <Footprints :size="12" />
                Walk
              </button>
              <button
                class="ai-guide-mode-btn"
                :class="{ 'ai-guide-mode-btn--active': guide.mode === 'do-it-for-me' }"
                title="Do-it-for-me mode: pre-fills forms on your behalf"
                @click="guide.setMode('do-it-for-me')"
              >
                <Bot :size="12" />
                Auto
              </button>
            </div>

            <button
              class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors flex-shrink-0"
              aria-label="Close guide"
              @click="guide.close()"
            >
              <X :size="16" />
            </button>
          </div>

          <!-- Current route context pill -->
          <div class="px-3 py-1.5 bg-navy/5 border-b border-gray-100 text-[11px] text-navy/70 flex items-center gap-1.5">
            <MapPin :size="11" class="flex-shrink-0" />
            <span class="truncate font-mono">{{ currentRoute }}</span>
          </div>

          <!-- Message list -->
          <div
            ref="scrollEl"
            class="ai-guide-panel__messages"
          >
            <!-- Welcome state -->
            <div v-if="!guide.messages.length && !guide.isLoading" class="ai-guide-welcome">
              <div class="ai-guide-welcome__icon">
                <Sparkles :size="20" />
              </div>
              <p class="text-sm font-semibold text-gray-800 mt-3 mb-1">
                {{ portalRole === 'owner' ? 'Hi, I\'m your owner portal guide' : 'Hi, I\'m your agent portal guide' }}
              </p>
              <p class="text-xs text-gray-500 text-center leading-relaxed">
                Ask me to navigate anywhere, explain a feature, or walk you through a task.
              </p>
              <p class="mt-2 text-[11px] text-gray-400 text-center leading-relaxed px-2">
                Messages you send here are processed by an AI service.
              </p>
              <div class="mt-4 w-full space-y-1.5">
                <button
                  v-for="prompt in quickPrompts"
                  :key="prompt"
                  class="ai-guide-quick-prompt"
                  @click="submitPrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>
            </div>

            <!-- Messages -->
            <template v-for="msg in guide.messages" :key="msg.id">
              <!-- User bubble -->
              <div v-if="msg.role === 'user'" class="flex justify-end">
                <div class="ai-guide-bubble ai-guide-bubble--user">
                  {{ msg.content }}
                </div>
              </div>

              <!-- Assistant bubble + optional action card -->
              <div v-else class="space-y-2">
                <div class="flex items-start gap-2">
                  <div class="ai-guide-panel__avatar ai-guide-panel__avatar--sm flex-shrink-0 mt-0.5">
                    <Sparkles :size="11" />
                  </div>
                  <div class="ai-guide-bubble ai-guide-bubble--assistant">
                    {{ msg.content }}
                  </div>
                </div>

                <!-- Action card (walkthrough mode) -->
                <div
                  v-if="msg.action && guide.mode === 'walkthrough'"
                  class="ai-guide-action-card"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <ArrowRight :size="14" class="text-navy flex-shrink-0" />
                    <span class="text-xs font-medium text-navy truncate">{{ msg.action.label || msg.action.route }}</span>
                  </div>
                  <button
                    class="ai-guide-action-card__btn"
                    @click="navigateTo(msg.action!.route)"
                  >
                    Go
                  </button>
                </div>

                <!-- Do-it-for-me action card -->
                <div
                  v-if="msg.action && guide.mode === 'do-it-for-me' && msg.action.confirmationRequired"
                  class="ai-guide-action-card ai-guide-action-card--confirm"
                >
                  <span class="text-xs text-gray-700 flex-1">Ready to {{ msg.action.label || 'proceed' }}. Confirm?</span>
                  <div class="flex gap-1.5">
                    <button class="ai-guide-action-card__btn" @click="confirmAction(msg.action!)">
                      Confirm
                    </button>
                    <button class="ai-guide-action-card__btn ai-guide-action-card__btn--cancel" @click="cancelAction">
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </template>

            <!-- Loading indicator -->
            <div v-if="guide.isLoading" class="flex items-start gap-2">
              <div class="ai-guide-panel__avatar ai-guide-panel__avatar--sm flex-shrink-0">
                <Sparkles :size="11" />
              </div>
              <div class="ai-guide-bubble ai-guide-bubble--assistant ai-guide-bubble--loading">
                <span class="ai-guide-dot-1" />
                <span class="ai-guide-dot-2" />
                <span class="ai-guide-dot-3" />
              </div>
            </div>

            <!-- Error -->
            <p v-if="guide.error" class="text-xs text-red-500 text-center px-4">
              {{ guide.error }}
            </p>
          </div>

          <!-- Composer -->
          <div class="ai-guide-panel__composer">
            <form class="flex items-end gap-2" @submit.prevent="submit">
              <textarea
                ref="inputEl"
                v-model="draft"
                class="ai-guide-panel__input"
                rows="2"
                placeholder="Ask me anything…"
                :disabled="guide.isLoading"
                @keydown.enter.exact.prevent="submit"
              />
              <button
                type="submit"
                class="ai-guide-panel__send"
                :disabled="guide.isLoading || !draft.trim()"
                aria-label="Send"
              >
                <Send :size="14" />
              </button>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </template>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Bot, Footprints, MapPin, Send, Sparkles, X } from 'lucide-vue-next'
import { AI_GUIDE_ENABLED } from '../composables/useAIGuide'
import { useAIGuideStore, type GuideAction } from '../stores/aiGuide'

const props = withDefaults(
  defineProps<{
    portalRole?: 'agent' | 'owner'
  }>(),
  { portalRole: 'agent' },
)

const enabled = AI_GUIDE_ENABLED

const guide = useAIGuideStore()
const route = useRoute()
const router = useRouter()

const draft = ref('')
const scrollEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const highlightRect = ref<DOMRect | null>(null)

const currentRoute = computed(() => route.path)

const quickPrompts = computed(() =>
  props.portalRole === 'owner'
    ? ['Show my properties', 'View my leases', 'Go to dashboard']
    : ['Create a new property', 'View maintenance issues', 'Go to leases'],
)

// ── Highlight tracking ──────────────────────────────────────────────────────

let _highlightRaf = 0

function updateHighlightRect() {
  const sel = guide.highlightedSelector
  if (!sel) {
    highlightRect.value = null
    return
  }
  const el = document.querySelector(sel)
  if (el) {
    const r = el.getBoundingClientRect()
    // Only update if position changed meaningfully (avoid thrash)
    const cur = highlightRect.value
    if (
      !cur ||
      Math.abs(cur.top - r.top) > 1 ||
      Math.abs(cur.left - r.left) > 1
    ) {
      highlightRect.value = r
    }
  } else {
    highlightRect.value = null
  }
  _highlightRaf = requestAnimationFrame(updateHighlightRect)
}

watch(
  () => guide.highlightedSelector,
  (sel) => {
    cancelAnimationFrame(_highlightRaf)
    if (sel) {
      _highlightRaf = requestAnimationFrame(updateHighlightRect)
    } else {
      highlightRect.value = null
    }
  },
)

// ── Scroll to bottom on new messages ───────────────────────────────────────

function scrollToBottom() {
  void nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

watch(() => guide.messages.length, scrollToBottom)

// ── Close on Escape ─────────────────────────────────────────────────────────

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && guide.isOpen) {
    guide.close()
  }
}

onMounted(() => document.addEventListener('keydown', handleKey))
onUnmounted(() => {
  document.removeEventListener('keydown', handleKey)
  cancelAnimationFrame(_highlightRaf)
})

// ── Clear highlight on route change ────────────────────────────────────────
watch(() => route.path, () => guide.clearHighlight())

// ── Focus input when panel opens ────────────────────────────────────────────
watch(
  () => guide.isOpen,
  (open) => {
    if (open) void nextTick(() => inputEl.value?.focus())
  },
)

// ── Actions ─────────────────────────────────────────────────────────────────

async function submit() {
  const msg = draft.value.trim()
  if (!msg || guide.isLoading) return
  draft.value = ''
  await guide.sendMessage(msg, props.portalRole)

  // In walkthrough mode the nav is deferred to the action card button.
  // In do-it-for-me without confirmationRequired, navigate immediately.
  if (guide.mode === 'do-it-for-me' && guide.pendingAction?.route) {
    const action = guide.pendingAction
    if (!action.confirmationRequired) {
      await router.push(action.route)
      guide.pendingAction = null
    }
  }
}

async function submitPrompt(prompt: string) {
  draft.value = prompt
  await submit()
}

async function navigateTo(path?: string) {
  if (path) {
    await router.push(path)
    guide.pendingAction = null
  }
}

async function confirmAction(action: GuideAction) {
  if (action.route) await router.push(action.route)
  guide.pendingAction = null
}

function cancelAction() {
  guide.pendingAction = null
}
</script>

<style scoped>
/* ── Floating Action Button ────────────────────────────────────────────────── */
.ai-guide-fab {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 9000;
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  background: #2B2D6E;
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(43, 45, 110, 0.35);
  transition: background 150ms, box-shadow 150ms, transform 150ms;
}
.ai-guide-fab:hover {
  background: #1f2155;
  box-shadow: 0 6px 20px rgba(43, 45, 110, 0.45);
  transform: scale(1.05);
}
.ai-guide-fab:active {
  transform: scale(0.95);
}
.ai-guide-fab--open {
  background: #FF3D7F;
  box-shadow: 0 4px 16px rgba(255, 61, 127, 0.35);
}
.ai-guide-fab--open:hover {
  background: #e02466;
}

/* ── Highlight overlay ──────────────────────────────────────────────────────── */
.ai-guide-highlight {
  position: fixed;
  z-index: 8999;
  pointer-events: none;
  border-radius: 6px;
  outline: 2.5px solid #FF3D7F;
  box-shadow: 0 0 0 4px rgba(255, 61, 127, 0.18);
  animation: ai-guide-pulse 1.6s ease-in-out infinite;
}
@keyframes ai-guide-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(255, 61, 127, 0.18); }
  50%       { box-shadow: 0 0 0 8px rgba(255, 61, 127, 0.10); }
}

/* ── Panel ─────────────────────────────────────────────────────────────────── */
.ai-guide-panel {
  position: fixed;
  bottom: 5.5rem;
  right: 1.5rem;
  z-index: 8998;
  width: 22rem;
  max-width: calc(100vw - 2rem);
  max-height: min(600px, calc(100vh - 8rem));
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(16, 20, 48, 0.16);
  overflow: hidden;
}

/* Slide-in transitions */
.ai-guide-slide-enter-active,
.ai-guide-slide-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}
.ai-guide-slide-enter-from,
.ai-guide-slide-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}
.ai-guide-slide-enter-to,
.ai-guide-slide-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ── Panel sub-sections ─────────────────────────────────────────────────────── */
.ai-guide-panel__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.ai-guide-panel__avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: #2B2D6E;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-guide-panel__avatar--sm {
  width: 1.5rem;
  height: 1.5rem;
}

.ai-guide-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: #f9fafb;
  scroll-behavior: smooth;
}

.ai-guide-panel__composer {
  border-top: 1px solid #e5e7eb;
  padding: 0.75rem;
  background: #fff;
  flex-shrink: 0;
}

.ai-guide-panel__input {
  flex: 1;
  resize: none;
  font-size: 0.8125rem;
  line-height: 1.4;
  padding: 0.5rem 0.625rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  outline: none;
  transition: border-color 120ms;
  width: 100%;
}
.ai-guide-panel__input:focus {
  border-color: #2B2D6E;
}

.ai-guide-panel__send {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  background: #2B2D6E;
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 120ms, opacity 120ms;
}
.ai-guide-panel__send:hover {
  background: #1f2155;
}
.ai-guide-panel__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── Mode buttons ──────────────────────────────────────────────────────────── */
.ai-guide-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: background 100ms, color 100ms, border-color 100ms;
}
.ai-guide-mode-btn:hover {
  background: #f3f4f6;
  color: #374151;
}
.ai-guide-mode-btn--active {
  background: #2B2D6E;
  color: #fff;
  border-color: #2B2D6E;
}

/* ── Bubbles ─────────────────────────────────────────────────────────────── */
.ai-guide-bubble {
  font-size: 0.8125rem;
  line-height: 1.5;
  padding: 0.5rem 0.75rem;
  border-radius: 12px;
  white-space: pre-wrap;
  max-width: 87%;
  word-break: break-word;
}
.ai-guide-bubble--user {
  background: #2B2D6E;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.ai-guide-bubble--assistant {
  background: #fff;
  color: #111827;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.ai-guide-bubble--loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0.625rem 0.75rem;
}

/* Typing dots */
.ai-guide-dot-1,
.ai-guide-dot-2,
.ai-guide-dot-3 {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: #9ca3af;
  animation: ai-guide-bounce 1.2s ease-in-out infinite;
}
.ai-guide-dot-2 { animation-delay: 0.2s; }
.ai-guide-dot-3 { animation-delay: 0.4s; }
@keyframes ai-guide-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40%            { transform: translateY(-4px); opacity: 1; }
}

/* ── Action card ─────────────────────────────────────────────────────────── */
.ai-guide-action-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.625rem;
  padding: 0.5rem 0.625rem;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #eff6ff;
  margin-left: 2rem;
}
.ai-guide-action-card--confirm {
  border-color: #fde68a;
  background: #fffbeb;
}
.ai-guide-action-card__btn {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  border: none;
  background: #2B2D6E;
  color: #fff;
  cursor: pointer;
  transition: background 100ms;
  flex-shrink: 0;
}
.ai-guide-action-card__btn:hover {
  background: #1f2155;
}
.ai-guide-action-card__btn--cancel {
  background: #e5e7eb;
  color: #374151;
}
.ai-guide-action-card__btn--cancel:hover {
  background: #d1d5db;
}

/* ── Welcome / quick prompts ─────────────────────────────────────────────── */
.ai-guide-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 0.5rem 0.5rem;
}
.ai-guide-welcome__icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: #eff6ff;
  color: #2B2D6E;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-guide-quick-prompt {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  transition: background 100ms, border-color 100ms;
}
.ai-guide-quick-prompt:hover {
  background: #f9fafb;
  border-color: #2B2D6E;
  color: #2B2D6E;
}
</style>
