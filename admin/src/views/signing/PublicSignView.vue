<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <!-- Header -->
    <header class="bg-navy text-white px-4 py-4 shadow-md">
      <h1 class="text-lg font-semibold tracking-tight">Sign Document</h1>
      <p v-if="docTitle" class="text-sm text-white/80 mt-0.5">{{ docTitle }}</p>
      <p v-if="signerLine" class="text-xs text-white/70 mt-0.5">{{ signerLine }}</p>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center p-8">
      <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-3 border-navy/20 border-t-navy rounded-full animate-spin" />
        <span class="text-gray-500 text-sm">Loading document...</span>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="errorMsg" class="flex-1 flex items-center justify-center p-8">
      <div class="max-w-md text-center rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-red-800 text-sm">
        {{ errorMsg }}
      </div>
    </div>

    <!-- Success -->
    <div v-else-if="submitted" class="flex-1 flex items-center justify-center p-8">
      <div class="max-w-md text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-success-100 flex items-center justify-center">
          <svg class="w-8 h-8 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 mb-2">Signed Successfully</h2>
        <p class="text-gray-600 text-sm">
          Your signature has been submitted. You will receive a copy of the signed document by email once all parties have signed.
        </p>
      </div>
    </div>

    <!-- Document + Signing UI -->
    <template v-else>
      <!-- Step indicator -->
      <div class="bg-white border-b px-4 py-2 flex items-center justify-between text-sm">
        <div class="flex items-center gap-2">
          <span
            :class="[
              'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold',
              step === 'review' ? 'bg-navy text-white' : 'bg-gray-200 text-gray-500'
            ]"
          >1</span>
          <span :class="step === 'review' ? 'font-medium text-gray-900' : 'text-gray-500'">Review</span>
          <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          <span
            :class="[
              'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold',
              step === 'sign' ? 'bg-navy text-white' : 'bg-gray-200 text-gray-500'
            ]"
          >2</span>
          <span :class="step === 'sign' ? 'font-medium text-gray-900' : 'text-gray-500'">Sign</span>
        </div>
        <span class="text-xs text-gray-400">
          Page {{ currentPage }} of {{ totalPages }}
        </span>
      </div>

      <!-- PDF Viewer -->
      <div class="flex-1 overflow-auto bg-gray-100 p-4" ref="scrollContainer">
        <div class="max-w-3xl mx-auto space-y-4" ref="pagesContainer">
          <canvas
            v-for="page in totalPages"
            :key="page"
            :data-page="page"
            class="w-full shadow-md rounded bg-white"
          />
        </div>
      </div>

      <!-- Bottom bar -->
      <div class="bg-white border-t px-4 py-3 shadow-inner">
        <div v-if="step === 'review'" class="flex items-center justify-between max-w-3xl mx-auto">
          <p class="text-sm text-gray-600">
            Review the document, then proceed to sign.
          </p>
          <button
            @click="step = 'sign'"
            class="px-5 py-2.5 bg-navy text-white text-sm font-medium rounded-lg hover:bg-navy-dark transition-colors"
          >
            Proceed to Sign
          </button>
        </div>

        <div v-else class="max-w-3xl mx-auto space-y-4">
          <!-- Signature pad -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Your Signature
            </label>
            <div class="relative border-2 border-dashed border-gray-300 rounded-lg bg-white overflow-hidden"
                 :class="{ 'border-navy': signatureDrawn }">
              <canvas
                ref="sigCanvas"
                class="w-full touch-none"
                style="height: 160px;"
              />
              <button
                v-if="signatureDrawn"
                @click="clearSignature"
                class="absolute top-2 right-2 text-xs text-gray-500 hover:text-red-600 bg-white/90 px-2 py-1 rounded"
              >
                Clear
              </button>
              <p v-if="!signatureDrawn" class="absolute inset-0 flex items-center justify-center text-gray-400 text-sm pointer-events-none">
                Draw your signature here
              </p>
            </div>
          </div>

          <!-- Date field -->
          <div class="flex items-end gap-4">
            <div class="flex-1">
              <label class="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                v-model="signDate"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy"
              />
            </div>
            <button
              @click="submitSignature"
              :disabled="!canSubmit || submitting"
              class="px-6 py-2.5 bg-accent text-white text-sm font-semibold rounded-lg hover:bg-accent-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {{ submitting ? 'Submitting...' : 'Submit Signature' }}
            </button>
          </div>

          <button
            @click="step = 'review'"
            class="text-sm text-gray-500 hover:text-gray-700"
          >
            &larr; Back to review
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import SignaturePad from 'signature_pad'
import * as pdfjsLib from 'pdfjs-dist'

// PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url,
).toString()

const route = useRoute()
const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// State
const loading = ref(true)
const errorMsg = ref('')
const submitted = ref(false)
const submitting = ref(false)
const step = ref<'review' | 'sign'>('review')

// Document info
const docTitle = ref('')
const signerName = ref('')
const signerEmail = ref('')
const signerRole = ref('')
const fields = ref<any[]>([])

// PDF rendering
const totalPages = ref(0)
const currentPage = ref(1)
const pagesContainer = ref<HTMLElement>()
const scrollContainer = ref<HTMLElement>()
let pdfDoc: any = null

// Signature
const sigCanvas = ref<HTMLCanvasElement>()
const signatureDrawn = ref(false)
const signDate = ref(new Date().toISOString().split('T')[0])
let signaturePad: SignaturePad | null = null

const signerLine = computed(() => {
  const n = signerName.value.trim()
  const e = signerEmail.value.trim()
  if (n && e) return `${n} · ${e}`
  return n || e || ''
})

const canSubmit = computed(() => signatureDrawn.value && signDate.value)

// Token from route
const token = computed(() => route.params.token as string)

onMounted(async () => {
  if (!token.value) {
    errorMsg.value = 'Invalid link.'
    loading.value = false
    return
  }

  try {
    // Fetch fields and document in parallel
    const [fieldsRes, docRes] = await Promise.all([
      axios.get(`${apiBase}/esigning/public-sign/${token.value}/fields/`, {
        headers: { Accept: 'application/json' },
      }),
      axios.get(`${apiBase}/esigning/public-sign/${token.value}/document/`, {
        responseType: 'arraybuffer',
      }),
    ])

    // Set metadata
    docTitle.value = fieldsRes.data.document_title || ''
    signerName.value = fieldsRes.data.signer_name || ''
    signerEmail.value = fieldsRes.data.signer_email || ''
    signerRole.value = fieldsRes.data.signer_role || ''
    fields.value = fieldsRes.data.fields || []

    // Load PDF
    const pdfData = new Uint8Array(docRes.data)
    pdfDoc = await pdfjsLib.getDocument({ data: pdfData }).promise
    totalPages.value = pdfDoc.numPages

    // Show the canvas DOM first, then render into it
    loading.value = false
    await nextTick()
    await renderAllPages()
  } catch (e: any) {
    const d = e?.response?.data
    // arraybuffer error responses need decoding
    if (d instanceof ArrayBuffer) {
      try {
        const text = new TextDecoder().decode(d)
        const json = JSON.parse(text)
        errorMsg.value = json.detail || 'Could not load this signing link.'
      } catch {
        errorMsg.value = 'Could not load this signing link.'
      }
    } else {
      errorMsg.value =
        (typeof d?.detail === 'string' && d.detail) ||
        e?.message ||
        'Could not load this signing link.'
    }
    loading.value = false
  }
})

function getCanvasForPage(page: number): HTMLCanvasElement | null {
  return pagesContainer.value?.querySelector(`canvas[data-page="${page}"]`) ?? null
}

async function renderAllPages() {
  if (!pdfDoc) return

  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const page = await pdfDoc.getPage(i)
    const canvas = getCanvasForPage(i)
    if (!canvas) continue

    // Render at 1.5x for crisp text on retina
    const scale = 1.5
    const viewport = page.getViewport({ scale })
    canvas.width = viewport.width
    canvas.height = viewport.height
    canvas.style.width = '100%'
    canvas.style.height = 'auto'

    const ctx = canvas.getContext('2d')!
    await page.render({ canvasContext: ctx, viewport }).promise
  }
}

