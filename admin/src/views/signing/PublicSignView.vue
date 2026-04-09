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
        <template v-if="signingFields.length">
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

    <!-- ══════════════ DOCUMENTS STEP ══════════════ -->
    <div v-else-if="showDocumentsStep" class="flex-1 overflow-auto">
      <div class="max-w-lg mx-auto px-4 py-8 space-y-5">

        <!-- Header -->
        <div class="text-center">
          <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-navy/10 flex items-center justify-center">
            <svg class="w-6 h-6 text-navy" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Upload Supporting Documents</h2>
          <p class="text-sm text-gray-500 mt-1">
            Please upload the following documents before signing.
          </p>
        </div>

        <!-- Document type cards -->
        <div class="space-y-3">
          <div
            v-for="docType in DOCUMENT_TYPES"
            :key="docType.key"
            class="bg-white rounded-xl border border-gray-200 overflow-hidden"
          >
            <div class="px-4 py-3 flex items-start justify-between gap-3">
              <div class="flex items-start gap-3 min-w-0">
                <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                     :class="uploadedByType[docType.key]?.length ? 'bg-green-50' : 'bg-navy/5'">
                  <!-- Uploaded: green check -->
                  <svg v-if="uploadedByType[docType.key]?.length" class="w-4.5 h-4.5 text-green-600"
                       fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                  </svg>
                  <!-- Bank statement icon -->
                  <svg v-else-if="docType.key === 'bank_statement'" class="w-4.5 h-4.5 text-navy/60"
                       fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>
                  </svg>
                  <!-- ID icon -->
                  <svg v-else-if="docType.key === 'id_copy'" class="w-4.5 h-4.5 text-navy/60"
                       fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c0 2.21 4 3 4 3"/>
                  </svg>
                  <!-- Proof of address icon -->
                  <svg v-else class="w-4.5 h-4.5 text-navy/60"
                       fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
                  </svg>
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900">{{ docType.label }}</span>
                    <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                          :class="docType.required ? 'bg-amber-50 text-amber-700' : 'bg-gray-100 text-gray-500'">
                      {{ docType.required ? 'Required' : 'Optional' }}
                    </span>
                  </div>
                  <p class="text-xs text-gray-400 mt-0.5">{{ docType.hint }}</p>

                  <!-- Uploaded files list -->
                  <div v-if="uploadedByType[docType.key]?.length" class="mt-2 space-y-1">
                    <div v-for="doc in uploadedByType[docType.key]" :key="doc.id"
                         class="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-2 py-1.5">
                      <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span class="flex-1 truncate font-mono">{{ doc.original_filename }}</span>
                      <span class="text-gray-400 flex-shrink-0">{{ formatFileSize(doc.file_size) }}</span>
                      <button @click="removeDocument(doc.id)" :disabled="uploadingFor === docType.key"
                              class="text-red-400 hover:text-red-600 flex-shrink-0 transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Upload button -->
              <div class="flex-shrink-0">
                <label :for="`upload-${docType.key}`"
                       class="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors"
                       :class="uploadingFor === docType.key
                         ? 'border-navy/20 text-navy/50 bg-navy/5 cursor-not-allowed'
                         : 'border-navy/30 text-navy hover:bg-navy/5'">
                  <svg v-if="uploadingFor !== docType.key" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                  </svg>
                  <svg v-else class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  {{ uploadingFor === docType.key ? 'Uploading…' : 'Upload' }}
                </label>
                <input :id="`upload-${docType.key}`" type="file"
                       accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                       class="hidden"
                       :disabled="uploadingFor === docType.key"
                       @change="(e) => onFileSelected(e, docType.key)" />
              </div>
            </div>

            <!-- Upload error for this type -->
            <div v-if="uploadErrorFor === docType.key"
                 class="px-4 pb-3 text-xs text-red-600">
              {{ uploadError }}
            </div>
          </div>
        </div>

        <!-- Accepted formats note -->
        <p class="text-center text-xs text-gray-400">
          Accepted: PDF, JPEG, PNG &middot; Max 10 MB per file
        </p>

        <!-- Continue button -->
        <div class="space-y-2 pt-1">
          <button
            @click="onContinueToSigning"
            class="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all bg-navy hover:bg-navy/90 shadow-sm"
          >
            Continue to Signing
            <span v-if="missingRequiredDocs > 0" class="ml-1 opacity-70 font-normal">
              ({{ missingRequiredDocs }} required doc{{ missingRequiredDocs > 1 ? 's' : '' }} missing)
            </span>
          </button>
          <p v-if="missingRequiredDocs > 0" class="text-center text-xs text-amber-600">
            You can continue without all documents, but they may be requested later.
          </p>
        </div>
      </div>
    </div>

    <!-- ══════════════ SIGNING FORM ══════════════ -->
    <template v-else-if="showForm">

      <!-- Draft restore banner (shown until dismissed) -->
      <div v-if="showDraftRestoredBanner"
           class="bg-blue-50 border-b border-blue-200 px-5 py-2.5 flex items-center justify-between">
        <div class="flex items-center gap-2 text-xs text-blue-700">
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          <span>Progress restored from your last session ({{ draftSavedAt }}).</span>
        </div>
        <button @click="showDraftRestoredBanner = false"
                class="text-blue-400 hover:text-blue-600 ml-4 flex-shrink-0">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

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
        <div class="sticky bottom-0 bg-white/95 backdrop-blur border-t border-gray-200 px-5 py-3 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <div class="text-xs text-gray-500 truncate">
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
            <!-- Save toast -->
            <Transition name="fade-toast">
              <span v-if="savedToast" class="text-xs text-green-600 font-medium flex-shrink-0">
                ✓ Saved
              </span>
            </Transition>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <!-- Save progress -->
            <button
              @click="saveDraft"
              :disabled="savingDraft"
              class="px-3 py-2 text-xs font-medium text-gray-500 hover:text-navy rounded-lg transition-colors border border-gray-200 hover:border-navy/30"
              title="Save your progress and continue later"
            >
              <svg v-if="!savingDraft" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
              </svg>
              <svg v-else class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
            </button>
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

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import SigningDocumentViewer from './SigningDocumentViewer.vue'
import SignatureCapture from './SignatureCapture.vue'

