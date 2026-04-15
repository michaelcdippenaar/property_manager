<template>
  <div class="document-page-wrapper flex-1 overflow-y-auto py-8 px-4 min-h-0 document-canvas-bg">
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

      <!-- Signing-field overlays (positioned per page) -->
      <div
        v-for="(field, idx) in renderedOverlays"
        :key="'sf-' + idx"
        class="signing-field-overlay"
        :style="field.style"
      >
        <template v-if="field.type === 'initials'">AB {{ field.label }}</template>
        <template v-else-if="field.type === 'signature'">✍ {{ field.label }}</template>
        <template v-else>{{ field.label }}</template>
      </div>

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

export interface SigningFieldOverlay {
  name: string
  type: string
  party: string
  page: number
  top: number
  left: number
  width: number
  height: number
}

const props = withDefaults(defineProps<{
  html: string
  editable?: boolean
  showHeader?: boolean
  showFooter?: boolean
  headerLeft?: string
  headerRight?: string
  footerLeft?: string
  contentClass?: string
  signingFields?: SigningFieldOverlay[]
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

// Signing field overlays — recomputed after page breaks settle
const renderedOverlays = ref<{ type: string; label: string; style: Record<string, string> }[]>([])

function computeOverlayPositions() {
  if (!props.signingFields?.length || !docEl.value) {
    renderedOverlays.value = []
    return
  }

  const breaks = Array.from(docEl.value.querySelectorAll('[data-auto-page-break]'))
  if (!breaks.length) {
    renderedOverlays.value = []
    return
  }

  // Compute cumulative page start offsets relative to docEl top
  // Each page break element sits between pages — the next page starts after it
  const docRect = docEl.value.getBoundingClientRect()
  const pageStarts = [0] // page 0 starts at the top of docEl
  for (const el of breaks) {
    const rect = el.getBoundingClientRect()
    pageStarts.push(rect.bottom - docRect.top)
  }

  // Scale field positions from the template editor coordinate system to the
  // lease builder's actual rendered dimensions.
  // Template editor: max-w-[680px] with px-14 (56px) padding → 568px content area
  const TEMPLATE_CONTENT_W = 568
  const padLeft = parseFloat(getComputedStyle(docEl.value).paddingLeft) || 56
  const actualContentW = docEl.value.clientWidth - padLeft * 2
  const scale = actualContentW / TEMPLATE_CONTENT_W

  renderedOverlays.value = props.signingFields.map(f => {
    const pageStart = pageStarts[f.page] ?? pageStarts[pageStarts.length - 1] ?? 0
    const label = f.name
      .replace(/_(signature|initials|date_signed)$/i, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c: string) => c.toUpperCase())

    const isInitials = f.type === 'initials'
    const scaledLeft = Math.round(f.left * scale)
    const scaledWidth = Math.round(f.width * scale)

    return {
      type: f.type,
      label,
      style: {
        position: 'absolute',
        top: `${pageStart + f.top}px`,
        left: `${padLeft + scaledLeft}px`,
        width: `${scaledWidth}px`,
        height: `${f.height}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '2px dashed var(--party-landlord-base)',
        borderRadius: '6px',
        color: 'var(--party-landlord-base)',
        fontSize: isInitials ? '8pt' : '9pt',
        fontWeight: '600',
        pointerEvents: 'none',
        zIndex: '5',
      },
    }
  })
}

function scheduleWithOverlays() {
  schedule()
  // Wait for page breaks to be injected, then compute overlay positions
  setTimeout(computeOverlayPositions, 150)
}

// Expose the element and page break scheduler for parent components
defineExpose({ docEl, pageCount, schedulePageBreaks: schedule })

// Re-run page breaks when html content changes
watch(() => props.html, () => {
  nextTick(scheduleWithOverlays)
})

// Recompute overlays when signing fields change
watch(() => props.signingFields, () => {
  nextTick(() => setTimeout(computeOverlayPositions, 150))
})

onMounted(() => {
  nextTick(scheduleWithOverlays)
})

onBeforeUnmount(destroy)
</script>

<style scoped>
/* Canvas background — surfaces `--doc-canvas-bg` as a non-scoped utility
   so the template markup stays free of hex literals. */
.document-canvas-bg { background-color: var(--doc-canvas-bg); }

/* Header overlay */
.doc-header-overlay {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3rem;
  padding: 0 3.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--doc-border);
  background: #fff;
  pointer-events: none;
  z-index: 2;
}
/* 9px/8px here are sub-text-micro chrome (document header/footer),
   not content — sanctioned micro-label exception per design standard. */
.doc-header-left  { font-size: 9px; color: var(--doc-header-text); font-family: ui-sans-serif, system-ui; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 60%; }
.doc-header-right { font-size: 16px; font-weight: 800; color: var(--doc-header-title); font-family: Georgia, serif; letter-spacing: -0.5px; }

/* Footer bar */
.doc-footer-bar {
  position: absolute;
  left: 3.5rem;
  right: 3.5rem;
  bottom: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  color: var(--doc-footer-text);
  pointer-events: none;
  z-index: 2;
}

/* Signing-field overlay box */
.signing-field-overlay {
  background: rgba(255, 255, 255, 0.85);
}

/* Typography — matches .document-editor in TemplateEditorView */
.document-page :deep(h1) { font-size: 1.15rem; font-weight: 700; margin: 1.25rem 0 0.4rem; }
.document-page :deep(h2) { font-size: 1rem;    font-weight: 600; margin: 1rem 0 0.3rem; }
.document-page :deep(h3) { font-size: 0.9rem;  font-weight: 500; margin: 0.75rem 0 0.25rem; }
.document-page :deep(p)  { font-size: 0.875rem; margin: 0.3rem 0; }
.document-page :deep(ul) { list-style-type: disc;    padding-left: 1.5rem; font-size: 0.875rem; }
.document-page :deep(ol) { list-style-type: decimal; padding-left: 1.5rem; font-size: 0.875rem; }
.document-page :deep(table) { border-collapse: collapse; width: 100%; margin: 0.5rem 0; font-size: 0.875rem; }
.document-page :deep(td), .document-page :deep(th) { border: 1px solid var(--doc-border); padding: 0.375rem 0.5rem; }
.document-page :deep(th) { background: var(--doc-th-bg); font-weight: 600; }

/* Auto page breaks */
.document-page :deep([data-auto-page-break]) {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin: 0 -3.5rem;
  padding: 0 3.5rem 4px;
  background: linear-gradient(to bottom, #fff 0%, #fff calc(100% - 16px), var(--doc-canvas-bg) calc(100% - 16px), var(--doc-canvas-bg) 100%);
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
  color: var(--doc-footer-text);
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

/* Merge field highlights (preview mode) — uses info/warning tokens */
.document-page :deep(.pf-filled) {
  background: theme('colors.info.100' / 33%);
  color: var(--party-landlord-base);
  font-weight: 500;
  border-bottom: 1px solid theme('colors.info.500');
  padding: 0 2px;
  border-radius: 2px;
}
.document-page :deep(.pf-empty) {
  background: theme('colors.warning.100');
  color: theme('colors.warning.700');
  font-size: 0.82em;
  padding: 0 4px;
  border-radius: 3px;
  font-family: ui-monospace, monospace;
  border: 1px dashed theme('colors.warning.500');
}

/* Party-colored filled fields — colors hoisted to :root in main.css */
.document-page :deep(.pf-filled[data-party="landlord"])  { background: color-mix(in srgb, var(--party-landlord-base) 9%, transparent);  color: var(--party-landlord-base);  border-bottom-color: color-mix(in srgb, var(--party-landlord-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="tenant"])    { background: color-mix(in srgb, var(--party-tenant-base) 9%, transparent);    color: var(--party-tenant-solid);   border-bottom-color: color-mix(in srgb, var(--party-tenant-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="occupant"])  { background: color-mix(in srgb, var(--party-occupant-base) 9%, transparent);  color: var(--party-occupant-solid); border-bottom-color: color-mix(in srgb, var(--party-occupant-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="witness"])   { background: color-mix(in srgb, var(--party-witness-base) 9%, transparent);   color: var(--party-witness-solid);  border-bottom-color: color-mix(in srgb, var(--party-witness-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="property"])  { background: color-mix(in srgb, var(--party-property-base) 9%, transparent);  color: var(--party-property-base);  border-bottom-color: color-mix(in srgb, var(--party-property-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="financial"]) { background: color-mix(in srgb, var(--party-financial-base) 9%, transparent); color: var(--party-financial-base); border-bottom-color: color-mix(in srgb, var(--party-financial-base) 53%, transparent); }
.document-page :deep(.pf-filled[data-party="lease"])     { background: color-mix(in srgb, var(--party-lease-base) 9%, transparent);     color: var(--party-lease-base);     border-bottom-color: color-mix(in srgb, var(--party-lease-base) 53%, transparent); }

/* Party-colored empty placeholders */
.document-page :deep(.pf-empty[data-party="landlord"])  { background: color-mix(in srgb, var(--party-landlord-base) 7%, transparent);  color: var(--party-landlord-base);  border-color: color-mix(in srgb, var(--party-landlord-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="tenant"])    { background: color-mix(in srgb, var(--party-tenant-base) 7%, transparent);    color: var(--party-tenant-solid);   border-color: color-mix(in srgb, var(--party-tenant-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="occupant"])  { background: color-mix(in srgb, var(--party-occupant-base) 7%, transparent);  color: var(--party-occupant-solid); border-color: color-mix(in srgb, var(--party-occupant-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="witness"])   { background: color-mix(in srgb, var(--party-witness-base) 7%, transparent);   color: var(--party-witness-solid);  border-color: color-mix(in srgb, var(--party-witness-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="property"])  { background: color-mix(in srgb, var(--party-property-base) 7%, transparent);  color: var(--party-property-base);  border-color: color-mix(in srgb, var(--party-property-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="financial"]) { background: color-mix(in srgb, var(--party-financial-base) 7%, transparent); color: var(--party-financial-base); border-color: color-mix(in srgb, var(--party-financial-base) 33%, transparent); }
.document-page :deep(.pf-empty[data-party="lease"])     { background: color-mix(in srgb, var(--party-lease-base) 7%, transparent);     color: var(--party-lease-base);     border-color: color-mix(in srgb, var(--party-lease-base) 33%, transparent); }

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
  background: var(--doc-chip-navy-bg);
  color: var(--doc-chip-navy-text);
  border: 1px solid var(--doc-chip-navy-border);
  cursor: grab;
}

/* Party-colored merge field chips */
.document-page :deep(span[data-party="landlord"])::before  { background: color-mix(in srgb, var(--party-landlord-base) 9%, transparent);  color: var(--party-landlord-base);  border-color: color-mix(in srgb, var(--party-landlord-base) 27%, transparent); }
.document-page :deep(span[data-party="tenant"])::before    { background: color-mix(in srgb, var(--party-tenant-base) 9%, transparent);    color: var(--party-tenant-base);    border-color: color-mix(in srgb, var(--party-tenant-base) 27%, transparent); }
.document-page :deep(span[data-party="occupant"])::before  { background: color-mix(in srgb, var(--party-occupant-base) 9%, transparent);  color: var(--party-occupant-base);  border-color: color-mix(in srgb, var(--party-occupant-base) 27%, transparent); }
.document-page :deep(span[data-party="witness"])::before   { background: color-mix(in srgb, var(--party-witness-base) 9%, transparent);   color: var(--party-witness-base);   border-color: color-mix(in srgb, var(--party-witness-base) 27%, transparent); }
.document-page :deep(span[data-party="property"])::before  { background: color-mix(in srgb, var(--party-property-base) 9%, transparent);  color: var(--party-property-base);  border-color: color-mix(in srgb, var(--party-property-base) 27%, transparent); }
.document-page :deep(span[data-party="financial"])::before { background: color-mix(in srgb, var(--party-financial-base) 9%, transparent); color: var(--party-financial-base); border-color: color-mix(in srgb, var(--party-financial-base) 27%, transparent); }
.document-page :deep(span[data-party="lease"])::before     { background: color-mix(in srgb, var(--party-lease-base) 9%, transparent);     color: var(--party-lease-base);     border-color: color-mix(in srgb, var(--party-lease-base) 27%, transparent); }
</style>
