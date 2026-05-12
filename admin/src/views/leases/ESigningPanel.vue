<template>
  <div class="space-y-4">

    <!-- Just-sent success banner — prominent, persistent confirmation that
         the lease has actually been dispatched. Sticks for ~15s and lists
         who got emailed. Complements the corner toast for unambiguous
         "yes, that worked" feedback. -->
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="justSent"
        class="flex items-start gap-3 p-4 bg-success-50 border border-success-200 rounded-xl shadow-sm"
        role="status"
        aria-live="polite"
      >
        <div class="flex-shrink-0 w-9 h-9 rounded-full bg-success-500 flex items-center justify-center">
          <CheckCircle2 :size="20" class="text-white" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-success-900">
            Lease sent for signing
          </div>
          <div class="text-xs text-success-800 mt-1 leading-relaxed">
            <template v-if="justSent.recipients.length === 1">
              Signing email is on its way to
              <span class="font-medium">{{ justSent.recipients[0] }}</span>.
            </template>
            <template v-else-if="justSent.recipients.length > 1">
              Signing emails are on their way to
              <span class="font-medium">{{ justSent.recipients.length }} signers</span>:
              {{ justSent.recipients.join(', ') }}.
            </template>
            <template v-else>
              {{ justSent.count }} signer{{ justSent.count === 1 ? '' : 's' }} added — share signing links manually below.
            </template>
            <span class="text-success-600/80"> You'll see live status updates appear here as each signer opens and signs.</span>
          </div>
        </div>
        <button
          type="button"
          class="flex-shrink-0 text-success-700/60 hover:text-success-900 p-1 -mt-1 -mr-1 transition-colors"
          aria-label="Dismiss"
          @click="justSent = null"
        >
          <X :size="14" />
        </button>
      </div>
    </transition>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-4">
      <Loader2 :size="15" class="animate-spin" />
      Loading…
    </div>

    <!-- ── Active submission: signing timeline ── -->
    <template v-else-if="latestSub">

      <!-- Header with progress -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span v-if="latestSub.status === 'completed'" class="inline-flex items-center gap-1.5 text-sm font-medium text-success-700">
            <CheckCircle2 :size="15" />
            Lease fully signed
          </span>
          <span v-else-if="latestSub.status === 'declined'" class="inline-flex items-center gap-1.5 text-sm font-medium text-danger-600">
            <XCircle :size="15" />
            Signing declined
          </span>
          <span v-else class="text-sm font-medium text-gray-700">
            Signing progress
            <span class="text-gray-400 font-normal ml-1">{{ signedCount }} of {{ totalSigners }} signed</span>
          </span>
          <!-- Live connection indicator -->
          <span
            v-if="latestSub.status !== 'completed' && latestSub.status !== 'declined'"
            class="inline-flex items-center gap-1 text-xs"
            :class="wsConnected ? 'text-success-500' : 'text-gray-300'"
            :title="wsConnected ? 'Live updates active' : 'Reconnecting…'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="wsConnected ? 'bg-success-400 animate-pulse' : 'bg-gray-300'" />
            {{ wsConnected ? 'Live' : '' }}
          </span>
        </div>
        <a
          v-if="latestSub.signed_pdf_url || latestSub.status === 'completed'"
          href="#"
          @click.prevent="downloadSignedPdf"
          class="btn-ghost text-xs flex items-center gap-1"
        >
          <Download :size="12" />
          Download signed PDF
        </a>
      </div>

      <!-- Progress bar -->
      <div v-if="latestSub.status !== 'completed' && latestSub.status !== 'declined'" class="w-full bg-gray-100 rounded-full h-1.5">
        <div
          class="bg-success-500 h-1.5 rounded-full transition-all duration-500"
          :style="{ width: `${(signedCount / totalSigners) * 100}%` }"
        />
      </div>

      <!-- Signer timeline -->
      <div class="space-y-0">
        <div
          v-for="(signer, idx) in latestSub.signers"
          :key="signer.id || idx"
          class="relative pl-7 pb-5 last:pb-0"
        >
          <!-- Vertical line -->
          <div
            v-if="idx < latestSub.signers.length - 1"
            class="absolute left-[11px] top-6 bottom-0 w-px"
            :class="isSignerDone(signer) ? 'bg-success-400' : 'bg-gray-200'"
          />

          <!-- Status dot -->
          <div
            class="absolute left-0 top-0.5 w-6 h-6 rounded-full flex items-center justify-center border-2"
            :class="signerDotClass(signer)"
          >
            <CheckCircle2 v-if="isSignerDone(signer)" :size="14" class="text-success-600" />
            <XCircle v-else-if="isSignerDeclined(signer)" :size="14" class="text-danger-500" />
            <Eye v-else-if="isSignerViewing(signer)" :size="12" class="text-info-600" />
            <Clock v-else :size="12" class="text-gray-400" />
          </div>

          <!-- Signer info -->
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm font-medium text-gray-900">{{ signer.name || signer.email }}</span>
              <span class="text-micro text-gray-400">{{ signer.role }}</span>
            </div>

            <!-- Status narrative -->
            <div class="text-xs mt-0.5" :class="signerNarrativeColor(signer)">
              {{ signerNarrative(signer) }}
            </div>

            <!-- Action: only for unsigned signers on active submissions -->
            <div
              v-if="!isSignerDone(signer) && !isSignerDeclined(signer) && latestSub.status !== 'completed' && latestSub.status !== 'declined'"
              class="flex items-center gap-2 mt-2"
            >
              <button
                v-if="signer.id && signer.email"
                type="button"
                class="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1"
                :disabled="actionLoadingId === signer.id"
                @click="sendReminder(latestSub.id, signer)"
              >
                <Loader2 v-if="actionLoadingId === signer.id" :size="11" class="animate-spin" />
                <Mail v-else :size="11" />
                Send reminder
              </button>
              <button
                v-if="signer.id"
                type="button"
                class="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors"
                :disabled="copyingLinkId === signer.id"
                @click="copyPublicLink(latestSub.id, signer)"
              >
                <Loader2 v-if="copyingLinkId === signer.id" :size="11" class="animate-spin" />
                <Link2 v-else :size="11" />
                Copy link
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Landlord can sign — shown when all tenants have signed -->
      <div
        v-if="landlordCanSign"
        class="flex items-center gap-3 px-4 py-3 bg-info-50 border border-info-100 rounded-xl mt-2"
      >
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-info-700">All tenants have signed</div>
          <div class="text-xs text-info-600 mt-0.5">The landlord can now review and sign the lease</div>
        </div>
        <button
          class="btn-primary text-xs flex items-center gap-1.5 flex-shrink-0"
          :disabled="landlordLinkLoading"
          @click="openLandlordSigningLink"
        >
          <Loader2 v-if="landlordLinkLoading" :size="12" class="animate-spin" />
          <PenTool v-else :size="12" />
          Sign as Landlord
        </button>
      </div>

      <!-- Cancel pending submission — only allowed before anyone has signed -->
      <button
        v-if="latestSub && latestSub.status !== 'completed' && latestSub.status !== 'declined' && signedCount === 0"
        class="text-xs text-danger-400 hover:text-danger-600 flex items-center gap-1 mt-2 transition-colors"
        @click="cancelSubmission"
      >
        <X :size="11" />
        Cancel signing request
      </button>

      <!-- Send again (only if previous is done/declined/expired) -->
      <button
        v-if="canSendAgain"
        class="btn-ghost text-xs flex items-center gap-1.5 w-full justify-center py-2 border-dashed border border-gray-200 rounded-xl mt-2"
        @click="openModal"
      >
        <Send :size="13" />
        Send for signing again
      </button>
    </template>

    <!-- ── RHA compliance flags ── -->
    <!-- Blocking flags: red banner, prevents signing -->
    <div
      v-if="rhaBlockingFlags.length > 0 && !rhaOverride"
      class="rounded-xl border border-danger-200 bg-danger-50 p-4 space-y-3"
    >
      <div class="flex items-start gap-2">
        <ShieldAlert :size="16" class="text-danger-600 mt-0.5 flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-danger-800">RHA Compliance Issues — Cannot Send for Signing</div>
          <p class="text-xs text-danger-600 mt-0.5">
            {{ rhaBlockingFlags.length }} blocking issue{{ rhaBlockingFlags.length !== 1 ? 's' : '' }} must be resolved before this lease can be sent for signing.
          </p>
        </div>
      </div>
      <ul class="space-y-2">
        <li
          v-for="flag in rhaBlockingFlags"
          :key="flag.code"
          class="flex items-start gap-2 text-xs text-danger-700"
        >
          <XCircle :size="13" class="text-danger-500 mt-0.5 flex-shrink-0" />
          <div>
            <span class="font-medium">{{ flag.section }}:</span> {{ flag.message }}
            <span v-if="flag.field" class="ml-1 text-danger-400">(field: {{ flag.field }})</span>
          </div>
        </li>
      </ul>
      <!-- Override — staff / agency_admin only (hidden from lower-role users) -->
      <div v-if="canRecordOverride && !showOverrideForm" class="pt-1">
        <button
          class="text-xs text-danger-500 hover:text-danger-700 underline underline-offset-2 transition-colors"
          @click="showOverrideForm = true"
        >
          Override as authorised user (reason required)
        </button>
      </div>
      <div v-else-if="canRecordOverride && showOverrideForm" class="space-y-2 pt-1 border-t border-danger-200">
        <label class="label text-danger-700">Override reason *</label>
        <textarea
          v-model="overrideReason"
          class="input text-xs resize-none h-16"
          placeholder="Explain why this lease may proceed despite the compliance issues…"
        />
        <div class="flex items-center gap-2">
          <button
            class="btn-primary bg-danger-600 hover:bg-danger-700 text-xs flex items-center gap-1.5"
            :disabled="!overrideReason.trim() || overrideLoading"
            @click="submitOverride"
          >
            <Loader2 v-if="overrideLoading" :size="12" class="animate-spin" />
            <ShieldAlert v-else :size="12" />
            Record Override &amp; Unlock
          </button>
          <button class="btn-ghost text-xs" @click="showOverrideForm = false; overrideReason = ''">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Advisory flags: yellow warning banner -->
    <div
      v-if="rhaAdvisoryFlags.length > 0"
      class="rounded-xl border border-warning-200 bg-warning-50 p-4 space-y-2"
    >
      <div class="flex items-start gap-2">
        <AlertTriangle :size="15" class="text-warning-600 mt-0.5 flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold text-warning-800">
            {{ rhaAdvisoryFlags.length }} Advisory RHA Reminder{{ rhaAdvisoryFlags.length !== 1 ? 's' : '' }}
          </div>
        </div>
      </div>
      <ul class="space-y-1.5">
        <li
          v-for="flag in rhaAdvisoryFlags"
          :key="flag.code"
          class="flex items-start gap-2 text-xs text-warning-700"
        >
          <AlertTriangle :size="12" class="text-warning-500 mt-0.5 flex-shrink-0" />
          <span><span class="font-medium">{{ flag.section }}:</span> {{ flag.message }}</span>
        </li>
      </ul>
    </div>

    <!-- Override recorded confirmation -->
    <div
      v-if="rhaOverride"
      class="flex items-start gap-2 px-4 py-3 bg-warning-50 border border-warning-200 rounded-xl"
    >
      <ShieldAlert :size="14" class="text-warning-600 mt-0.5 flex-shrink-0" />
      <div class="text-xs text-warning-700">
        <span class="font-semibold">RHA override recorded</span> by {{ rhaOverride.user_email }} on {{ formatDate(rhaOverride.overridden_at) }}.
        Reason: "{{ rhaOverride.reason }}"
      </div>
    </div>

    <!-- ── Empty state: no submissions yet ── -->
    <!-- Standalone v-if (NOT v-else-if chained to the rhaOverride banner) so the
         Send button stays visible after a successful override (RNT-026 fix).
         The extra guard `(rhaBlockingFlags.length === 0 || rhaOverride)` ensures
         the button is only rendered when the lease is genuinely sendable — i.e.
         either there are no blocking flags, or an authorised override is in place.
         When blocking flags exist with no override, this block is hidden entirely
         and only the red banner is shown. -->
    <div v-if="!latestSub && leaseData?.status !== 'active' && (rhaBlockingFlags.length === 0 || rhaOverride)" class="text-center py-6">
      <div class="w-12 h-12 rounded-full bg-navy/5 flex items-center justify-center mx-auto mb-3">
        <Send :size="20" class="text-navy" />
      </div>
      <div class="text-sm font-medium text-gray-800">Ready to send for signing</div>
      <p class="text-xs text-gray-400 mt-1 mb-4 max-w-xs mx-auto">
        Send this lease to your tenants to review and sign electronically. They'll get an email with a link.
      </p>
      <button
        class="btn-primary text-xs flex items-center gap-1.5 mx-auto"
        :disabled="rhaBlockingFlags.length > 0 && !rhaOverride"
        @click="openModal"
      >
        <Send :size="13" />
        Send for Signing
      </button>
    </div>

    <!-- Error banner -->
    <div
      v-if="errorMsg"
      class="flex items-center gap-2 px-4 py-3 bg-danger-50 border border-danger-100 rounded-xl text-sm text-danger-700"
    >
      <AlertCircle :size="14" class="flex-shrink-0" />
      {{ errorMsg }}
    </div>

    <div
      v-if="linkHint"
      class="flex items-center gap-2 px-4 py-3 bg-success-50 border border-success-100 rounded-xl text-sm text-success-700"
    >
      <CheckCircle2 :size="14" class="flex-shrink-0" />
      {{ linkHint }}
    </div>

    <!-- Create submission modal -->
    <BaseModal :open="showModal" size="lg" @close="closeModal">
      <template #header>
        <div class="flex items-center gap-2">
          <Send :size="16" class="text-navy" />
          <span class="font-semibold text-gray-900 text-sm">Send Lease for Signing</span>
        </div>
      </template>

      <div class="space-y-4">
        <p class="text-xs text-gray-500">
          Each signer will receive an email with a link to review and sign the lease document.
        </p>

        <!-- Signer list -->
        <div class="space-y-3">
          <div
            v-for="(signer, idx) in draftSigners"
            :key="idx"
            class="rounded-xl border p-4 space-y-3"
            :class="!signer.email ? 'border-warning-100 bg-warning-50/40' : 'border-gray-200'"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-gray-600">Signer {{ idx + 1 }}</span>
                <span
                  v-if="!signer.email"
                  class="text-micro px-1.5 py-0.5 rounded-full bg-warning-100 text-warning-700 font-medium"
                >
                  Email required
                </span>
              </div>
              <button
                v-if="draftSigners.length > 1"
                class="text-xs text-danger-400 hover:text-danger-600 transition-colors"
                @click="removeSigner(idx)"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="col-span-2">
                <label class="label">Full Name</label>
                <input v-model="signer.name" class="input" placeholder="Full legal name" />
              </div>
              <div class="col-span-2">
                <label class="label">Email *</label>
                <input
                  v-model="signer.email"
                  type="email"
                  class="input"
                  :class="!signer.email ? 'border-warning-500 focus:border-warning-500' : ''"
                  placeholder="signer@example.com"
                />
              </div>
              <div>
                <label class="label">Phone</label>
                <input v-model="signer.phone" type="tel" class="input" placeholder="+27 …" />
              </div>
              <div>
                <label class="label">Role</label>
                <input v-model="signer.role" class="input" placeholder="e.g. Tenant" />
              </div>
            </div>

            <!-- Per-signer options -->
            <div class="flex flex-wrap items-center gap-4 pt-1">
              <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none">
                <input type="checkbox" v-model="signer.send_email" class="rounded" />
                Send invitation email
              </label>
              <label
                v-if="signer.personId"
                class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none"
              >
                <input type="checkbox" v-model="signer.saveToRecord" class="rounded" />
                Save contact to tenant record
              </label>
            </div>

            <!-- Required documents -->
            <div class="pt-2 border-t border-gray-100">
              <p class="text-micro font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Required Documents</p>
              <div class="flex flex-wrap gap-3">
                <label
                  v-for="doc in SIGNER_DOC_TYPES"
                  :key="doc.key"
                  class="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    class="rounded"
                    :checked="(signer.required_documents ?? []).includes(doc.key)"
                    @change="toggleSignerDoc(signer, doc.key, ($event.target as HTMLInputElement).checked)"
                  />
                  {{ doc.label }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <button
          class="btn-ghost text-xs flex items-center gap-1.5 w-full justify-center py-2 border-dashed border border-gray-200 rounded-xl"
          @click="addSigner"
        >
          <Plus :size="13" />
          Add Another Signer
        </button>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="closeModal">Cancel</button>
        <button
          class="btn-primary flex items-center gap-2"
          :disabled="submitting || !canSubmit"
          @click="submitSigning"
        >
          <Loader2 v-if="submitting" :size="14" class="animate-spin" />
          <Send v-else :size="14" />
          Send for Signing
        </button>
      </template>
    </BaseModal>

    <!-- ── Compliance gate dialog ────────────────────────────────────────── -->
    <!-- Pops up instead of the signer-config modal when the user clicks
         "Send for Signing" while the lease has blocking RHA flags and no
         override has been recorded. Lists every blocking flag and offers
         the authorised override path inline so the user can resolve and
         continue in one go. Cancel returns them to the lease so they can
         edit the source data. -->
    <BaseModal :open="showComplianceDialog" size="md" @close="closeComplianceDialog">
      <template #header>
        <div class="flex items-center gap-2">
          <ShieldAlert :size="18" class="text-danger-600 flex-shrink-0" />
          <div>
            <div class="text-sm font-semibold text-gray-900">Cannot send for signing</div>
            <div class="text-xs text-gray-500 mt-0.5">RHA compliance issues must be resolved first</div>
          </div>
        </div>
      </template>

      <div class="space-y-4">
        <p class="text-sm text-gray-700">
          This lease has
          <span class="font-semibold text-danger-700">{{ rhaBlockingFlags.length }} blocking issue{{ rhaBlockingFlags.length !== 1 ? 's' : '' }}</span>
          that must be resolved before it can go out to signers.
        </p>

        <ul class="space-y-2 bg-danger-50 border border-danger-200 rounded-xl p-3">
          <li
            v-for="flag in rhaBlockingFlags"
            :key="flag.code"
            class="flex items-start gap-2 text-xs text-danger-700"
          >
            <XCircle :size="13" class="text-danger-500 mt-0.5 flex-shrink-0" />
            <div class="min-w-0">
              <span class="font-medium">{{ flag.section }}:</span> {{ flag.message }}
              <span v-if="flag.field" class="ml-1 text-danger-400">(field: {{ flag.field }})</span>
            </div>
          </li>
        </ul>

        <!-- Path A: instructions for non-override users -->
        <div v-if="!canRecordOverride" class="text-xs text-gray-600 leading-relaxed">
          Edit the lease to fill in the flagged fields, then return here to send for signing.
        </div>

        <!-- Path B: authorised override prompt -->
        <div v-if="canRecordOverride && !showOverrideInDialog" class="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-1.5">
          <div class="text-xs font-semibold text-gray-700">How to proceed</div>
          <ul class="text-xs text-gray-600 space-y-0.5 list-disc list-inside">
            <li>Edit the lease and resolve the flagged fields, <span class="text-gray-400">or</span></li>
            <li>Record an authorised override (reason required, logged in the audit trail)</li>
          </ul>
        </div>

        <!-- Path C: override form (expanded) -->
        <div v-if="canRecordOverride && showOverrideInDialog" class="border-t border-gray-200 pt-3 space-y-2">
          <label class="label text-danger-700 text-xs">Override reason <span class="text-danger-500">*</span></label>
          <textarea
            v-model="overrideReason"
            class="input text-xs resize-none h-20"
            placeholder="Explain why this lease may proceed despite the compliance issues…"
          />
          <p v-if="errorMsg" class="text-xs text-danger-600">{{ errorMsg }}</p>
        </div>
      </div>

      <template #footer>
        <button class="btn-ghost text-xs" @click="closeComplianceDialog">Cancel</button>
        <button
          v-if="canRecordOverride && !showOverrideInDialog"
          class="btn-secondary text-xs flex items-center gap-1.5"
          @click="showOverrideInDialog = true"
        >
          <ShieldAlert :size="13" />
          Record override instead
        </button>
        <button
          v-else-if="canRecordOverride && showOverrideInDialog"
          class="btn-primary bg-danger-600 hover:bg-danger-700 text-xs flex items-center gap-1.5"
          :disabled="!overrideReason.trim() || overrideLoading"
          @click="submitOverrideAndContinue"
        >
          <Loader2 v-if="overrideLoading" :size="13" class="animate-spin" />
          <ShieldAlert v-else :size="13" />
          Override &amp; continue
        </button>
      </template>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../../api'
import {
  Send, Mail, CheckCircle2, Clock, XCircle, AlertCircle, Eye,
  Plus, Loader2, Download, Link2, Wifi, WifiOff, PenTool, X,
  ShieldAlert, AlertTriangle,
} from 'lucide-vue-next'
import BaseModal from '../../components/BaseModal.vue'
import { useESigningSocket } from '../../composables/useESigningSocket'
import { markSigningEventSeen } from '../../composables/useGlobalSigningNotifications'
import { usePersonsStore } from '../../stores/persons'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'
import { trackEvent } from '../../plugins/plausible'

const personsStore = usePersonsStore()
const authStore = useAuthStore()
const toast = useToast()

/** Only staff and agency_admin users may record an RHA override. */
const canRecordOverride = computed(() => {
  const role = authStore.user?.role ?? ''
  return role === 'agency_admin' || role === 'admin'
})

// ── Document type config ─────────────────────────────────────────────── //
const SIGNER_DOC_TYPES = [
  { key: 'bank_statement',   label: 'Bank Statement (3 months)' },
  { key: 'id_copy',          label: 'Copy of ID / Passport' },
  { key: 'proof_of_address', label: 'Proof of Address' },
]

function toggleSignerDoc(signer: DraftSigner, key: string, checked: boolean) {
  const docs = [...(signer.required_documents ?? [])]
  if (checked && !docs.includes(key)) docs.push(key)
  else if (!checked) { const i = docs.indexOf(key); if (i > -1) docs.splice(i, 1) }
  signer.required_documents = docs
}

const props = defineProps<{
  leaseId: number
  leaseTenants?: any[]
  leaseData?: any
}>()

const emit = defineEmits<{ signed: [] }>()

// ── State ────────────────────────────────────────────────────────────── //
const submissions = ref<any[]>([])
const loading     = ref(false)
const errorMsg    = ref('')
const showModal   = ref(false)
const submitting  = ref(false)
const actionLoadingId = ref<number | string | null>(null)
const copyingLinkId = ref<number | string | null>(null)
const linkHint = ref('')

// RHA compliance state
const rhaFlags     = ref<any[]>([])
const rhaOverride  = ref<any | null>(null)
const showOverrideForm = ref(false)
const overrideReason   = ref('')
const overrideLoading  = ref(false)
// Compliance gate dialog (shown when "Send for Signing" is clicked while the
// lease has blocking RHA flags and no override). Separate from the inline
// banner-style override form (showOverrideForm) so both entry-points can be
// open independently without leaking state into each other.
const showComplianceDialog = ref(false)
const showOverrideInDialog = ref(false)

interface DraftSigner {
  name: string
  email: string
  phone: string
  role: string
  send_email: boolean
  personId?: number
  saveToRecord?: boolean
  required_documents?: string[]
}
const draftSigners = ref<DraftSigner[]>([])

/**
 * Post-submit success state. Populated immediately after a successful
 * POST /esigning/submissions/ and cleared automatically after ~15s.
 * Drives the prominent green confirmation banner above the timeline so
 * the user gets unambiguous feedback that the lease has gone out — the
 * tiny live-WS pulse dot wasn't loud enough on its own.
 */
const justSent = ref<{ count: number; recipients: string[]; at: Date } | null>(null)
let justSentTimer: ReturnType<typeof setTimeout> | null = null

// ── Computed ─────────────────────────────────────────────────────────── //
const latestSub = computed(() => submissions.value[0] ?? null)

const totalSigners = computed(() => latestSub.value?.signers?.length ?? 0)

const signedCount = computed(() =>
  (latestSub.value?.signers ?? []).filter((s: any) => isSignerDone(s)).length
)

const canSubmit = computed(() =>
  draftSigners.value.length > 0 &&
  draftSigners.value.every(s => s.name.trim() && s.email.trim())
)

const rhaBlockingFlags = computed(() =>
  rhaFlags.value.filter((f: any) => f.severity === 'blocking')
)

const rhaAdvisoryFlags = computed(() =>
  rhaFlags.value.filter((f: any) => f.severity === 'advisory')
)

// ── Real-time WebSocket updates ──────────────────────────────────────── //
const { connected: wsConnected } = useESigningSocket(
  () => latestSub.value?.id ?? null,
  (event) => {
    if (!latestSub.value) return

    // If the event carries an event_id, mark it seen in the global dedup cache
    // so the global signing notification composable in App.vue doesn't show a
    // duplicate toast while this panel is already showing live updates.
    if (event.event_id) {
      markSigningEventSeen(event.event_id)
    }

    if (event.signers) {
      latestSub.value.signers = event.signers
    }
    if (event.type === 'submission_completed') {
      latestSub.value.status = 'completed'
      if (event.signed_pdf_url) {
        latestSub.value.signed_pdf_url = event.signed_pdf_url
      }
      trackEvent('first_lease_signed')
      loadSubmissions()
      emit('signed')
    } else if (event.type === 'signer_completed') {
      // Reload to get accurate completed_at timestamps
      loadSubmissions()
    } else if (event.type === 'signer_declined') {
      latestSub.value.status = 'declined'
    }
  },
)

const canSendAgain = computed(() => {
  if (!latestSub.value) return false
  return ['declined', 'expired'].includes(latestSub.value.status)
})

// Landlord can sign: all non-landlord signers done, landlord still pending
const landlordSigner = computed(() => {
  if (!latestSub.value?.signers) return null
  return latestSub.value.signers.find((s: any) => {
    const role = (s.role ?? '').toLowerCase()
    return role.includes('landlord') || role.includes('lessor') || role.includes('owner')
  }) ?? null
})

const landlordCanSign = computed(() => {
  if (!latestSub.value || latestSub.value.status === 'completed' || latestSub.value.status === 'declined') return false
  const ls = landlordSigner.value
  if (!ls || isSignerDone(ls)) return false
  // Check all other signers are done
  return latestSub.value.signers
    .filter((s: any) => s !== ls)
    .every((s: any) => isSignerDone(s))
})

const landlordLinkLoading = ref(false)

// ── Lifecycle ────────────────────────────────────────────────────────── //
// Tracks whether this panel instance is still in the DOM — guards against
// async callbacks that complete after the component has been torn down.
let _mounted = true

onMounted(async () => {
  _mounted = true
  await Promise.all([loadSubmissions(), loadRhaFlags()])
  // autoOpen is handled by LeasesView.initView() calling openModal() via ref.
  // No autoOpen logic here — parent is responsible for triggering the modal
  // after verifying the component is still mounted and data is loaded.
})

// Poll for updates when WS is disconnected and submission is active
let pollTimer: ReturnType<typeof setInterval> | null = null
watch(() => latestSub.value?.status, (status) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (status === 'pending' || status === 'in_progress') {
    pollTimer = setInterval(() => {
      if (!wsConnected.value) loadSubmissions()
    }, 10_000)
  }
}, { immediate: true })
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (justSentTimer) clearTimeout(justSentTimer)
  _mounted = false
})