// ── Document type master list ────────────────────────────────────────
const ALL_DOC_TYPE_META: Record<string, { label: string; hint: string }> = {
  bank_statement:   { label: 'Bank Statement', hint: '3 months most recent — confirms income & affordability' },
  id_copy:          { label: 'Copy of ID / Passport', hint: 'South African ID document or valid passport' },
  proof_of_address: { label: 'Proof of Address', hint: 'Utility bill or bank letter not older than 3 months' },
}

// Set by API on load — keys of doc types the landlord requires for this signer
const requiredDocKeys = ref<string[]>([])

// Computed list used by the documents step template
const DOCUMENT_TYPES = computed(() =>
  requiredDocKeys.value
    .filter(k => ALL_DOC_TYPE_META[k])
    .map(k => ({ key: k, ...ALL_DOC_TYPE_META[k], required: true }))
)

const route = useRoute()
const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// State
const loading = ref(true)
const errorMsg = ref('')
const completed = ref(false)
const showForm = ref(false)
const consentGiven = ref(false)
const submitting = ref(false)

// Document / signer info
const signingBackend = ref<'native'>('native')
const docTitle = ref('')
const signerName = ref('')
const signerEmail = ref('')
const signerRole = ref('')

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

// ── Documents step state ────────────────────────────────────────────
const showDocumentsStep = ref(false)
const uploadedDocs = ref<Array<{
  id: number
  document_type: string
  document_type_label: string
  original_filename: string
  file_size: number
  notes: string
}>>([])
const uploadingFor = ref('')
const uploadError = ref('')
const uploadErrorFor = ref('')

const uploadedByType = computed(() => {
  const map: Record<string, typeof uploadedDocs.value> = {}
  for (const doc of uploadedDocs.value) {
    if (!map[doc.document_type]) map[doc.document_type] = []
    map[doc.document_type].push(doc)
  }
  return map
})

