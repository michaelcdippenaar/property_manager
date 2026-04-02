<template>
  <div class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/40" @click="$emit('cancel')" />

    <!-- Modal -->
    <div class="relative bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl shadow-xl overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
        <h3 class="text-sm font-semibold text-gray-900">
          {{ fieldType === 'initials' ? 'Add Your Initials' : 'Add Your Signature' }}
        </h3>
        <button @click="$emit('cancel')" class="p-1 rounded-full hover:bg-gray-100 text-gray-400">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-gray-100">
        <button
          @click="mode = 'draw'"
          class="flex-1 py-2.5 text-xs font-medium transition-colors"
          :class="mode === 'draw' ? 'text-navy border-b-2 border-navy' : 'text-gray-400 hover:text-gray-600'"
        >
          Draw
        </button>
        <button
          @click="mode = 'type'"
          class="flex-1 py-2.5 text-xs font-medium transition-colors"
          :class="mode === 'type' ? 'text-navy border-b-2 border-navy' : 'text-gray-400 hover:text-gray-600'"
        >
          Type
        </button>
      </div>

      <!-- Draw mode -->
      <div v-show="mode === 'draw'" class="px-5 py-4">
        <div class="border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/50 overflow-hidden">
          <canvas
            ref="canvasRef"
            :width="canvasWidth"
            :height="canvasHeight"
            class="w-full touch-none"
            :style="{ height: canvasHeight / 2 + 'px' }"
          />
        </div>
        <p class="text-[10px] text-gray-400 mt-1.5 text-center">
          Use your mouse or finger to {{ fieldType === 'initials' ? 'initial' : 'sign' }} above
        </p>
      </div>

      <!-- Type mode -->
      <div v-show="mode === 'type'" class="px-5 py-4">
        <input
          v-model="typedText"
          :placeholder="fieldType === 'initials' ? 'Your initials' : 'Your full name'"
          class="w-full border border-gray-200 rounded-xl px-4 py-3 text-center text-lg focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none"
          :class="typedText ? 'font-signature text-2xl' : ''"
          @input="renderTypedSignature"
        />
        <!-- Preview of typed signature -->
        <div v-if="typedText" class="mt-3 border border-gray-100 rounded-xl bg-gray-50/50 p-4 flex items-center justify-center">
          <canvas ref="typedCanvasRef" :width="canvasWidth" :height="canvasHeight" class="max-h-16" style="display:none;" />
          <span class="font-signature text-3xl text-navy select-none">{{ typedText }}</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-3 px-5 pb-5">
        <button
          @click="handleClear"
          class="px-4 py-2.5 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
        >
          Clear
        </button>
        <button
          @click="handleConfirm"
          :disabled="!canConfirm"
          class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
          :class="canConfirm ? 'bg-navy hover:bg-navy/90 shadow-sm' : 'bg-gray-300 cursor-not-allowed'"
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import SignaturePad from 'signature_pad'

const props = defineProps<{
  fieldType: 'signature' | 'initials'
  signerName?: string
}>()

const emit = defineEmits<{
  confirm: [imageData: string]
  cancel: []
}>()

const mode = ref<'draw' | 'type'>('draw')
const typedText = ref('')
const canvasRef = ref<HTMLCanvasElement | null>(null)
const typedCanvasRef = ref<HTMLCanvasElement | null>(null)
let signaturePad: SignaturePad | null = null

const canvasWidth = computed(() => props.fieldType === 'initials' ? 400 : 600)
const canvasHeight = computed(() => props.fieldType === 'initials' ? 160 : 200)

const canConfirm = computed(() => {
  if (mode.value === 'draw') return signaturePad ? !signaturePad.isEmpty() : false
  return typedText.value.trim().length > 0
})

onMounted(() => {
  nextTick(() => {
    if (canvasRef.value) {
      signaturePad = new SignaturePad(canvasRef.value, {
        penColor: '#1e3a5f',
        minWidth: 1.5,
        maxWidth: 3,
        backgroundColor: 'rgba(0,0,0,0)',
      })
      resizeCanvas()
    }
  })
  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas)
  signaturePad?.off()
})

function resizeCanvas() {
  if (!canvasRef.value || !signaturePad) return
  const canvas = canvasRef.value
  const ratio = Math.max(window.devicePixelRatio || 1, 1)
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * ratio
  canvas.height = rect.height * ratio
  const ctx = canvas.getContext('2d')
  if (ctx) ctx.scale(ratio, ratio)
  signaturePad.clear()
}

function handleClear() {
  if (mode.value === 'draw') {
    signaturePad?.clear()
  } else {
    typedText.value = ''
  }
}

function handleConfirm() {
  let imageData = ''

  if (mode.value === 'draw' && signaturePad) {
    imageData = signaturePad.toDataURL('image/png')
  } else if (mode.value === 'type' && typedText.value.trim()) {
    // Render typed text to canvas
    imageData = renderTextToCanvas(typedText.value.trim())
  }

  if (imageData) {
    emit('confirm', imageData)
  }
}

function renderTextToCanvas(text: string): string {
  const canvas = document.createElement('canvas')
  const w = props.fieldType === 'initials' ? 200 : 400
  const h = props.fieldType === 'initials' ? 80 : 100
  canvas.width = w * 2
  canvas.height = h * 2
  const ctx = canvas.getContext('2d')!
  ctx.scale(2, 2)
  ctx.fillStyle = '#1e3a5f'
  const fontSize = props.fieldType === 'initials' ? 36 : 32
  ctx.font = `italic ${fontSize}px "Dancing Script", "Brush Script MT", cursive`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, w / 2, h / 2)
  return canvas.toDataURL('image/png')
}

function renderTypedSignature() {
  // No-op — preview is shown via CSS text
}

watch(mode, () => {
  if (mode.value === 'draw') {
    nextTick(() => resizeCanvas())
  }
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;700&display=swap');
.font-signature {
  font-family: 'Dancing Script', 'Brush Script MT', cursive;
}
</style>