// ── Signer status helpers ───────────────────────────────────────────── //
function isSignerDone(s: any): boolean {
  const st = (s.status ?? '').toLowerCase()
  return st === 'completed' || st === 'signed'
}

function isSignerDeclined(s: any): boolean {
  return (s.status ?? '').toLowerCase() === 'declined'
}

function isSignerViewing(s: any): boolean {
  return (s.status ?? '').toLowerCase() === 'opened'
}

function signerDotClass(s: any): string {
  if (isSignerDone(s)) return 'border-success-500 bg-success-50'
  if (isSignerDeclined(s)) return 'border-danger-400 bg-danger-50'
  if (isSignerViewing(s)) return 'border-info-500 bg-info-50'
  return 'border-gray-300 bg-white'
}

function signerNarrative(s: any): string {
  const name = s.name?.split(' ')[0] || 'Signer'
  const st = (s.status ?? '').toLowerCase()
  if (st === 'completed' || st === 'signed') {
    return s.completed_at
      ? `${name} signed on ${formatDate(s.completed_at)}`
      : `${name} signed`
  }
  if (st === 'declined') return `${name} declined to sign`
  if (st === 'opened') return `${name} viewed the lease — waiting for signature`
  return `Lease sent — waiting for ${name} to open`
}

function signerNarrativeColor(s: any): string {
  const st = (s.status ?? '').toLowerCase()
  if (st === 'completed' || st === 'signed') return 'text-success-600'
  if (st === 'declined') return 'text-danger-500'
  if (st === 'opened') return 'text-info-600'
  return 'text-gray-400'
}

