<template>
  <div ref="rootRef" class="signing-document-viewer" style="background:#f1f3f4;">
    <!-- Outer wrapper reserves the scaled height so the floating action bar
         stays at the bottom of the visible content. When pageScale === 1
         it shrinks to fit the natural page so mx-auto centers normally. -->
    <div
      class="tiptap-page-container mx-auto"
      :style="pageScale < 1
        ? { width: scaledWidthPx, height: scaledHeightPx }
        : { width: PAGE_WIDTH_PX + 'px', maxWidth: '100%' }"
    >
      <div
        ref="pageRef"
        class="py-6"
        :style="pageScale < 1
          ? { transform: `scale(${pageScale})`, transformOrigin: 'top left', width: PAGE_WIDTH_PX + 'px' }
          : { width: '100%' }"
      >
        <editor-content
          :editor="editor"
          class="tiptap-editor bg-white"
          style="box-shadow: 0 0 0 1px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { provide, reactive, ref, onBeforeUnmount, onMounted, computed, nextTick, watch } from 'vue'
import { EditorContent } from '@tiptap/vue-3'
import { useTiptapEditor } from '../../composables/useTiptapEditor'
import { PAGE_WIDTH } from '../../config/tiptapSettings'

const PAGE_WIDTH_PX = PAGE_WIDTH // 794
const SIDE_PADDING = 16 // px gutter on each side at narrow widths

const props = defineProps<{
  html: string
  signerRole: string
  signedFields: Map<string, { imageData: string; signedAt: string; textValue?: string }>
  alreadySigned: Array<{ fieldName: string; fieldType: string; signerName: string; signedAt: string; textValue?: string }>
  onFieldClick: (fieldName: string, fieldType: string) => void
  capturedFields: Record<string, string>
  onMergeFieldChange: (fieldName: string, value: string) => void
  onTextFieldChange?: (fieldName: string, value: string) => void
}>()

const { editor } = useTiptapEditor({
  content: props.html,
  editable: false,
})

// Provide signing context to SignatureBlockComponent via inject
const signingContext = reactive({
  signerRole: props.signerRole,
  signedFields: props.signedFields,
  alreadySigned: props.alreadySigned,
  onFieldClick: props.onFieldClick,
  capturedFields: props.capturedFields,
  onMergeFieldChange: props.onMergeFieldChange,
  onTextFieldChange: props.onTextFieldChange,
})

provide('signingContext', signingContext)

// ── Mobile fit-to-width scaling ─────────────────────────────────────
// PaginationPlus uses fixed-pixel page math (pageWidth: 794) so we MUST
// preserve the 794px layout; we only visually scale via CSS transform.
const rootRef = ref<HTMLDivElement>()
const pageRef = ref<HTMLDivElement>()
const pageScale = ref(1)
const pageNaturalHeight = ref(0)

const scaledWidthPx = computed(() =>
  pageScale.value < 1 ? `${Math.round(PAGE_WIDTH_PX * pageScale.value)}px` : '100%'
)
const scaledHeightPx = computed(() =>
  pageScale.value < 1 && pageNaturalHeight.value
    ? `${Math.ceil(pageNaturalHeight.value * pageScale.value)}px`
    : 'auto'
)

function updateScale() {
  const root = rootRef.value
  if (!root) return
  const available = root.clientWidth - SIDE_PADDING * 2
  const next = Math.min(1, available / PAGE_WIDTH_PX)
  pageScale.value = next > 0 ? next : 1
  if (pageRef.value) {
    pageNaturalHeight.value = pageRef.value.scrollHeight
  }
}

let ro: ResizeObserver | null = null
let pageRo: ResizeObserver | null = null

onMounted(() => {
  updateScale()
  if (rootRef.value && 'ResizeObserver' in window) {
    ro = new ResizeObserver(updateScale)
    ro.observe(rootRef.value)
  }
  window.addEventListener('resize', updateScale)
})

// Recompute height whenever the rendered TipTap content grows
// (pagination plugin appends pages after initial mount).
watch(
  () => editor.value,
  (ed) => {
    if (!ed) return
    ed.on('update', () => nextTick(updateScale))
    // Watch the rendered page for size changes (PaginationPlus async layout)
    nextTick(() => {
      if (pageRef.value && 'ResizeObserver' in window) {
        pageRo = new ResizeObserver(updateScale)
        pageRo.observe(pageRef.value)
      }
    })
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  ro?.disconnect()
  pageRo?.disconnect()
  window.removeEventListener('resize', updateScale)
  editor.value?.destroy()
})
</script>

<style>
@import '../../styles/tiptap-editor.css';

.signing-document-viewer {
  min-height: 100%;
}

/* Hide drag handles and resize controls in signing mode */
.signing-document-viewer .tiptap-editor [data-drag-handle] {
  cursor: default !important;
}
.signing-document-viewer .tiptap-editor .column-resize-handle {
  display: none;
}

/* Hide page break labels in signing mode */
.signing-document-viewer .tiptap-editor .tiptap div[data-page-break]::after {
  display: none;
}
</style>