// Track scroll position for page indicator
function handleScroll() {
  const container = scrollContainer.value
  if (!container) return

  const scrollTop = container.scrollTop
  let closestPage = 1
  let closestDist = Infinity

  for (let i = 1; i <= totalPages.value; i++) {
    const canvas = getCanvasForPage(i)
    if (!canvas) continue
    const dist = Math.abs(canvas.offsetTop - scrollTop - 80)
    if (dist < closestDist) {
      closestDist = dist
      closestPage = i
    }
  }
  currentPage.value = closestPage
}

// Initialize signature pad when step changes to 'sign'
watch(step, async (val) => {
  if (val === 'sign') {
    await nextTick()
    initSignaturePad()
  }
})

function initSignaturePad() {
  const canvas = sigCanvas.value
  if (!canvas || signaturePad) return

  // Size canvas to container
  const rect = canvas.parentElement!.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = 160 * window.devicePixelRatio
  canvas.style.width = `${rect.width}px`
  canvas.style.height = '160px'

  const ctx = canvas.getContext('2d')!
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  signaturePad = new SignaturePad(canvas, {
    backgroundColor: 'rgb(255, 255, 255)',
    penColor: 'rgb(0, 0, 0)',
  })

  signaturePad.addEventListener('endStroke', () => {
    signatureDrawn.value = !signaturePad!.isEmpty()
  })
}

function clearSignature() {
  signaturePad?.clear()
  signatureDrawn.value = false
}

// Convert SVG string to a PNG data URL via an offscreen canvas
function svgToPngDataUrl(svg: string, width: number, height: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width * 2   // 2x for crisp output
      canvas.height = height * 2
      const ctx = canvas.getContext('2d')!
      ctx.scale(2, 2)
      ctx.drawImage(img, 0, 0, width, height)
      URL.revokeObjectURL(url)
      resolve(canvas.toDataURL('image/png'))
    }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('SVG render failed')) }
    img.src = url
  })
}

async function submitSignature() {
  if (!canSubmit.value || submitting.value || !signaturePad) return
  submitting.value = true

  // Capture signature as SVG (vector — source of truth)
  const sigSvg = signaturePad.toSVG()
  // Convert to PNG for DocuSeal submission
  const canvas = sigCanvas.value!
  const sigPng = await svgToPngDataUrl(sigSvg, canvas.offsetWidth, canvas.offsetHeight)

  // Build field submissions matching the DocuSeal field names
  const sigField = fields.value.find((f: any) => f.type === 'signature')
  const dateField = fields.value.find((f: any) => f.type === 'date')

  const submitFields: { name: string; value: string }[] = []
  if (sigField) {
    submitFields.push({ name: sigField.name, value: sigPng })
  }
  if (dateField) {
    submitFields.push({ name: dateField.name, value: signDate.value })
  }

  // Fallback if field names not found
  if (!sigField) {
    submitFields.push({
      name: `Signature (${signerRole.value || 'First Party'})`,
      value: sigPng,
    })
  }
  if (!dateField) {
    submitFields.push({
      name: `Date (${signerRole.value || 'First Party'})`,
      value: signDate.value,
    })
  }

  try {
    await axios.post(
      `${apiBase}/esigning/public-sign/${token.value}/submit/`,
      {
        fields: submitFields,
        signature_svg: sigSvg,  // vector source of truth for our DB
      },
      { headers: { 'Content-Type': 'application/json' } },
    )
    submitted.value = true
  } catch (e: any) {
    const d = e?.response?.data
    errorMsg.value =
      d?.error || d?.detail || e?.message || 'Failed to submit signature. Please try again.'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  scrollContainer.value?.addEventListener('scroll', handleScroll, { passive: true })
})
</script>