// ── API ──────────────────────────────────────────────────────────────── //

async function loadRhaFlags() {
  if (!props.leaseId) return
  try {
    const { data } = await api.get(`/leases/${props.leaseId}/rha-check/`)
    // Backend returns { flags, blocking, advisory, override } — map to local refs
    rhaFlags.value = data.flags ?? []
    rhaOverride.value = data.override ?? null
  } catch {
    // Silent — RHA check is a best-effort pre-flight; don't block the panel
  }
}

async function submitOverride() {
  if (!overrideReason.value.trim()) return
  overrideLoading.value = true
  errorMsg.value = ''
  try {
    const { data } = await api.post(`/leases/${props.leaseId}/rha-override/`, {
      reason: overrideReason.value.trim(),
    })
    // Backend returns { detail, override } — map to local ref
    rhaOverride.value = data.override
    showOverrideForm.value = false
    overrideReason.value = ''
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? 'Could not record override'
  } finally {
    overrideLoading.value = false
  }
}

async function loadSubmissions() {
  if (!props.leaseId) return
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await api.get('/esigning/submissions/', {
      params: { lease_id: props.leaseId },
    })
    submissions.value = data.results ?? data
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? 'Failed to load submissions'
  } finally {
    loading.value = false
  }
}

async function submitSigning() {
  if (!canSubmit.value) return
  submitting.value = true
  errorMsg.value = ''
  try {
    const savePromises = draftSigners.value
      .filter(s => s.personId && s.saveToRecord)
      .map(s => personsStore.updatePerson(s.personId!, {
        full_name: s.name,
        email: s.email,
        phone: s.phone,
      }))
    if (savePromises.length) await Promise.allSettled(savePromises)

    const emailRecipients = draftSigners.value
      .filter(s => s.send_email && s.email)
      .map(s => s.email)
    const { data } = await api.post('/esigning/submissions/', {
      lease_id: props.leaseId,
      signers: draftSigners.value,
    })
    submissions.value.unshift(data)
    closeModal()

    // Explicit success feedback — the live-update pulse alone was too subtle.
    // 1. Toast (corner): immediate, glanceable confirmation
    // 2. justSent banner (above timeline): persistent for ~15s, lists
    //    exactly who was emailed and at what time, so the user sees the
    //    delivery without any ambiguity.
    const recipientCount = emailRecipients.length
    const signerCount = draftSigners.value.length
    if (recipientCount > 0) {
      toast.success(
        recipientCount === 1
          ? `Lease sent for signing — email on its way to ${emailRecipients[0]}`
          : `Lease sent for signing — emails on their way to ${recipientCount} signers`,
      )
    } else {
      toast.success(`Lease sent for signing — ${signerCount} signer${signerCount === 1 ? '' : 's'} added`)
    }
    justSent.value = {
      count: signerCount,
      recipients: emailRecipients,
      at: new Date(),
    }
    if (justSentTimer) clearTimeout(justSentTimer)
    justSentTimer = setTimeout(() => { justSent.value = null }, 15000)

    emit('signed')
  } catch (e: any) {
    const responseData = e?.response?.data
    if (responseData?.rha_override_required) {
      // Refresh flags so the banner becomes visible
      rhaFlags.value = responseData.rha_flags ?? rhaFlags.value
      errorMsg.value = 'Blocked by RHA compliance issues. Resolve or override the flags shown above.'
    } else {
      errorMsg.value = responseData?.error ?? 'Failed to create submission'
    }
  } finally {
    submitting.value = false
  }
}

