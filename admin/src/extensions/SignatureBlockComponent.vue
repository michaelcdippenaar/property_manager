<template>
  <node-view-wrapper
    as="span"
    :class="signingContext ? 'inline align-baseline' : 'inline-block align-middle'"
    :data-field-name="node.attrs.fieldName"
  >

    <!-- ══════════════ SIGNING MODE ══════════════ -->
    <template v-if="signingContext">
      <!-- My signed-at (location) field: inline text input -->
      <span
        v-if="isMyField && node.attrs.fieldType === 'signed_at'"
        class="inline-flex items-center gap-1 align-middle"
      >
        <MapPin :size="11" class="text-navy/70 flex-shrink-0" />
        <input
          type="text"
          :value="signedAtValue"
          @input="onSignedAtInput(($event.target as HTMLInputElement).value)"
          placeholder="Type location…"
          class="inline-block px-2 py-0.5 rounded border border-navy/30 bg-white
                 text-xs font-semibold text-navy placeholder:text-gray-400
                 focus:outline-none focus:ring-1 focus:ring-navy/50
                 min-w-[140px] max-w-[220px]"
        />
      </span>

      <!-- My date field: auto-filled with today's date (check BEFORE signed/unsigned) -->
      <span
        v-else-if="isMyField && node.attrs.fieldType === 'date'"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-50 text-green-700 text-xs font-semibold align-middle"
      >
        <Calendar :size="11" />
        {{ todayFormatted }}
      </span>

      <!-- My field: already signed — show signature image -->
      <span
        v-else-if="isMyField && mySignedData"
        class="inline-flex items-center rounded border border-green-300 bg-green-50/60 align-baseline"
        :class="isInitials ? 'px-0.5 py-0 gap-0 max-h-[18px]' : 'px-1.5 py-0.5 gap-1'"
        :style="isInitials ? 'line-height: 1' : ''"
      >
        <img
          :src="mySignedData.imageData"
          :class="isInitials ? 'h-[14px] max-h-[14px]' : 'h-6'"
          class="object-contain"
          alt="Signed"
        />
        <svg v-if="!isInitials" class="w-3 h-3 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </span>

      <!-- My field: unsigned — click to sign button -->
      <button
        v-else-if="isMyField && !mySignedData"
        @click="handleSignClick"
        class="inline-flex items-center border-dashed
               border-navy bg-navy/5 hover:bg-navy/10 text-navy font-medium
               transition-all cursor-pointer animate-pulse-subtle"
        :class="isInitials
          ? 'gap-0.5 px-1.5 py-0 rounded border text-[10px] align-baseline leading-tight'
          : 'gap-1.5 px-3 py-1.5 rounded-lg border-2 text-xs align-middle'"
      >
        <component :is="iconComponent" :size="isInitials ? 10 : 14" />
        {{ signButtonLabel }}
      </button>

      <!-- Other signer's completed field -->
      <span
        v-else-if="otherSignerData"
        class="inline-flex items-center gap-0.5 border border-gray-200 bg-gray-50 text-gray-400"
        :class="isInitials ? 'px-1 py-0 rounded text-[9px] align-baseline leading-tight' : 'px-2 py-0.5 rounded-lg text-[10px] align-middle'"
      >
        <svg :class="isInitials ? 'w-2.5 h-2.5' : 'w-3 h-3'" class="text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        Signed by {{ otherSignerData.signerName }}
      </span>

      <!-- Other signer's pending field -->
      <span
        v-else
        class="inline-flex items-center gap-0.5 border border-gray-200 bg-gray-50/50 text-gray-300"
        :class="isInitials ? 'px-1 py-0 rounded text-[9px] align-baseline leading-tight' : 'px-2 py-0.5 rounded-lg text-[10px] align-middle'"
      >
        <component :is="iconComponent" :size="isInitials ? 8 : 10" />
        Pending: {{ roleName }}
      </span>
    </template>

    <!-- ══════════════ EDITOR MODE (unchanged) ══════════════ -->
    <template v-else>
      <!-- Date / Initials / Signed-At: compact chip -->
      <span
        v-if="['date','initials','signed_at'].includes(node.attrs.fieldType)"
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px]
               font-medium cursor-grab active:cursor-grabbing select-none align-baseline leading-tight"
        :class="[chipClasses, selected ? 'ring-2 ring-navy/40' : '']"
        contenteditable="false"
        :title="node.attrs.fieldName"
        data-drag-handle
        draggable="true"
      >
        <component :is="iconComponent" :size="11" class="flex-shrink-0" />
        {{ chipLabel }}
        <button
          v-if="editor.isEditable"
          @click="deleteNode"
          class="ml-0.5 p-0 hover:text-red-500 transition-colors"
          @mousedown.stop
        >
          <X :size="10" />
        </button>
      </span>

      <!-- Signature: larger card with controls -->
      <span
        v-else
        class="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-lg border-2 border-dashed select-none group whitespace-nowrap align-middle"
        :class="[blockClasses, selected ? 'ring-2 ring-navy/40' : '']"
        contenteditable="false"
      >
        <span
          class="flex-shrink-0 p-0.5 rounded cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 hover:bg-gray-100/80 transition-colors"
          data-drag-handle
          draggable="true"
          title="Drag to reposition"
        >
          <GripVertical :size="12" />
        </span>
        <span class="w-6 h-6 rounded-full inline-flex items-center justify-center flex-shrink-0" :class="iconBgClass">
          <component :is="iconComponent" :size="12" :class="iconClass" />
        </span>
        <span class="min-w-0">
          <span class="text-xs font-semibold truncate block" :class="iconClass">
            {{ displayLabel }}
          </span>
          <span class="text-[9px] text-gray-400 uppercase tracking-wider leading-tight block">
            {{ node.attrs.fieldType }} · {{ roleName }}
          </span>
        </span>
        <select
          v-if="editor.isEditable"
          :value="node.attrs.signerRole"
          @change="updateAttributes({ signerRole: ($event.target as HTMLSelectElement).value })"
          class="text-[10px] border border-gray-200 rounded px-1 py-0.5 bg-white/80 focus:ring-1 focus:ring-navy/30 flex-shrink-0"
          @mousedown.stop
          @dragstart.stop
        >
          <option value="landlord">Landlord</option>
          <option value="tenant_1">Tenant 1</option>
          <option value="tenant_2">Tenant 2</option>
          <option value="tenant_3">Tenant 3</option>
          <option value="witness">Witness</option>
          <option value="agent">Agent</option>
        </select>
        <button
          v-if="editor.isEditable"
          @click="deleteNode"
          class="p-0.5 rounded hover:bg-red-100 text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
          title="Remove"
          @mousedown.stop
        >
          <X :size="12" />
        </button>
      </span>
    </template>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import {
  PenTool, Type, Calendar, MapPin, X, GripVertical,
} from 'lucide-vue-next'

