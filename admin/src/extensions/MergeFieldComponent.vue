<template>
  <node-view-wrapper
    as="span"
    class="inline"
    :data-field-name="node.attrs.fieldName"
  >
    <!-- ══════════════ SIGNING MODE ══════════════ -->
    <template v-if="signingContext">
      <!-- My editable field -->
      <span v-if="isMyField" class="inline align-baseline">
        <input
          type="text"
          :value="currentValue"
          :placeholder="displayLabel"
          @input="onInput"
          class="signing-merge-input"
          :class="currentValue ? 'has-value' : ''"
          :style="{ width: inputWidth }"
        />
      </span>

      <!-- Other signer's already-filled field -->
      <span v-else-if="prefilledValue" class="font-semibold">{{ prefilledValue }}</span>

      <!-- Other signer's unfilled field -->
      <span v-else class="text-gray-300 italic text-xs align-baseline">{{ displayLabel }}</span>
    </template>

    <!-- ══════════════ PREVIEW MODE (filled values) ══════════════ -->
    <template v-else-if="previewValue">
      <span class="font-semibold text-navy">{{ previewValue }}</span>
    </template>

    <!-- ══════════════ EDITOR MODE ══════════════ -->
    <template v-else>
      <span
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-micro
               font-medium cursor-grab active:cursor-grabbing select-none align-baseline leading-tight"
        :class="[chipClasses, selected ? 'ring-2 ring-navy/40' : '']"
        contenteditable="false"
        :title="node.attrs.fieldName"
        data-drag-handle
        draggable="true"
      >
        <component :is="iconComponent" :size="11" class="flex-shrink-0" />
        {{ displayLabel }}
      </span>
    </template>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { computed, inject, type Ref } from 'vue'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import { User, Home, FileText, Calendar, Briefcase } from 'lucide-vue-next'

const props = defineProps(nodeViewProps)

// ── Signing context (provided by SigningDocumentViewer) ──────────────
interface SigningContextType {
  signerRole: string
  capturedFields: Record<string, string>
  onMergeFieldChange: (fieldName: string, value: string) => void
}
const signingContext = inject<SigningContextType | null>('signingContext', null)

// Preview values (provided by LeaseBuilderView for live preview — injected as ComputedRef)
const previewValues = inject<Ref<Record<string, string>> | null>('mergeFieldPreviewValues', null)

const displayLabel = computed(() =>
  props.node.attrs.label || props.node.attrs.fieldName?.replace(/_/g, ' ') || '?'
)

const previewValue = computed(() => {
  const vals = previewValues?.value
  if (!vals) return null
  const val = vals[props.node.attrs.fieldName]
  return val && val !== '—' && val.trim() ? val : null
})

// ── Signing mode helpers ────────────────────────────────────────────

function _fieldBelongsToRole(fieldName: string, signerRole: string): boolean {
  const f = fieldName.toLowerCase()
  const r = signerRole.toLowerCase()

  // Landlord signer owns landlord_* and lessor_* fields
  if (r.includes('landlord') || r.includes('lessor')) {
    return f.startsWith('landlord') || f.startsWith('lessor')
  }
  // tenant_1 signer owns tenant_* (no number) and tenant_1_* fields
  if (r === 'tenant_1' || r === 'tenant' || r === 'lessee') {
    return (f.startsWith('tenant_') && !f.match(/^tenant_[2-9]/))
      || f.startsWith('tenant_1_') || f === 'tenant_name' || f === 'tenant_id'
      || f === 'tenant_phone' || f === 'tenant_email' || f.startsWith('occupant')
  }
  // tenant_2 signer owns tenant_2_* fields
  if (r === 'tenant_2') return f.startsWith('tenant_2_')
  if (r === 'tenant_3') return f.startsWith('tenant_3_')
  // Agent
  if (r.includes('agent')) return f.startsWith('agent')
  return false
}

const isMyField = computed(() => {
  if (!signingContext) return false
  return _fieldBelongsToRole(props.node.attrs.fieldName, signingContext.signerRole)
})

// Value for the current signer's editable field — read directly from capturedFields
const currentValue = computed(() =>
  signingContext?.capturedFields?.[props.node.attrs.fieldName] ?? ''
)

// Value filled by a previous signer (only for fields NOT belonging to current signer)
const prefilledValue = computed(() => {
  if (!signingContext) return null
  const val = signingContext.capturedFields?.[props.node.attrs.fieldName]
  return val && val.trim() ? val : null
})

function onInput(e: Event) {
  const val = (e.target as HTMLInputElement).value
  signingContext?.onMergeFieldChange?.(props.node.attrs.fieldName, val)
}

const inputWidth = computed(() => {
  const text = currentValue.value || displayLabel.value
  // Use em units — ~0.55em per char for proportional fonts, plus padding room
  const chars = Math.max(text.length, 8)
  return `${chars * 0.55 + 1.5}em`
})

// ── Editor mode computeds (unchanged) ───────────────────────────────

const chipClasses = computed(() => {
  const cat = props.node.attrs.category
  return {
    landlord: 'bg-info-100 text-info-700 border border-info-100',
    tenant:   'bg-success-100 text-success-700 border border-success-100',
    property: 'bg-warning-100 text-warning-700 border border-warning-100',
    lease:    'bg-purple-100 text-purple-700 border border-purple-200',
    agent:    'bg-cyan-100 text-cyan-700 border border-cyan-200',
  }[cat] ?? 'bg-gray-100 text-gray-600 border border-gray-200'
})

const iconComponent = computed(() => {
  return {
    landlord: User,
    tenant: User,
    property: Home,
    lease: FileText,
    agent: Briefcase,
  }[props.node.attrs.category] ?? Calendar
})
</script>

<style>
/* Professional inline fill-zone input — e-signing industry standard
   CRITICAL: Must not increase line height vs plain text, or pagination breaks. */
.signing-merge-input {
  display: inline;
  font: inherit;
  font-size: inherit;
  line-height: inherit;
  color: theme('colors.gray.900');
  font-weight: 600;
  vertical-align: baseline;
  box-sizing: border-box;

  /* Warm highlighted fill zone — ZERO vertical impact.
     Use box-shadow instead of border-bottom so line height is unchanged. */
  background: rgb(254 249 235 / 0.8);  /* amber-50 */
  border: none;
  border-radius: 0;
  padding: 0 2px;
  margin: 0;
  outline: none;
  box-shadow: 0 2px 0 0 rgb(245 158 11);  /* amber-500 underline */

  transition: all 150ms ease;
}

.signing-merge-input::placeholder {
  color: rgb(180 160 100 / 0.6);
  font-weight: 400;
  font-style: normal;
  font-size: 0.92em;
}

/* Focus state */
.signing-merge-input:focus {
  background: rgb(254 243 199);  /* amber-100 */
  box-shadow: 0 2px 0 0 rgb(217 119 6);  /* amber-600 underline */
}

/* Filled state — settle into the document */
.signing-merge-input.has-value {
  background: transparent;
  box-shadow: 0 2px 0 0 rgb(156 163 175);  /* gray-400 underline */
}

.signing-merge-input.has-value:focus {
  background: rgb(254 249 235 / 0.6);
  box-shadow: 0 2px 0 0 rgb(245 158 11);  /* amber-500 underline */
}
</style>
