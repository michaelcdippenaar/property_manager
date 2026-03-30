<template>
  <div class="h-screen bg-gray-50 flex flex-col overflow-hidden">
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

    <!-- Document + Inline Signing -->
    <template v-else>
      <!-- Top bar -->
      <div class="bg-white border-b px-4 py-2 flex items-center justify-between text-sm">
        <span class="text-gray-500">
          Page {{ currentPage }} of {{ totalPages }}
        </span>
        <button
          v-if="hasSignatureField"
          @click="scrollToSignature"
          class="text-navy font-medium hover:underline text-sm"
        >
          Jump to signature &darr;
        </button>
      </div>

      <!-- PDF Viewer with inline overlays -->
      <div class="flex-1 overflow-auto bg-gray-100 p-4" ref="scrollContainer" data-scroll-container>
        <div class="max-w-3xl mx-auto space-y-4" ref="pagesContainer" data-pages-container>
          <div
            v-for="page in totalPages"
            :key="page"
            class="relative"
            :data-page-wrapper="page"
          >
            <canvas
              :data-page="page"
              class="w-full shadow-md rounded bg-white"
            />

            <!-- Signature overlay on this page -->
            <div
              v-for="field in fieldsOnPage(page)"
              :key="field.name"
              class="absolute"
              :style="fieldStyle(field)"
            >
              <!-- Signature field -->
              <div
                v-if="field.type === 'signature'"
                data-sig-field
                class="w-full h-full"
              >
                <div
                  v-if="!signatureDrawn"
                  class="w-full h-full border-2 border-dashed border-navy/40 rounded-lg bg-white/90 flex items-center justify-center cursor-pointer hover:border-navy hover:bg-navy/5 transition-all"
                  @click="openSignaturePad"
                >
                  <div class="flex flex-col items-center gap-1">
                    <svg class="w-5 h-5 text-navy/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16.862 3.487a2.1 2.1 0 113.004 2.938L7.5 18.79l-4 1 1-4L16.862 3.487z" />
                    </svg>
                    <span class="text-xs font-medium text-navy/60">Click to sign</span>
                  </div>
                </div>
                <div
                  v-else
                  class="w-full h-full border-2 border-navy rounded-lg bg-white overflow-hidden flex items-center justify-center cursor-pointer group relative"
                  @click="openSignaturePad"
                >
                  <img :src="signaturePreview" class="max-w-full max-h-full object-contain p-1" alt="Your signature" />
                  <div class="absolute inset-0 bg-navy/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span class="text-xs font-medium text-navy bg-white/90 px-2 py-1 rounded">Edit</span>
                  </div>
                </div>
              </div>

              <!-- Initials field -->
              <div
                v-else-if="field.type === 'initials'"
                data-initials-field
                class="w-full h-full"
              >
                <div
                  v-if="!initialsDrawn"
                  class="w-full h-full border-2 border-dashed border-navy/40 rounded-lg bg-white/90 flex items-center justify-center cursor-pointer hover:border-navy hover:bg-navy/5 transition-all"
                  @click="openInitialsPad"
                >
                  <div class="flex flex-col items-center gap-0.5">
                    <span class="text-xs font-bold text-navy/60">AB</span>
                    <span class="text-[10px] text-navy/50">Initials</span>
                  </div>
                </div>
                <div
                  v-else
                  class="w-full h-full border-2 border-navy rounded-lg bg-white overflow-hidden flex items-center justify-center cursor-pointer group relative"
                  @click="openInitialsPad"
                >
                  <img :src="initialsPreview" class="max-w-full max-h-full object-contain p-1" alt="Your initials" />
                  <div class="absolute inset-0 bg-navy/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span class="text-[10px] font-medium text-navy bg-white/90 px-2 py-0.5 rounded">Edit</span>
                  </div>
                </div>
              </div>

              <!-- Date field -->
              <div v-else-if="field.type === 'date'" class="w-full h-full">
                <input
                  type="date"
                  v-model="signDate"
                  class="w-full h-full px-2 text-sm border-2 border-gray-300 rounded-lg bg-white/95 focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom submit bar -->
      <div class="bg-white border-t px-4 py-3 shadow-inner">
        <div class="flex items-center justify-between max-w-3xl mx-auto">
          <p class="text-sm text-gray-600">
            <template v-if="!signatureDrawn">
              Scroll down and click the signature area to sign.
            </template>
            <template v-else-if="hasInitialsField && !initialsDrawn">
              Click the initials area to add your initials.
            </template>
            <template v-else-if="!signDate">
              Select a date to continue.
            </template>
            <template v-else>
              Ready to submit your signature.
            </template>
          </p>
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
      </div>

      <!-- Signature pad modal -->
      <Teleport to="body">
        <div
          v-if="showSigModal"
          class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
          @click.self="closeSigModal"
        >
          <div class="bg-white w-full sm:max-w-lg sm:rounded-xl rounded-t-xl shadow-2xl overflow-hidden">
            <div class="flex items-center justify-between px-4 py-3 border-b">
              <h3 class="font-semibold text-gray-900">Draw Your Signature</h3>
              <button @click="closeSigModal" class="text-gray-400 hover:text-gray-600">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="p-4">
              <div class="relative border-2 border-dashed border-gray-300 rounded-lg bg-white overflow-hidden"
                   :class="{ 'border-navy': sigPadHasContent }">
                <canvas
                  ref="sigCanvas"
                  class="w-full touch-none"
                  style="height: 180px;"
                />
                <p v-if="!sigPadHasContent" class="absolute inset-0 flex items-center justify-center text-gray-400 text-sm pointer-events-none">
                  Draw your signature here
                </p>
              </div>
            </div>
            <div class="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <button
                @click="clearSigPad"
                class="text-sm text-gray-500 hover:text-red-600"
              >
                Clear
              </button>
              <div class="flex gap-2">
                <button
                  @click="closeSigModal"
                  class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  @click="confirmSignature"
                  :disabled="!sigPadHasContent"
                  class="px-5 py-2 bg-navy text-white text-sm font-medium rounded-lg hover:bg-navy-dark disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Initials pad modal -->
      <Teleport to="body">
        <div
          v-if="showInitialsModal"
          class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
          @click.self="closeInitialsModal"
        >
          <div class="bg-white w-full sm:max-w-md sm:rounded-xl rounded-t-xl shadow-2xl overflow-hidden">
            <div class="flex items-center justify-between px-4 py-3 border-b">
              <h3 class="font-semibold text-gray-900">Draw Your Initials</h3>
              <button @click="closeInitialsModal" class="text-gray-400 hover:text-gray-600">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="p-4">
              <div class="relative border-2 border-dashed border-gray-300 rounded-lg bg-white overflow-hidden"
                   :class="{ 'border-navy': initialsPadHasContent }">
                <canvas
                  ref="initialsCanvas"
                  class="w-full touch-none"
                  style="height: 120px;"
                />
                <p v-if="!initialsPadHasContent" class="absolute inset-0 flex items-center justify-center text-gray-400 text-sm pointer-events-none">
                  Draw your initials here
                </p>
              </div>
            </div>
            <div class="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <button
                @click="clearInitialsPad"
                class="text-sm text-gray-500 hover:text-red-600"
              >
                Clear
              </button>
              <div class="flex gap-2">
                <button
                  @click="closeInitialsModal"
                  class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  @click="confirmInitials"
                  :disabled="!initialsPadHasContent"
                  class="px-5 py-2 bg-navy text-white text-sm font-medium rounded-lg hover:bg-navy-dark disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
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