async function sendReminder(submissionId: number, signer: any) {
  actionLoadingId.value = signer.id
  errorMsg.value = ''
  linkHint.value = ''
  try {
    const { data } = await api.post(`/esigning/submissions/${submissionId}/public-link/`, {
      signer_role: signer.role,
      send_email: true,
      public_app_origin: window.location.origin,
    })
    if (data.email_sent) {
      linkHint.value = `Reminder sent to ${signer.name || signer.email}`
      window.setTimeout(() => { linkHint.value = '' }, 5000)
    } else {
      errorMsg.value = (data.email_error as string) || 'Could not send reminder email'
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not send reminder'
  } finally {
    actionLoadingId.value = null
  }
}

async function copyPublicLink(submissionId: number, signer: any) {
  copyingLinkId.value = signer.id ?? signer.role
  errorMsg.value = ''
  linkHint.value = ''
  try {
    const { data } = await api.post(`/esigning/submissions/${submissionId}/public-link/`, {
      signer_role: signer.role,
      public_app_origin: window.location.origin,
    })
    const path = (data.sign_path as string) || `/sign/${data.uuid}/`
    const full = (data.signing_url as string) || `${window.location.origin}${path}`
    try {
      await navigator.clipboard.writeText(full)
      linkHint.value = 'Signing link copied to clipboard'
    } catch {
      // Clipboard blocked — show the URL so user can copy manually
      linkHint.value = full
    }
    window.setTimeout(() => { linkHint.value = '' }, 15000)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not create signing link'
  } finally {
    copyingLinkId.value = null
  }
}

async function cancelSubmission() {
  if (!latestSub.value) return
  if (!confirm('Cancel this signing request? All signing links will be invalidated.')) return
  try {
    await api.delete(`/esigning/submissions/${latestSub.value.id}/`)
    submissions.value = submissions.value.filter((s: any) => s.id !== latestSub.value.id)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Could not cancel submission'
  }
}

async function downloadSignedPdf() {
  if (!latestSub.value) return
  try {
    const { data } = await api.get(`/esigning/submissions/${latestSub.value.id}/download/`)
    if (data.url) {
      window.open(data.url, '_blank')
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Could not fetch signed document'
  }
}

async function openLandlordSigningLink() {
  const ls = landlordSigner.value
  if (!ls?.role || !latestSub.value) return
  landlordLinkLoading.value = true
  errorMsg.value = ''
  // Open the window synchronously while still inside the click gesture so the
  // browser doesn't treat it as a popup and block it. We'll set the URL once
  // the API call resolves.
  const win = window.open('', '_blank')
  try {
    const { data } = await api.post(`/esigning/submissions/${latestSub.value.id}/public-link/`, {
      signer_role: ls.role,
      public_app_origin: window.location.origin,
    })
    const path = (data.sign_path as string) || `/sign/${data.uuid}/`
    const full = (data.signing_url as string) || `${window.location.origin}${path}`
    if (win) {
      win.location.href = full
    } else {
      window.open(full, '_blank')
    }
  } catch (e: any) {
    win?.close()
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not create signing link'
  } finally {
    landlordLinkLoading.value = false
  }
}

// ── Modal helpers ────────────────────────────────────────────────────── //
function buildDefaultSigners(): DraftSigner[] {
  const tenants = props.leaseTenants ?? []
  if (!tenants.length) {
    // Dev-only stub — no signer pre-filled in production builds
    if (import.meta.env.DEV && import.meta.env.VITE_DEV_SIGNER_EMAIL) {
      return [
        {
          name:       import.meta.env.VITE_DEV_SIGNER_NAME  || 'Dev Signer',
          email:      import.meta.env.VITE_DEV_SIGNER_EMAIL,
          phone:      import.meta.env.VITE_DEV_SIGNER_PHONE || '',
          role:       'Tenant',
          send_email: true,
        },
      ]
    }
    return []
  }
  const signers: DraftSigner[] = tenants.map((t, i) => ({
    name:               t.person?.full_name ?? t.full_name ?? '',
    email:              t.person?.email     ?? t.email     ?? '',
    phone:              t.person?.phone     ?? t.phone     ?? '',
    role:               i === 0 ? 'Tenant' : 'Co-Tenant',
    send_email:         true,
    personId:           t.person?.id ?? t.id ?? undefined,
    saveToRecord:       false,
    // Default to all doc types when not set — agent can untick in the modal
    required_documents: t.required_documents?.length ? t.required_documents : SIGNER_DOC_TYPES.map(d => d.key),
  }))

  // Auto-add landlord as last signer
  const ll = props.leaseData?.landlord_info
  if (ll?.email) {
    signers.push({
      name: ll.name ?? '', email: ll.email ?? '', phone: ll.phone ?? '',
      role: 'Landlord', send_email: false,
    })
  }
  return signers
}

async function openModal() {
  // Refresh compliance check before deciding. The in-row "Send for signing"
  // pill on LeasesView calls openModal() immediately after the panel mounts,
  // and loadRhaFlags() runs in parallel with loadSubmissions() in onMounted
  // (it does NOT block the panel's `loading` flag). Without this re-fetch
  // the very first click would race past the gate while rhaFlags is still
  // [], drop the user into the signer modal, and they'd only learn the
  // lease is blocked when the POST 4xx'd with rha_override_required.
  // Refetching here is also correct on subsequent clicks — the user may
  // have just edited the lease drawer to fix flagged fields.
  await loadRhaFlags()

  // Compliance gate: if blocking flags exist and no override is recorded,
  // intercept the click and show an explanatory dialog instead of the
  // signer-config modal. Surfaces the issues and (for authorised users) the
  // override path in-context, rather than dumping the user into a signer
  // modal that will fail on submit.
  if (rhaBlockingFlags.value.length > 0 && !rhaOverride.value) {
    showOverrideInDialog.value = false
    overrideReason.value = ''
    errorMsg.value = ''
    showComplianceDialog.value = true
    return
  }
  draftSigners.value = buildDefaultSigners()
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  draftSigners.value = []
  errorMsg.value = ''
  linkHint.value = ''
}

function closeComplianceDialog() {
  showComplianceDialog.value = false
  showOverrideInDialog.value = false
  overrideReason.value = ''
}

/** Record the RHA override, then transition straight into the signer modal so
 *  the user doesn't have to click "Send for Signing" a second time. */
async function submitOverrideAndContinue() {
  await submitOverride()
  // submitOverride() sets rhaOverride.value on success and errorMsg on failure.
  // Only proceed to the signer modal if the override actually took.
  if (rhaOverride.value) {
    closeComplianceDialog()
    draftSigners.value = buildDefaultSigners()
    showModal.value = true
  }
}

function addSigner() {
  draftSigners.value.push({
    name: '', email: '', phone: '', role: 'Signer', send_email: true,
    required_documents: SIGNER_DOC_TYPES.map(d => d.key),
  })
}

function removeSigner(idx: number) {
  draftSigners.value.splice(idx, 1)
}

// ── Display helpers ──────────────────────────────────────────────────── //
function formatDate(d: string) {
  if (!d) return ''
  const dt = new Date(d)
  const date = dt.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
  const time = dt.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
  return `${date} at ${time}`
}

// Expose openModal so parent can trigger it via ref.
// openModalWhenReady: waits for the initial submissions + RHA load to finish,
// then opens the modal only if there is no existing active submission. This is
// the safe entry-point for URL-driven deep-links (?sign=1).
async function openModalWhenReady() {
  // If still loading, wait for the in-flight onMounted promise to settle.
  // We do this by polling the loading flag (it's fast — typically one API call).
  // A simple nextTick isn't enough; use a small wait loop bounded by a timeout.
  const deadline = Date.now() + 5000
  while (loading.value && _mounted && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  if (!_mounted) return
  // Only open if there's no existing submission — don't interrupt an in-progress signing.
  if (!submissions.value.length) {
    await openModal()
  }
}
defineExpose({ openModal, openModalWhenReady })
</script>