const props = defineProps(nodeViewProps)

// ── Signing context (provided by SigningDocumentViewer) ──────────────
interface SignedFieldData {
  imageData: string
  signedAt: string
  textValue?: string
}
interface SigningContextType {
  signerRole: string
  signedFields: Map<string, SignedFieldData>
  alreadySigned: Array<{ fieldName: string; fieldType: string; signerName: string; signedAt: string; textValue?: string }>
  onFieldClick: (fieldName: string, fieldType: string) => void
  onTextFieldChange?: (fieldName: string, value: string) => void
}
const signingContext = inject<SigningContextType | null>('signingContext', null)

const isInitials = computed(() => props.node.attrs.fieldType === 'initials')

const isMyField = computed(() => {
  if (!signingContext) return false
  return props.node.attrs.signerRole === signingContext.signerRole
})

const mySignedData = computed(() => {
  if (!signingContext) return null
  return signingContext.signedFields.get(props.node.attrs.fieldName) || null
})

const otherSignerData = computed(() => {
  if (!signingContext) return null
  return signingContext.alreadySigned.find(
    (f) => f.fieldName === props.node.attrs.fieldName
  ) || null
})

const signButtonLabel = computed(() => {
  const type = props.node.attrs.fieldType
  if (type === 'initials') return 'Click to Initial'
  if (type === 'date') return 'Click to Date'
  return 'Click to Sign'
})