// Vue template refs inside <template v-else> fragments can fail to bind.
// Use a reliable fallback via data attribute.
function getScrollContainer(): HTMLElement | null {
  return scrollContainer.value || document.querySelector('[data-scroll-container]')
}
function getPagesContainer(): HTMLElement | null {
  return pagesContainer.value || document.querySelector('[data-pages-container]')
}

// Signature state
const sigCanvas = ref<HTMLCanvasElement>()
const showSigModal = ref(false)
const sigPadHasContent = ref(false)
const signatureDrawn = ref(false)
const signaturePreview = ref('')  // PNG data URL for preview
const signatureSvg = ref('')      // SVG for submission
const signDate = ref(new Date().toISOString().split('T')[0])
let signaturePad: SignaturePad | null = null

// Initials state
const initialsCanvas = ref<HTMLCanvasElement>()
const showInitialsModal = ref(false)
const initialsPadHasContent = ref(false)
const initialsDrawn = ref(false)
const initialsPreview = ref('')  // PNG data URL for preview
const initialsSvg = ref('')      // SVG for submission
let initialsPad: SignaturePad | null = null

const signerLine = computed(() => {
  const n = signerName.value.trim()
  const e = signerEmail.value.trim()
  if (n && e) return `${n} · ${e}`
  return n || e || ''
})