const missingRequiredDocs = computed(() =>
  DOCUMENT_TYPES.value.filter(
    t => t.required && !(uploadedByType.value[t.key]?.length)
  ).length
)

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function onFileSelected(event: Event, docType: string) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = '' // reset so same file can be reselected
  uploadingFor.value = docType
  uploadError.value = ''
  uploadErrorFor.value = ''

  const form = new FormData()
  form.append('file', file)
  form.append('document_type', docType)

  try {
    const res = await axios.post(
      `${apiBase}/esigning/public-sign/${token.value}/documents/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    uploadedDocs.value.push(res.data)
  } catch (e: any) {
    const d = e?.response?.data
    uploadError.value =
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      'Upload failed. Please try again.'
    uploadErrorFor.value = docType
  } finally {
    uploadingFor.value = ''
  }
}

async function removeDocument(docId: number) {
  try {
    await axios.delete(`${apiBase}/esigning/public-sign/${token.value}/documents/${docId}/`)
    uploadedDocs.value = uploadedDocs.value.filter(d => d.id !== docId)
  } catch {
    // silent — file may already be gone
  }
}

async function loadUploadedDocs() {
  try {
    const res = await axios.get(`${apiBase}/esigning/public-sign/${token.value}/documents/`)
    uploadedDocs.value = res.data.documents || []
    if (res.data.required_documents?.length) {
      requiredDocKeys.value = res.data.required_documents
    }
  } catch {
    // non-fatal
  }
}

function onContinueToSigning() {
  showDocumentsStep.value = false
}

// ── Draft save / restore ────────────────────────────────────────────
const savingDraft = ref(false)
const savedToast = ref(false)
const showDraftRestoredBanner = ref(false)
const draftSavedAt = ref('')

async function saveDraft() {
  if (savingDraft.value) return
  savingDraft.value = true
  const signedFieldsObj: Record<string, { imageData: string; signedAt: string }> = {}
  signedFieldsMap.forEach((val, key) => { signedFieldsObj[key] = val })
  try {
    await axios.post(
      `${apiBase}/esigning/public-sign/${token.value}/draft/`,
      {
        signed_fields: signedFieldsObj,
        captured_fields: { ...capturedFields },
      },
    )
    savedToast.value = true
    setTimeout(() => { savedToast.value = false }, 2500)
  } catch {
    // non-fatal — user can try again
  } finally {
    savingDraft.value = false
  }
}

async function checkForDraft() {
  try {
    const res = await axios.get(`${apiBase}/esigning/public-sign/${token.value}/draft/`)
    if (res.data?.has_draft) {
      // Restore signed fields
      const fields = res.data.signed_fields || {}
      Object.entries(fields).forEach(([k, v]: [string, any]) => {
        signedFieldsMap.set(k, v)
      })
      // Restore captured merge fields
      const captured = res.data.captured_fields || {}
      Object.assign(capturedFields, captured)
      // Show restored banner
      const savedDate = res.data.saved_at ? new Date(res.data.saved_at) : null
      if (savedDate) {
        draftSavedAt.value = savedDate.toLocaleString('en-ZA', {
          day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
        })
      }
      if (Object.keys(fields).length > 0 || Object.keys(captured).length > 0) {
        showDraftRestoredBanner.value = true
      }
    }
  } catch {
    // non-fatal
  }
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

    signingBackend.value = 'native'
    docTitle.value = res.data.document_title || ''
    signerName.value = res.data.signer_name || ''
    signerEmail.value = res.data.signer_email || ''
    signerRole.value = res.data.signer_role || ''
    // Set required document types from landlord config (falls back to all 3)
    if (res.data.required_documents?.length) {
      requiredDocKeys.value = res.data.required_documents
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
  consentTimestamp.value = new Date().toISOString()

  // Fetch document HTML, field info, and draft in parallel
  loading.value = true
  try {
    const [docRes] = await Promise.all([
      axios.get(
        `${apiBase}/esigning/public-sign/${token.value}/document/`,
        { headers: { Accept: 'application/json' } },
      ),
      loadUploadedDocs(),
    ])
    documentHtml.value = docRes.data.html || ''
    signingFields.value = docRes.data.fields || []
    alreadySignedFields.value = docRes.data.already_signed || []
    editableMergeFields.value = docRes.data.editable_merge_fields || []
    // Pre-populate with already captured data from previous signers
    Object.assign(capturedFields, docRes.data.already_captured || {})

      // Auto-sign date fields
      for (const field of signingFields.value) {
        if (field.fieldType === 'date') {
          signedFieldsMap.set(field.fieldName, {
            imageData: '',
            signedAt: new Date().toISOString(),
          })
        }
      }

      // Restore draft state (overlays on top of auto-signed dates)
      await checkForDraft()

      // Show documents step before signing
      showDocumentsStep.value = true
      showForm.value = true
    } catch (e: any) {
      const d = e?.response?.data
      errorMsg.value =
        (typeof d?.detail === 'string' && d.detail) ||
        e?.message ||
        'Could not load document.'
    } finally {
      loading.value = false
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

</script>

<style>
@keyframes klikk-bounce {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(4px); }
}
.klikk-dot {
  animation: klikk-bounce 0.8s ease-in-out infinite;
}

/* Save toast fade */
.fade-toast-enter-active, .fade-toast-leave-active { transition: opacity 0.3s ease; }
.fade-toast-enter-from, .fade-toast-leave-to { opacity: 0; }

/* Document icon colours */
.doc-icon { width: 18px; height: 18px; }
</style>
