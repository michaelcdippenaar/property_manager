<template>
  <div class="h-screen bg-gray-50 flex flex-col overflow-hidden">

    <!-- Header -->
    <header class="bg-navy text-white px-5 py-3.5 shadow-md flex items-center justify-between">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 flex-shrink-0 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h1 class="text-base font-semibold tracking-tight truncate">{{ docTitle || 'Sign Document' }}</h1>
        </div>
        <p v-if="signerLine" class="text-xs text-white/60 mt-0.5 ml-7">{{ signerLine }}</p>
      </div>
      <!-- Step indicator when signing -->
      <div
        v-if="showForm && !completed && !errorMsg"
        class="flex-shrink-0 text-xs text-white/50 hidden sm:block"
      >
        <template v-if="signingBackend === 'native' && signingFields.length">
          Field {{ currentFieldIndex + 1 }} of {{ signingFields.length }}
        </template>
        <template v-else>
          Electronic Signature
        </template>
      </div>
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
      <div class="max-w-md text-center">
        <div class="w-14 h-14 mx-auto mb-4 rounded-full bg-red-50 flex items-center justify-center">
          <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <div class="rounded-xl border border-red-200 bg-red-50 px-6 py-4 text-red-800 text-sm">
          {{ errorMsg }}
        </div>
      </div>
    </div>

    <!-- Completed -->
    <div v-else-if="completed" class="flex-1 flex items-center justify-center p-8">
      <div class="max-w-md text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-50 flex items-center justify-center">
          <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 mb-2">Signed Successfully</h2>
        <p class="text-gray-500 text-sm leading-relaxed mb-6">
          Your signature has been submitted. You will receive a copy of the signed document by email once all parties have signed.
        </p>
        <div class="space-y-3">
          <div class="flex items-center gap-3 text-left bg-white rounded-xl border border-gray-200 p-4">
            <div class="w-9 h-9 rounded-full bg-navy/5 flex items-center justify-center flex-shrink-0">
              <svg class="w-4.5 h-4.5 text-navy" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div class="min-w-0">
              <div class="text-sm font-medium text-gray-800">Check your email</div>
              <p class="text-xs text-gray-400">A signed copy will be sent to {{ signerEmail }}</p>
            </div>
          </div>
          <p class="text-xs text-gray-400">
            You can safely close this page.
          </p>
        </div>
      </div>
    </div>

    <!-- Welcome / Consent Gate -->
    <div v-else-if="!showForm" class="flex-1 flex items-center justify-center p-8">
      <div class="max-w-md w-full">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="bg-navy/[0.03] px-6 pt-6 pb-4 border-b border-gray-100">
            <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-navy/10 flex items-center justify-center">
              <svg class="w-6 h-6 text-navy" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900 text-center">You've been invited to sign</h2>
            <p class="text-sm text-gray-500 text-center mt-1">{{ docTitle }}</p>
          </div>

          <div class="px-6 py-4 space-y-3">
            <div v-if="signerName" class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0">
                <span class="text-xs font-semibold text-navy">{{ signerName.charAt(0).toUpperCase() }}</span>
              </div>
              <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">{{ signerName }}</div>
                <div class="text-xs text-gray-400 truncate">{{ signerEmail }}</div>
              </div>
            </div>

            <div class="bg-gray-50 rounded-xl p-3.5 space-y-2">
              <div class="text-xs font-medium text-gray-600 mb-1.5">What to expect:</div>
              <div v-for="item in ['Review the document at your own pace', 'Add your signature where indicated', 'Draw or type your signature']" :key="item" class="flex items-start gap-2">
                <span class="text-navy mt-0.5 flex-shrink-0">
                  <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                  </svg>
                </span>
                <span class="text-xs text-gray-600">{{ item }}</span>
              </div>
            </div>

            <label class="flex items-start gap-2.5 cursor-pointer select-none pt-1">
              <input v-model="consentGiven" type="checkbox"
                class="mt-0.5 rounded border-gray-300 text-navy focus:ring-navy/30" />
              <span class="text-xs text-gray-600 leading-relaxed">
                I agree to sign this document electronically and acknowledge that electronic signatures are legally binding.
              </span>
            </label>
          </div>

          <div class="px-6 pb-6">
            <button
              :disabled="!consentGiven"
              @click="onGetStarted"
              class="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all"
              :class="consentGiven ? 'bg-navy hover:bg-navy/90 shadow-sm' : 'bg-gray-300 cursor-not-allowed'"
            >
              Get Started
            </button>
          </div>
        </div>
        <p class="text-center text-[11px] text-gray-400 mt-4">Powered by Tremly</p>
      </div>
    </div>

    <!-- ══════════════ NATIVE SIGNING FORM ══════════════ -->
    <template v-else-if="signingBackend === 'native' && showForm">
      <div class="flex-1 overflow-auto relative">
        <SigningDocumentViewer
          :html="documentHtml"
          :signer-role="signerRole"
          :signed-fields="signedFieldsMap"
          :already-signed="alreadySignedFields"
          :on-field-click="onFieldClick"
          :captured-fields="capturedFields"
          :on-merge-field-change="onMergeFieldChange"
        />

        <!-- Floating action bar -->
        <div class="sticky bottom-0 bg-white/95 backdrop-blur border-t border-gray-200 px-5 py-3 flex items-center justify-between">
          <div class="text-xs text-gray-500">
            <template v-if="unfilledMergeFieldCount > 0">
              {{ unfilledMergeFieldCount }} info field{{ unfilledMergeFieldCount > 1 ? 's' : '' }} to fill
            </template>
            <template v-else-if="unsignedFieldCount > 0">
              {{ unsignedFieldCount }} signature{{ unsignedFieldCount > 1 ? 's' : '' }} remaining
            </template>
            <template v-else>
              All fields complete
            </template>
          </div>
          <div class="flex items-center gap-3">
            <button
              v-if="unsignedFieldCount > 0 || unfilledMergeFieldCount > 0"
              @click="scrollToNextField"
              class="px-4 py-2 text-xs font-medium text-navy bg-navy/5 hover:bg-navy/10 rounded-lg transition-colors"
            >
              Next Field
            </button>
            <button
              @click="submitSignatures"
              :disabled="unsignedFieldCount > 0 || unfilledMergeFieldCount > 0 || submitting"
              class="px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
              :class="unsignedFieldCount === 0 && unfilledMergeFieldCount === 0 && !submitting
                ? 'bg-navy hover:bg-navy/90 shadow-sm'
                : 'bg-gray-300 cursor-not-allowed'"
            >
              <template v-if="submitting">
                <span class="inline-flex items-center gap-1.5">
                  <span class="inline-flex items-center">
                    <span class="font-bold text-white text-sm">K</span>
                    <span class="klikk-dot inline-block w-1.5 h-1.5 rounded-full bg-accent"></span>
                  </span>
                  <span>Submitting</span>
                </span>
              </template>
              <template v-else>Submit Signature</template>
            </button>
          </div>
        </div>
      </div>

      <!-- Signature capture modal -->
      <SignatureCapture
        v-if="captureFieldName"
        :field-type="captureFieldType as any"
        :signer-name="signerName"
        @confirm="onSignatureConfirm"
        @cancel="captureFieldName = ''"
      />
    </template>

    <!-- ══════════════ DOCUSEAL SIGNING FORM (backward compat) ══════════════ -->
    <div v-else-if="signingBackend === 'docuseal' && embedSrc && showForm" class="flex-1 overflow-auto">
      <DocusealForm
        :src="embedSrc"
        :email="signerEmail"
        :role="signerRole"
        :expand="true"
        :with-title="false"
        :with-send-copy-button="false"
        :with-download-button="true"
        :with-field-names="false"
        :go-to-last="false"
        :allow-to-resubmit="false"
        :allow-typed-signature="true"
        :autoscroll-fields="true"
        background-color="#f9fafb"
        :custom-css="formCss"
        @completed="onCompleted"
        @declined="onDeclined"
        class="w-full h-full"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { DocusealForm } from '@docuseal/vue'
