<template>
  <div class="document-page-wrapper flex-1 overflow-y-auto py-8 px-4 min-h-0 bg-[#e8eaed]">
    <div class="relative max-w-[680px] mx-auto overflow-x-hidden">
      <!-- Header overlay -->
      <div v-if="showHeader" class="doc-header-overlay">
        <span class="doc-header-left">{{ headerLeft }}</span>
        <span class="doc-header-right">{{ headerRight }}</span>
      </div>

      <!-- Document content area -->
      <div
        ref="docEl"
        class="w-full bg-white shadow-md px-14 min-h-[1061px] focus:outline-none document-page leading-relaxed relative"
        :class="[editable ? '' : 'select-text', contentClass]"
        :contenteditable="editable"
        :style="{ paddingTop: showHeader ? '3.5rem' : '3rem', paddingBottom: '3rem' }"
        v-html="html"
        @input="$emit('input', $event)"
        @keydown="$emit('keydown', $event)"
      />

      <!-- Footer bar (last page) -->
      <div v-if="showFooter" class="doc-footer-bar">
        <span class="text-gray-400">{{ footerLeft }}</span>
        <span class="text-gray-500">Page {{ pageCount }} of {{ pageCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick, toRef } from 'vue'
import { usePageBreaks } from '../composables/usePageBreaks'

const props = withDefaults(defineProps<{
  html: string
  editable?: boolean
  showHeader?: boolean
  showFooter?: boolean
  headerLeft?: string
  headerRight?: string
  footerLeft?: string
  contentClass?: string
}>(), {
  editable: false,
  showHeader: false,
  showFooter: false,
  headerLeft: '',
  headerRight: '',
  footerLeft: '',
  contentClass: '',
})

defineEmits<{
  input: [event: Event]
  keydown: [event: KeyboardEvent]
}>()

const docEl = ref<HTMLElement | null>(null)

const { pageCount, schedule, destroy } = usePageBreaks(docEl, {
  footerLeft: toRef(props, 'footerLeft'),
})

// Expose the element and page break scheduler for parent components
defineExpose({ docEl, pageCount, schedulePageBreaks: schedule })

// Re-run page breaks when html content changes
watch(() => props.html, () => {
  nextTick(schedule)
})

onMounted(() => {
  nextTick(schedule)
})

onBeforeUnmount(destroy)
</script>

<style scoped>
/* Header overlay */
.doc-header-overlay {
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
  z-index: 2;
}
.doc-header-left  { font-size: 9px; color: #6b7280; font-family: ui-sans-serif, system-ui; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
.doc-header-right { font-size: 16px; font-weight: 800; color: #1e3a5f; font-family: Georgia, serif; letter-spacing: -0.5px; }

/* Footer bar */
.doc-footer-bar {
  position: absolute;
  left: 3.5rem;
  right: 3.5rem;
  bottom: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  color: #9ca3af;
  pointer-events: none;
  z-index: 2;
}

/* Auto page breaks */
.document-page :deep([data-auto-page-break]) {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin: 0 -3.5rem;
  padding: 0 3.5rem 4px;
  background: linear-gradient(to bottom, #fff 0%, #fff calc(100% - 16px), #e8eaed calc(100% - 16px), #e8eaed 100%);
  position: relative;
  user-select: none;
  pointer-events: none;
}
.document-page :deep([data-auto-page-break])::before {
  content: '';
  position: absolute;
  left: 0; right: 0;
  top: calc(100% - 38px);
  height: 6px;
  box-shadow: 0 -3px 6px rgba(0,0,0,0.08);
}
.document-page :deep([data-auto-page-break])::after {
  content: '';
  position: absolute;
  left: 0; right: 0;
  bottom: 0;
  height: 6px;
  box-shadow: 0 3px 6px rgba(0,0,0,0.08);
}
.document-page :deep([data-auto-page-break]) .apb-left,
.document-page :deep([data-auto-page-break]) .apb-right {
  font-size: 8px;
  color: #9ca3af;
  font-family: ui-sans-serif, system-ui, sans-serif;
  position: relative;
  z-index: 1;
}

/* Manual page breaks */
.document-page :deep([data-page-break]) {
  display: block;
  height: 0;
  position: relative;
  margin: 0;
  page-break-after: always;
}

/* Merge field highlights (preview mode) */
.document-page :deep(.pf-filled) {
  background: #dbeafe55;
  color: #1e3a5f;
  font-weight: 500;
  border-bottom: 1px solid #93c5fd;
  padding: 0 2px;
  border-radius: 2px;
}
.document-page :deep(.pf-empty) {
  background: #fef9c3;
  color: #92400e;
  font-size: 0.82em;
  padding: 0 4px;
  border-radius: 3px;
  font-family: ui-monospace, monospace;
  border: 1px dashed #fcd34d;
}

/* Party-colored filled fields */
.document-page :deep(.pf-filled[data-party="landlord"]) { background: #1e3a5f18; color: #1e3a5f; border-bottom-color: #1e3a5f88; }
.document-page :deep(.pf-filled[data-party="tenant"]) { background: #3b82f618; color: #2563eb; border-bottom-color: #3b82f688; }
.document-page :deep(.pf-filled[data-party="occupant"]) { background: #10b98118; color: #059669; border-bottom-color: #10b98188; }
.document-page :deep(.pf-filled[data-party="witness"]) { background: #8b5cf618; color: #7c3aed; border-bottom-color: #8b5cf688; }
.document-page :deep(.pf-filled[data-party="property"]) { background: #b4530918; color: #b45309; border-bottom-color: #b4530988; }
.document-page :deep(.pf-filled[data-party="financial"]) { background: #04785718; color: #047857; border-bottom-color: #04785788; }
.document-page :deep(.pf-filled[data-party="lease"]) { background: #4f46e518; color: #4f46e5; border-bottom-color: #4f46e588; }

/* Party-colored empty placeholders */
.document-page :deep(.pf-empty[data-party="landlord"]) { background: #1e3a5f12; color: #1e3a5f; border-color: #1e3a5f55; }
.document-page :deep(.pf-empty[data-party="tenant"]) { background: #3b82f612; color: #2563eb; border-color: #3b82f655; }
.document-page :deep(.pf-empty[data-party="occupant"]) { background: #10b98112; color: #059669; border-color: #10b98155; }
.document-page :deep(.pf-empty[data-party="witness"]) { background: #8b5cf612; color: #7c3aed; border-color: #8b5cf655; }
.document-page :deep(.pf-empty[data-party="property"]) { background: #b4530912; color: #b45309; border-color: #b4530955; }
.document-page :deep(.pf-empty[data-party="financial"]) { background: #04785712; color: #047857; border-color: #04785755; }
.document-page :deep(.pf-empty[data-party="lease"]) { background: #4f46e512; color: #4f46e5; border-color: #4f46e555; }

/* Inline field chips (editor mode) */
.document-page :deep(span[data-merge-field]),
.document-page :deep(span[data-field]) {
  display: inline;
  font-size: 0;
  line-height: 0;
  vertical-align: baseline;
  white-space: nowrap;
}
.document-page :deep(span[data-merge-field])::before,
.document-page :deep(span[data-field])::before {
  content: '{{ ' attr(data-field) ' }}';
  font-size: 0.72rem;
  font-family: ui-monospace, monospace;
  font-weight: 500;
  line-height: 1.4;
  padding: 1px 6px;
  border-radius: 4px;
  margin: 0 1px;
  white-space: nowrap;
  background: #2B2D6E18;
  color: #2B2D6E;
  border: 1px solid #2B2D6E44;
  cursor: grab;
}

/* Party-colored merge field chips */
.document-page :deep(span[data-party="landlord"])::before {
  background: #1e3a5f18; color: #1e3a5f; border-color: #1e3a5f44;
}
.document-page :deep(span[data-party="tenant"])::before {
  background: #3b82f618; color: #3b82f6; border-color: #3b82f644;
}
.document-page :deep(span[data-party="occupant"])::before {
  background: #10b98118; color: #10b981; border-color: #10b98144;
}
.document-page :deep(span[data-party="witness"])::before {
  background: #8b5cf618; color: #8b5cf6; border-color: #8b5cf644;
}
.document-page :deep(span[data-party="property"])::before {
  background: #b4530918; color: #b45309; border-color: #b4530944;
}
.document-page :deep(span[data-party="financial"])::before {
  background: #04785718; color: #047857; border-color: #04785744;
}
.document-page :deep(span[data-party="lease"])::before {
  background: #4f46e518; color: #4f46e5; border-color: #4f46e544;
}
</style>