const todayFormatted = computed(() => {
  return new Date().toLocaleDateString('en-ZA', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
})

function handleSignClick() {
  if (signingContext) {
    signingContext.onFieldClick(props.node.attrs.fieldName, props.node.attrs.fieldType)
  }
}

const signedAtValue = computed(() => {
  if (!signingContext) return ''
  return signingContext.signedFields.get(props.node.attrs.fieldName)?.textValue || ''
})

function onSignedAtInput(value: string) {
  if (signingContext?.onTextFieldChange) {
    signingContext.onTextFieldChange(props.node.attrs.fieldName, value)
  }
}

// ── Editor mode computeds (unchanged) ───────────────────────────────
const displayLabel = computed(() =>
  props.node.attrs.label || `${props.node.attrs.fieldType} — ${props.node.attrs.signerRole}`
)

const chipLabel = computed(() => {
  const role = (props.node.attrs.signerRole || 'signer').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
  if (props.node.attrs.fieldType === 'initials') return `initials ${role}`
  if (props.node.attrs.fieldType === 'date') return `date ${role}`
  if (props.node.attrs.fieldType === 'signed_at') return `signed at ${role}`
  return displayLabel.value
})

const roleName = computed(() =>
  (props.node.attrs.signerRole || 'signer').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
)

const chipClasses = computed(() => {
  const role = props.node.attrs.signerRole
  return {
    landlord:  'bg-blue-100 text-blue-700 border border-blue-200',
    tenant_1:  'bg-green-100 text-green-700 border border-green-200',
    tenant_2:  'bg-purple-100 text-purple-700 border border-purple-200',
    tenant_3:  'bg-orange-100 text-orange-700 border border-orange-200',
    witness:   'bg-amber-100 text-amber-700 border border-amber-200',
    agent:     'bg-cyan-100 text-cyan-700 border border-cyan-200',
  }[role] ?? 'bg-gray-100 text-gray-600 border border-gray-200'
})

const blockClasses = computed(() => ({
  landlord:  'border-blue-300 bg-blue-50/60',
  tenant_1:  'border-green-300 bg-green-50/60',
  tenant_2:  'border-purple-300 bg-purple-50/60',
  tenant_3:  'border-orange-300 bg-orange-50/60',
  witness:   'border-amber-300 bg-amber-50/60',
  agent:     'border-cyan-300 bg-cyan-50/60',
}[props.node.attrs.signerRole] ?? 'border-gray-300 bg-gray-50/60'))

const iconBgClass = computed(() => ({
  landlord:  'bg-blue-100',
  tenant_1:  'bg-green-100',
  tenant_2:  'bg-purple-100',
  tenant_3:  'bg-orange-100',
  witness:   'bg-amber-100',
  agent:     'bg-cyan-100',
}[props.node.attrs.signerRole] ?? 'bg-gray-100'))

const iconClass = computed(() => ({
  landlord:  'text-blue-600',
  tenant_1:  'text-green-600',
  tenant_2:  'text-purple-600',
  tenant_3:  'text-orange-600',
  witness:   'text-amber-600',
  agent:     'text-cyan-600',
}[props.node.attrs.signerRole] ?? 'text-gray-600'))

const iconComponent = computed(() => ({
  signature: PenTool,
  initials: Type,
  date: Calendar,
  signed_at: MapPin,
}[props.node.attrs.fieldType] ?? PenTool))
</script>

<style>
@keyframes pulse-subtle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.animate-pulse-subtle {
  animation: pulse-subtle 2s ease-in-out infinite;
}
</style>