import SigningDocumentViewer from './SigningDocumentViewer.vue'
import SignatureCapture from './SignatureCapture.vue'

const route = useRoute()
const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// DocuSeal custom CSS (kept for backward compat)
const formCss = `
  .form-container { max-height: 260px !important; padding: 10px 12px !important; }
  .draw-canvas { max-height: 100px !important; }
  .steps-form { gap: 4px !important; }
  .submit-form-button, .base-button {
    background-color: #1e3a5f !important; border-radius: 8px !important; font-weight: 600 !important;
  }
  .submit-form-button:hover, .base-button:hover { background-color: #2d4a6f !important; }
`

// State
const loading = ref(true)
const errorMsg = ref('')
const completed = ref(false)
const showForm = ref(false)
const consentGiven = ref(false)
const submitting = ref(false)

// Document / signer info
const signingBackend = ref<'native' | 'docuseal'>('native')
const docTitle = ref('')
const signerName = ref('')
const signerEmail = ref('')
const signerRole = ref('')
const embedSrc = ref('')

// Native signing state
const documentHtml = ref('')
const signingFields = ref<Array<{ fieldName: string; fieldType: string; signerRole: string }>>([])
const alreadySignedFields = ref<Array<{ fieldName: string; fieldType: string; signerName: string; signedAt: string }>>([])
const signedFieldsMap = reactive(new Map<string, { imageData: string; signedAt: string }>())
const currentFieldIndex = ref(0)
const captureFieldName = ref('')
const captureFieldType = ref('')
const consentTimestamp = ref('')
// Remember last captured image per field type — auto-apply on subsequent clicks
const rememberedImages = reactive(new Map<string, string>()) // fieldType -> imageData