const hasInitialsField = computed(() => fields.value.some(f => f.type === 'initials'))
const canSubmit = computed(() => {
  if (!signatureDrawn.value || !signDate.value) return false
  if (hasInitialsField.value && !initialsDrawn.value) return false
  return true
})
const hasSignatureField = computed(() => fields.value.some(f => f.type === 'signature'))

const token = computed(() => route.params.token as string)

// Get fields positioned on a specific page
function fieldsOnPage(page: number) {
  return fields.value.filter(f =>
    f.areas?.some((a: any) => a.page === page)
  )
}

// Compute CSS position for a field overlay (relative to the page canvas)
function fieldStyle(field: any) {
  const area = field.areas?.[0]
  if (!area) return {}
  return {
    left: `${area.x * 100}%`,
    top: `${area.y * 100}%`,
    width: `${area.w * 100}%`,
    height: `${area.h * 100}%`,
  }
}

onMounted(async () => {
  if (!token.value) {
    errorMsg.value = 'Invalid link.'
    loading.value = false
    return
  }

  try {
    const [fieldsRes, docRes] = await Promise.all([
      axios.get(`${apiBase}/esigning/public-sign/${token.value}/fields/`, {
        headers: { Accept: 'application/json' },
      }),
      axios.get(`${apiBase}/esigning/public-sign/${token.value}/document/`, {
        responseType: 'arraybuffer',
      }),
    ])

    docTitle.value = fieldsRes.data.document_title || ''
    signerName.value = fieldsRes.data.signer_name || ''
    signerEmail.value = fieldsRes.data.signer_email || ''
    signerRole.value = fieldsRes.data.signer_role || ''
    fields.value = fieldsRes.data.fields || []

    const pdfData = new Uint8Array(docRes.data)
    pdfDoc = await pdfjsLib.getDocument({ data: pdfData }).promise
    totalPages.value = pdfDoc.numPages

    loading.value = false
    await nextTick()
    await renderAllPages()

    // Attach scroll listener now that the scroll container is rendered
    await nextTick()
    getScrollContainer()?.addEventListener('scroll', handleScroll, { passive: true })
  } catch (e: any) {
    const d = e?.response?.data
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
  return getPagesContainer()?.querySelector(`canvas[data-page="${page}"]`) ?? null
}

async function renderAllPages() {
  if (!pdfDoc) return

  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const page = await pdfDoc.getPage(i)
    const canvas = getCanvasForPage(i)
    if (!canvas) continue

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
  const container = getScrollContainer()
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

function smoothScrollTo(container: HTMLElement, target: number, duration = 600) {
  const start = container.scrollTop
  const distance = target - start
  if (Math.abs(distance) < 1) return
  const startTime = performance.now()

  function step(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    // Ease-out cubic
    const ease = 1 - Math.pow(1 - progress, 3)
    container.scrollTop = start + distance * ease
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function scrollToSignature() {
  const container = getScrollContainer()
  if (!container) return

  const el = container.querySelector('[data-sig-field]') as HTMLElement | null
  if (el) {
    const containerRect = container.getBoundingClientRect()
    const elRect = el.getBoundingClientRect()
    const offset = elRect.top - containerRect.top + container.scrollTop - (containerRect.height / 3)
    smoothScrollTo(container, offset)
    // Brief pulse animation to draw attention
    setTimeout(() => {
      el.classList.add('animate-pulse')
      setTimeout(() => el.classList.remove('animate-pulse'), 2000)
    }, 650)
    return
  }
  // Fallback: scroll to the page with the signature field
  const sigField = fields.value.find(f => f.type === 'signature')
  const page = sigField?.areas?.[0]?.page
  if (page) {
    const canvas = getCanvasForPage(page) as HTMLElement | null
    if (canvas) {
      const containerRect = container.getBoundingClientRect()
      const canvasRect = canvas.getBoundingClientRect()
      const offset = canvasRect.top - containerRect.top + container.scrollTop
      smoothScrollTo(container, offset)
    }
  }
}

// Signature pad modal
async function openSignaturePad() {
  showSigModal.value = true
  await nextTick()
  initSignaturePad()
}

function closeSigModal() {
  showSigModal.value = false
  signaturePad = null
  sigPadHasContent.value = false
}

function initSignaturePad() {
  const canvas = sigCanvas.value
  if (!canvas) return

  const rect = canvas.parentElement!.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = 180 * window.devicePixelRatio
  canvas.style.width = `${rect.width}px`
  canvas.style.height = '180px'

  const ctx = canvas.getContext('2d')!
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  signaturePad = new SignaturePad(canvas, {
    backgroundColor: 'rgb(255, 255, 255)',
    penColor: 'rgb(0, 0, 0)',
  })

  signaturePad.addEventListener('endStroke', () => {
    sigPadHasContent.value = !signaturePad!.isEmpty()
  })
}

function clearSigPad() {
  signaturePad?.clear()
  sigPadHasContent.value = false
}

async function confirmSignature() {
  if (!signaturePad || signaturePad.isEmpty()) return

  signatureSvg.value = signaturePad.toSVG()

  // Generate PNG preview
  const canvas = sigCanvas.value!
  signaturePreview.value = await svgToPngDataUrl(
    signatureSvg.value,
    canvas.offsetWidth,
    canvas.offsetHeight,
  )

  signatureDrawn.value = true
  closeSigModal()
}

// ── Initials pad modal ──────────────────────────────────────────────
async function openInitialsPad() {
  showInitialsModal.value = true
  await nextTick()
  initInitialsPad()
}

function closeInitialsModal() {
  showInitialsModal.value = false
  initialsPad = null
  initialsPadHasContent.value = false
}

function initInitialsPad() {
  const canvas = initialsCanvas.value
  if (!canvas) return

  const rect = canvas.parentElement!.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = 120 * window.devicePixelRatio
  canvas.style.width = `${rect.width}px`
  canvas.style.height = '120px'

  const ctx = canvas.getContext('2d')!
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  initialsPad = new SignaturePad(canvas, {
    backgroundColor: 'rgb(255, 255, 255)',
    penColor: 'rgb(0, 0, 0)',
    minWidth: 1.5,
    maxWidth: 3,
  })

  initialsPad.addEventListener('endStroke', () => {
    initialsPadHasContent.value = !initialsPad!.isEmpty()
  })
}

function clearInitialsPad() {
  initialsPad?.clear()
  initialsPadHasContent.value = false
}

async function confirmInitials() {
  if (!initialsPad || initialsPad.isEmpty()) return

  initialsSvg.value = initialsPad.toSVG()

  const canvas = initialsCanvas.value!
  initialsPreview.value = await svgToPngDataUrl(
    initialsSvg.value,
    canvas.offsetWidth,
    canvas.offsetHeight,
  )

  initialsDrawn.value = true
  closeInitialsModal()
}

// Convert SVG string to a PNG data URL via an offscreen canvas
function svgToPngDataUrl(svg: string, width: number, height: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width * 2
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
  if (!canSubmit.value || submitting.value) return
  submitting.value = true

  const sigPng = signaturePreview.value

  const sigField = fields.value.find((f: any) => f.type === 'signature')
  const dateField = fields.value.find((f: any) => f.type === 'date')
  const initField = fields.value.find((f: any) => f.type === 'initials')

  const submitFields: { name: string; value: string }[] = []

  // Initials
  if (initField && initialsPreview.value) {
    submitFields.push({ name: initField.name, value: initialsPreview.value })
  } else if (!initField && initialsPreview.value) {
    submitFields.push({
      name: `Initials (${signerRole.value || 'First Party'})`,
      value: initialsPreview.value,
    })
  }

  // Signature
  if (sigField) {
    submitFields.push({ name: sigField.name, value: sigPng })
  } else {
    submitFields.push({
      name: `Signature (${signerRole.value || 'First Party'})`,
      value: sigPng,
    })
  }

  // Date
  if (dateField) {
    submitFields.push({ name: dateField.name, value: signDate.value })
  } else {
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
        signature_svg: signatureSvg.value,
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

// Scroll listener is attached after loading completes (see first onMounted)
</script>