// Editable merge field state
const capturedFields = reactive<Record<string, string>>({})
const editableMergeFields = ref<Array<{ fieldName: string; category: string; editable: boolean; label: string }>>([])

function onMergeFieldChange(fieldName: string, value: string) {
  capturedFields[fieldName] = value
}

const signerLine = computed(() => {
  const n = signerName.value.trim()
  const e = signerEmail.value.trim()
  if (n && e) return `${n} · ${e}`
  return n || e || ''
})

const unsignedFieldCount = computed(() => {
  return signingFields.value.filter(f => !signedFieldsMap.has(f.fieldName)).length
})

const unfilledMergeFieldCount = computed(() =>
  editableMergeFields.value
    .filter(f => f.editable && !capturedFields[f.fieldName]?.trim())
    .length
)

const token = computed(() => route.params.token as string)

onMounted(async () => {
  if (!token.value) {
    errorMsg.value = 'Invalid link.'
    loading.value = false
    return
  }

  try {
    const res = await axios.get(
      `${apiBase}/esigning/public-sign/${token.value}/`,
      { headers: { Accept: 'application/json' } },
    )

    signingBackend.value = res.data.signing_backend || 'docuseal'
    docTitle.value = res.data.document_title || ''
    signerName.value = res.data.signer_name || ''
    signerEmail.value = res.data.signer_email || ''
    signerRole.value = res.data.signer_role || ''
    embedSrc.value = res.data.embed_src || ''

    if (signingBackend.value === 'docuseal' && !embedSrc.value) {
      errorMsg.value = 'Signing is not available yet. Try again later.'
    }
  } catch (e: any) {
    const d = e?.response?.data
    errorMsg.value =
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      'Could not load this signing link.'
  } finally {
    loading.value = false
  }
})

async function onGetStarted() {
  showForm.value = true
  consentTimestamp.value = new Date().toISOString()

  if (signingBackend.value === 'native') {
    // Fetch document HTML and field info
    loading.value = true
    try {
      const res = await axios.get(
        `${apiBase}/esigning/public-sign/${token.value}/document/`,
        { headers: { Accept: 'application/json' } },
      )
      documentHtml.value = res.data.html || ''
      signingFields.value = res.data.fields || []
      alreadySignedFields.value = res.data.already_signed || []
      editableMergeFields.value = res.data.editable_merge_fields || []
      // Pre-populate with already captured data from previous signers
      Object.assign(capturedFields, res.data.already_captured || {})

      // Auto-sign date fields
      for (const field of signingFields.value) {
        if (field.fieldType === 'date') {
          signedFieldsMap.set(field.fieldName, {
            imageData: '', // Dates don't need an image
            signedAt: new Date().toISOString(),
          })
        }
      }
    } catch (e: any) {
      const d = e?.response?.data
      errorMsg.value =
        (typeof d?.detail === 'string' && d.detail) ||
        e?.message ||
        'Could not load document.'
      showForm.value = false
    } finally {
      loading.value = false
    }
  }
}

function onFieldClick(fieldName: string, fieldType: string) {
  if (fieldType === 'date') {
    signedFieldsMap.set(fieldName, {
      imageData: '',
      signedAt: new Date().toISOString(),
    })
    return
  }

  // If we already have a remembered image for this field type, auto-apply it
  const remembered = rememberedImages.get(fieldType)
  if (remembered) {
    signedFieldsMap.set(fieldName, {
      imageData: remembered,
      signedAt: new Date().toISOString(),
    })
    return
  }

  // Otherwise open the capture modal
  captureFieldName.value = fieldName
  captureFieldType.value = fieldType
}

function onSignatureConfirm(imageData: string) {
  // Remember this image for future fields of the same type
  rememberedImages.set(captureFieldType.value, imageData)

  signedFieldsMap.set(captureFieldName.value, {
    imageData,
    signedAt: new Date().toISOString(),
  })
  captureFieldName.value = ''
  captureFieldType.value = ''

  // Advance to next unsigned field
  const nextUnsigned = signingFields.value.findIndex(
    f => !signedFieldsMap.has(f.fieldName) && f.fieldType !== 'date'
  )
  if (nextUnsigned >= 0) {
    currentFieldIndex.value = nextUnsigned
  }
}

function scrollToNextField() {
  // First try unfilled merge fields (text inputs), then unsigned signature fields
  const nextMerge = editableMergeFields.value.find(
    f => f.editable && !capturedFields[f.fieldName]?.trim()
  )
  if (nextMerge) {
    const el = document.querySelector(`[data-field-name="${nextMerge.fieldName}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // Focus the input inside
      const input = el.querySelector('input') as HTMLInputElement | null
      if (input) setTimeout(() => input.focus(), 400)
      return
    }
  }

  const nextField = signingFields.value.find(f => !signedFieldsMap.has(f.fieldName))
  if (nextField) {
    const el = document.querySelector(`[data-field-name="${nextField.fieldName}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
}

async function submitSignatures() {
  if (unsignedFieldCount.value > 0 || unfilledMergeFieldCount.value > 0 || submitting.value) return
  submitting.value = true

  const fields = signingFields.value.map(f => ({
    fieldName: f.fieldName,
    fieldType: f.fieldType,
    imageData: signedFieldsMap.get(f.fieldName)?.imageData || '',
  }))

  try {
    await axios.post(
      `${apiBase}/esigning/public-sign/${token.value}/sign/`,
      {
        fields,
        captured_fields: capturedFields,
        consent: {
          agreed: true,
          timestamp: consentTimestamp.value,
        },
      },
      { headers: { Accept: 'application/json' } },
    )
    completed.value = true
  } catch (e: any) {
    const d = e?.response?.data
    errorMsg.value =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      'Failed to submit your signature. Please try again.'
  } finally {
    submitting.value = false
  }
}

// DocuSeal callbacks (backward compat)
function onCompleted(_data: any) {
  completed.value = true
  axios.post(
    `${apiBase}/esigning/public-sign/${token.value}/completed/`,
    {},
    { headers: { Accept: 'application/json' } },
  ).catch(() => {})
}

function onDeclined(_data: any) {
  errorMsg.value = 'You have declined to sign this document.'
}
</script>

<style>
@keyframes klikk-bounce {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(4px); }
}
.klikk-dot {
  animation: klikk-bounce 0.8s ease-in-out infinite;
}
</style>
