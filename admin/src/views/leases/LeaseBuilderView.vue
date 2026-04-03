<template>
  <div class="flex flex-col h-full -m-6 bg-white overflow-hidden">

      <!-- ── Header row 1: Property + Template ── -->
      <div class="flex items-center py-2.5 border-b border-gray-200 flex-shrink-0">
        <!-- Property selector (left — matches form panel width) -->
        <div class="w-[400px] flex-shrink-0 px-5">
          <button
            class="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg border text-left transition-colors"
            :class="selectedUnit?.propertyId
              ? 'border-navy/20 bg-navy/[0.03]'
              : 'border-gray-200 hover:border-gray-300'"
            @click="propertyModal = true"
          >
            <Building2 :size="14" class="text-gray-400 flex-shrink-0" />
            <div v-if="selectedUnit?.propertyId" class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-900 truncate">
                {{ selectedUnit.propertyName }}
                <span v-if="selectedUnit.unitNumber" class="text-gray-400 font-normal">— Unit {{ selectedUnit.unitNumber }}</span>
              </div>
              <div class="text-[11px] text-gray-400 truncate">{{ selectedUnit.address }}, {{ selectedUnit.city }}</div>
            </div>
            <div v-else class="flex-1 text-sm text-gray-400">Select property…</div>
            <ChevronRight :size="14" class="text-gray-300 flex-shrink-0" />
          </button>
        </div>

        <!-- Template selector -->
        <div class="flex items-center gap-1.5 min-w-0 flex-shrink">
          <select
            v-model="selectedTemplateId"
            class="input text-xs py-1 px-2 max-w-[200px]"
          >
            <option :value="null" disabled>Template…</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">
              {{ t.name }} v{{ t.version }}
            </option>
          </select>
        </div>

        <div class="flex-1" />

        <!-- Action buttons (right) -->
        <div class="flex items-center gap-2 px-5 flex-shrink-0">
          <div v-if="submitError" class="flex items-center gap-1 text-xs text-red-600 max-w-[200px]">
            <AlertCircle :size="12" class="flex-shrink-0" />
            <span class="truncate">{{ submitError }}</span>
          </div>
          <!-- Drafts toggle -->
          <button
            class="btn-ghost text-xs flex items-center gap-1"
            :class="showDrafts ? 'text-navy' : ''"
            @click="showDrafts = !showDrafts"
          >
            <FolderOpen :size="12" />
            Drafts
            <span v-if="drafts.length" class="bg-gray-200 text-gray-600 text-[10px] font-semibold px-1.5 py-0.5 rounded-full">{{ drafts.length }}</span>
          </button>
          <button
            class="btn-ghost text-xs flex items-center gap-1"
            :disabled="savingDraft || !selectedUnit?.propertyId"
            :title="!selectedUnit?.propertyId ? 'Select a property first' : ''"
            @click="saveDraft"
          >
            <Loader2 v-if="savingDraft" :size="12" class="animate-spin" />
            <Save v-else :size="12" />
            Save
          </button>
          <button
            class="btn-ghost text-xs flex items-center gap-1"
            :disabled="generating || !selectedTemplateId"
            @click="previewDocx"
          >
            <Loader2 v-if="generating" :size="12" class="animate-spin" />
            DOCX
          </button>
          <button class="btn-primary text-xs" :disabled="submitting" @click="doFormCreate">
            <Loader2 v-if="submitting" :size="14" class="animate-spin" />
            {{ submitting ? 'Creating…' : 'Create Lease' }}
          </button>
        </div>
      </div>

      <!-- ── Drafts panel (slides down below header) ── -->
      <div v-if="showDrafts" class="border-b border-gray-200 bg-gray-50 px-5 py-3 flex-shrink-0">
        <div v-if="loadingDrafts" class="text-xs text-gray-400">Loading drafts…</div>
        <div v-else-if="!drafts.length" class="text-xs text-gray-400">No drafts yet. Select a property and click Save to create one.</div>
        <div v-else class="space-y-1.5 max-h-[200px] overflow-y-auto">
          <div
            v-for="d in drafts"
            :key="d.id"
            class="flex items-center gap-3 px-3 py-2 rounded-lg border transition-colors cursor-pointer"
            :class="draftId === d.id ? 'border-navy/20 bg-navy/[0.03]' : 'border-gray-200 bg-white hover:border-gray-300'"
            @click="loadDraft(d)"
          >
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-900 truncate">{{ d.summary || 'Untitled draft' }}</div>
              <div class="text-[11px] text-gray-400">{{ formatDraftDate(d.updated_at) }}</div>
            </div>
            <button
              class="text-gray-400 hover:text-red-500 flex-shrink-0"
              title="Delete draft"
              @click.stop="deleteDraft(d.id)"
            >
              <X :size="12" />
            </button>
          </div>
        </div>
      </div>

      <!-- ── Property Selection Modal ── -->
      <BaseModal :open="propertyModal" title="Select Property & Unit" @close="propertyModal = false">
        <div class="space-y-3">
          <!-- Search -->
          <div class="relative">
            <input
              v-model="propertySearch"
              class="input text-sm pl-8"
              placeholder="Search properties…"
            />
            <Search :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          </div>

          <!-- Property list -->
          <div class="space-y-1.5 max-h-[400px] overflow-y-auto">
            <div
              v-for="p in filteredModalProperties"
              :key="p.id"
              class="rounded-lg border transition-colors"
              :class="modalExpandedId === p.id ? 'border-navy/20 bg-navy/[0.03]' : 'border-gray-100 hover:border-gray-200'"
            >
              <!-- Property row -->
              <button
                class="w-full flex items-center gap-2.5 px-3 py-2.5 text-left"
                @click="onModalPropertyClick(p)"
              >
                <Building2 :size="14" class="text-gray-400 flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-gray-900 truncate">{{ p.name }}</div>
                  <div class="text-[11px] text-gray-400 truncate">{{ p.address }}</div>
                </div>
                <span class="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded flex-shrink-0">
                  {{ p.units?.length || 0 }} {{ p.units?.length === 1 ? 'unit' : 'units' }}
                </span>
                <ChevronRight
                  v-if="p.units?.length > 1"
                  :size="14"
                  class="text-gray-300 flex-shrink-0 transition-transform"
                  :class="modalExpandedId === p.id ? 'rotate-90' : ''"
                />
              </button>

              <!-- Units (expanded for multi-unit properties) -->
              <div v-if="modalExpandedId === p.id && p.units?.length > 1" class="px-3 pb-2 space-y-1">
                <button
                  v-for="u in p.units"
                  :key="u.id"
                  class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-left transition-colors border"
                  :class="selectedUnit?.unitId === u.id && selectedUnit?.propertyId === p.id
                    ? 'bg-navy/10 border-navy/20'
                    : 'bg-white border-gray-100 hover:border-gray-200'"
                  @click="selectFromModal(p, u)"
                >
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900">Unit {{ u.unit_number }}</div>
                    <div class="text-[11px] text-gray-400">{{ u.bedrooms }} bed · {{ u.bathrooms }} bath</div>
                  </div>
                  <span
                    class="text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0"
                    :class="{
                      'bg-emerald-50 text-emerald-700': u.status === 'occupied',
                      'bg-blue-50 text-blue-700': u.status === 'available',
                      'bg-amber-50 text-amber-700': u.status === 'maintenance',
                    }"
                  >
                    {{ u.status }}
                  </span>
                </button>
              </div>
            </div>

            <div v-if="!filteredModalProperties.length" class="text-center py-6 text-sm text-gray-400">
              No properties found.
            </div>
          </div>
        </div>
      </BaseModal>

      <!-- ── Done screen ── -->
      <div v-if="step === 3" class="flex-1 flex items-center justify-center">
        <div class="text-center space-y-5 max-w-md">
          <div class="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
            <CheckCircle2 :size="28" class="text-emerald-500" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-lg">Lease created!</div>
            <div class="text-sm text-gray-500 mt-1">
              {{ createdLeaseNumber }}
              <span v-if="form.primary_tenant?.full_name"> &middot; {{ form.primary_tenant.full_name }}</span>
            </div>
          </div>

          <!-- What happens next -->
          <div class="bg-gray-50 rounded-xl px-5 py-4 text-left space-y-2">
            <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">What happens next</div>
            <ol class="text-sm text-gray-600 space-y-1.5 list-decimal list-inside">
              <li>Send the lease to your tenant for electronic signing</li>
              <li>They'll receive an email with a link to review and sign</li>
              <li>You'll be notified as soon as they sign</li>
            </ol>
          </div>

          <div class="flex gap-2 justify-center">
            <button class="btn-primary" @click="router.push(`/leases?expand=${createdLeaseId}&sign=1`)">
              <Send :size="14" />
              Send for Signing
            </button>
            <button class="btn-ghost" @click="router.push('/leases')">View all leases</button>
          </div>
          <button class="text-xs text-gray-400 hover:text-gray-600 transition-colors" @click="reset">
            or build another lease
          </button>
        </div>
      </div>

      <!-- ── Main split panel ── -->
      <div v-else class="flex flex-1 min-h-0">

        <!-- Left: Form -->
        <div class="w-[400px] flex-shrink-0 border-r border-gray-200 flex flex-col overflow-hidden">
          <!-- Tab bar -->
          <div class="flex border-b border-gray-200 px-5 pt-3 gap-4 flex-shrink-0">
            <button
              v-for="t in formTabs"
              :key="t.key"
              class="pb-2 text-xs font-semibold uppercase tracking-wide border-b-2 transition-colors"
              :class="formTab === t.key
                ? 'border-navy text-navy'
                : 'border-transparent text-gray-400 hover:text-gray-600'"
              @click="formTab = t.key"
            >
              {{ t.label }}
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-5 py-5 space-y-8">
            <!-- TAB: Lease Agreement -->
            <template v-if="formTab === 'lease'">
              <LeaseFormFields
                v-model:form="form"
                tab="lease"
                :errors="validationErrors"
              />

              <!-- Landlord Info -->
              <section v-if="selectedUnit" class="space-y-2">
                <div class="text-xs font-semibold text-navy uppercase tracking-widest">Landlord</div>
                <select
                  :value="selectedLandlordId"
                  @change="onLandlordChange(Number(($event.target as HTMLSelectElement).value) || null)"
                  class="input text-xs py-1.5"
                >
                  <option :value="null">— No landlord —</option>
                  <option
                    v-for="ll in allLandlords"
                    :key="ll.id"
                    :value="ll.id"
                  >
                    {{ ll.name }}{{ ll.id === defaultLandlordId ? ' (default)' : '' }}
                  </option>
                </select>
                <div v-if="landlordInfo?.name" class="border border-navy/20 rounded-lg p-3 bg-navy/5 space-y-2">
                  <div class="grid grid-cols-2 gap-1.5">
                    <div class="col-span-2">
                      <div class="text-[10px] text-gray-400 uppercase">Name</div>
                      <div class="text-xs font-medium text-gray-900">{{ landlordInfo.name }}</div>
                    </div>
                    <div>
                      <div class="text-[10px] text-gray-400 uppercase">Email</div>
                      <div class="text-xs text-gray-700">{{ landlordInfo.email || '—' }}</div>
                    </div>
                    <div>
                      <div class="text-[10px] text-gray-400 uppercase">Phone</div>
                      <div class="text-xs text-gray-700">{{ landlordInfo.phone || '—' }}</div>
                    </div>
                    <div v-if="landlordInfo.id_number">
                      <div class="text-[10px] text-gray-400 uppercase">ID / Reg no.</div>
                      <div class="text-xs text-gray-700 font-mono">{{ landlordInfo.id_number }}</div>
                    </div>
                    <div v-if="landlordInfo.address">
                      <div class="text-[10px] text-gray-400 uppercase">Address</div>
                      <div class="text-xs text-gray-700">{{ landlordInfo.address }}</div>
                    </div>
                  </div>
                  <!-- Bank account -->
                  <div v-if="landlordInfo.bank_account" class="border-t border-navy/10 pt-2 mt-2">
                    <div class="text-[10px] text-navy/50 uppercase font-semibold mb-1">Bank Account (Default)</div>
                    <div class="grid grid-cols-2 gap-1.5">
                      <div>
                        <div class="text-[10px] text-gray-400 uppercase">Bank</div>
                        <div class="text-xs text-gray-700">{{ landlordInfo.bank_account.bank_name }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] text-gray-400 uppercase">Account holder</div>
                        <div class="text-xs text-gray-700">{{ landlordInfo.bank_account.account_holder }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] text-gray-400 uppercase">Account no.</div>
                        <div class="text-xs text-gray-700 font-mono">{{ landlordInfo.bank_account.account_number }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] text-gray-400 uppercase">Branch code</div>
                        <div class="text-xs text-gray-700 font-mono">{{ landlordInfo.bank_account.branch_code }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-[10px] text-amber-600 mt-1">No bank account on file — add one on the Landlords page.</div>
                </div>
                <div v-else class="border border-amber-200 rounded-lg p-3 bg-amber-50 text-xs text-amber-700">
                  No landlord linked to this property. Link one from the property's Landlord tab or the <router-link to="/landlords" class="underline font-medium">Landlords page</router-link>.
                </div>
              </section>

              <!-- Additional Terms -->
              <section class="space-y-2">
                <div class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Additional Terms</div>
                <textarea
                  v-model="additionalTerms"
                  rows="5"
                  class="input resize-none w-full text-sm"
                  placeholder="Type any additional clauses or special conditions…"
                />
              </section>
            </template>

            <!-- TAB: Tenants -->
            <template v-if="formTab === 'tenants'">
              <LeaseFormFields
                v-model:form="form"
                tab="tenants"
                :errors="validationErrors"
              />
            </template>
          </div>

        </div>

        <!-- Right: Template preview -->
        <template v-if="!selectedTemplateId && !loadingTemplates">
          <div class="flex-1 bg-[#e8eaed] flex items-center justify-center">
            <div class="text-center text-gray-400">
              <FileSignature :size="36" class="mx-auto mb-3 opacity-30" />
              <p class="font-medium text-sm">No template selected</p>
              <p class="text-xs mt-1">Pick a template in the header to preview it here</p>
            </div>
          </div>
        </template>

        <template v-else-if="loadingContent">
          <div class="flex-1 bg-[#e8eaed] flex items-center justify-center">
            <div class="flex items-center gap-2 text-gray-400 text-sm">
              <Loader2 :size="16" class="animate-spin" /> Loading template…
            </div>
          </div>
        </template>

        <template v-else-if="selectedTemplateId && !templateHtml">
          <div class="flex-1 bg-[#e8eaed] flex items-center justify-center">
            <div class="text-center text-gray-400 space-y-3">
              <p class="text-sm">This template has no content yet.</p>
              <button
                class="btn-ghost text-xs"
                @click="router.push(`/leases/templates/${selectedTemplateId}/edit`)"
              >
                Open in template editor →
              </button>
            </div>
          </div>
        </template>

        <div v-else-if="templateHtml" class="flex-1 bg-[#f8f9fa] overflow-y-auto">
          <div class="tiptap-editor mx-auto" style="max-width: 850px; padding: 32px 0;">
            <EditorContent :editor="previewEditor" />
          </div>
        </div>
      </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, defineComponent, h, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorContent } from '@tiptap/vue-3'
import api from '../../api'
import BaseModal from '../../components/BaseModal.vue'
import useTiptapEditor from '../../composables/useTiptapEditor'
import '../../styles/tiptap-editor.css'
import {
  FileSignature, AlertCircle, Loader2, CheckCircle2, Plus, X, Save, FolderOpen,
  Building2, ChevronRight, Search, Send,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const props = defineProps<{ existingLeaseId?: number | null; templateId?: number | null }>()

interface SelectedUnit {
  propertyId: number
  propertyName: string
  unitId: number
  unitNumber: string
  address: string
  city: string
  province: string
}

// ── Inline shared sub-components ──────────────────────────────────────────

const SectionLabel = defineComponent({
  props: { text: String, color: String },
  setup(props) {
    const colors: Record<string, string> = {
      navy: 'text-navy', blue: 'text-blue-600', green: 'text-emerald-600',
      amber: 'text-amber-600', purple: 'text-violet-600',
    }
    return () => h('div', {
      class: `text-xs font-semibold uppercase tracking-wide ${colors[props.color ?? 'navy'] ?? 'text-gray-500'}`,
    }, props.text)
  },
})

const PersonBlock = defineComponent({
  props: { modelValue: Object, hasError: { type: Boolean, default: false } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function upd(field: string, val: string) {
      emit('update:modelValue', { ...props.modelValue, [field]: val })
    }
    return () => {
      const p = props.modelValue as any
      const cls = 'input text-xs py-1.5'
      const errCls = 'input text-xs py-1.5 !border-red-400 !ring-red-100'
      return h('div', { class: 'grid grid-cols-2 gap-1.5' }, [
        h('div', { class: 'col-span-2' }, [
          h('input', { class: props.hasError && !p.full_name ? errCls : cls, value: p.full_name, placeholder: 'Full name *', onInput: (e: any) => upd('full_name', e.target.value) }),
        ]),
        h('div', [
          h('input', { class: cls + ' font-mono', value: p.id_number, placeholder: 'ID / Passport', onInput: (e: any) => upd('id_number', e.target.value) }),
        ]),
        h('div', [
          h('input', { class: cls, value: p.phone, placeholder: 'Phone', onInput: (e: any) => upd('phone', e.target.value) }),
        ]),
        h('div', { class: 'col-span-2' }, [
          h('input', { class: cls, value: p.email, type: 'email', placeholder: 'Email', onInput: (e: any) => upd('email', e.target.value) }),
        ]),
      ])
    }
  },
})

const LeaseFormFields = defineComponent({
  props: {
    form: Object,
    tab: { type: String, default: '' },
    errors: { type: Array, default: () => [] },
  },
  emits: ['update:form'],
  setup(props, { emit }) {
    function updForm(field: string, val: any) {
      emit('update:form', { ...props.form, [field]: val })
    }

    return () => {
      const f = props.form as any
      const errs = props.errors as string[]
      const inputCls = 'input'
      const errInputCls = 'input !border-red-400 !ring-red-100'

      const showLease = !props.tab || props.tab === 'lease'
      const showTenants = !props.tab || props.tab === 'tenants'

      return h('div', { class: 'space-y-8' }, [
        // Lease Terms (lease tab)
        ...(showLease ? [h('section', { class: 'space-y-3' }, [
          h('div', { class: 'grid grid-cols-2 gap-3' }, [
            h('div', [h('label', { class: 'label' }, 'Start date *'), h('input', { class: errs.includes('start_date') && !f.start_date ? errInputCls : inputCls, type: 'date', value: f.start_date, onInput: (e: any) => updForm('start_date', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'End date *'), h('input', { class: errs.includes('end_date') && !f.end_date ? errInputCls : inputCls, type: 'date', value: f.end_date, onInput: (e: any) => updForm('end_date', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'Monthly rent (R) *'), h('input', { class: errs.includes('monthly_rent') && !f.monthly_rent ? errInputCls : inputCls, type: 'number', value: f.monthly_rent, onInput: (e: any) => updForm('monthly_rent', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'Deposit (R)'), h('input', { class: inputCls, type: 'number', value: f.deposit, onInput: (e: any) => updForm('deposit', e.target.value) })]),
            h('div', { class: 'col-span-2' }, [h('label', { class: 'label' }, 'Payment reference'), h('input', { class: inputCls, value: f.payment_reference, onInput: (e: any) => updForm('payment_reference', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'Max occupants'), h('input', { class: inputCls, type: 'number', value: f.max_occupants, onInput: (e: any) => updForm('max_occupants', Number(e.target.value)) })]),
            h('div', [h('label', { class: 'label' }, 'Notice period (days)'), h('input', { class: inputCls, type: 'number', value: f.notice_period_days, onInput: (e: any) => updForm('notice_period_days', Number(e.target.value)) })]),
            h('div', [h('label', { class: 'label' }, 'Early termination (months)'), h('input', { class: inputCls, type: 'number', value: f.early_termination_penalty_months, onInput: (e: any) => updForm('early_termination_penalty_months', Number(e.target.value)) })]),
            h('div', { class: 'flex items-end gap-5 pb-1 col-span-2' }, [
              h('label', { class: 'flex items-center gap-2 text-sm text-gray-700 cursor-pointer' }, [
                h('input', { type: 'checkbox', class: 'rounded', checked: f.water_included, onChange: (e: any) => updForm('water_included', e.target.checked) }),
                'Water included',
              ]),
              h('label', { class: 'flex items-center gap-2 text-sm text-gray-700 cursor-pointer' }, [
                h('input', { type: 'checkbox', class: 'rounded', checked: f.electricity_prepaid, onChange: (e: any) => updForm('electricity_prepaid', e.target.checked) }),
                'Prepaid electricity',
              ]),
            ]),
          ]),
        ])] : []),

        // Tenants (tenants tab)
        ...(showTenants ? [h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Tenants', color: 'blue' }),
            f.co_tenants?.length < 3
              ? h('button', {
                  class: 'btn-ghost text-xs px-2 py-1',
                  onClick: () => updForm('co_tenants', [...(f.co_tenants ?? []), emptyPerson()]),
                }, '+ Add tenant')
              : null,
          ]),
          h('div', { class: 'relative border border-navy/20 rounded-lg p-3 bg-navy/5' }, [
            h('div', { class: 'flex items-center justify-between mb-1.5' }, [
              h('span', { class: 'text-[10px] font-semibold text-navy/50 uppercase tracking-wide' }, 'Tenant 1'),
            ]),
            h(PersonBlock, { modelValue: f.primary_tenant, hasError: errs.includes('primary_tenant'), 'onUpdate:modelValue': (v: any) => updForm('primary_tenant', v) }),
          ]),
          ...(f.co_tenants ?? []).map((ct: any, i: number) =>
            h('div', { key: i, class: 'relative border border-navy/20 rounded-lg p-3 bg-navy/5' }, [
              h('div', { class: 'flex items-center justify-between mb-1.5' }, [
                h('span', { class: 'text-[10px] font-semibold text-navy/50 uppercase tracking-wide' }, `Tenant ${i + 2}`),
                h('button', {
                  class: 'text-gray-400 hover:text-red-500',
                  onClick: () => updForm('co_tenants', f.co_tenants.filter((_: any, j: number) => j !== i)),
                }, h(X, { size: 12 })),
              ]),
              h(PersonBlock, {
                  modelValue: ct,
                  'onUpdate:modelValue': (v: any) => updForm('co_tenants', f.co_tenants.map((c: any, j: number) => j === i ? v : c)),
                }),
            ])
          ),
        ]),

        // Occupants
        h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Occupants', color: 'green' }),
            h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('occupants', [...(f.occupants ?? []), { ...emptyPerson(), relationship_to_tenant: 'self' }]),
            }, '+ Add'),
          ]),
          ...(f.occupants?.length
            ? f.occupants.map((oc: any, i: number) =>
                h('div', { key: i, class: 'relative border border-emerald-100 rounded-lg p-3 bg-emerald-50/40' }, [
                  h('div', { class: 'flex items-center justify-end mb-1.5' }, [
                    h('button', { class: 'text-gray-400 hover:text-red-500', onClick: () => updForm('occupants', f.occupants.filter((_: any, j: number) => j !== i)) }, h(X, { size: 12 })),
                  ]),
                  h(PersonBlock, { modelValue: oc, 'onUpdate:modelValue': (v: any) => updForm('occupants', f.occupants.map((o: any, j: number) => j === i ? v : o)) }),
                  h('div', { class: 'mt-1.5' }, [
                    h('input', { class: 'input text-xs py-1.5', value: oc.relationship_to_tenant, placeholder: 'Relationship (self, spouse, child…)', onInput: (e: any) => updForm('occupants', f.occupants.map((o: any, j: number) => j === i ? { ...o, relationship_to_tenant: e.target.value } : o)) }),
                  ]),
                ])
              )
            : [h('p', { class: 'text-xs text-gray-400' }, 'None')]),
        ]),

        h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Guarantors / Sureties', color: 'amber' }),
            h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('guarantors', [...(f.guarantors ?? []), { ...emptyPerson(), for_tenant: '' }]),
            }, '+ Add'),
          ]),
          ...(f.guarantors?.length
            ? f.guarantors.map((g: any, i: number) =>
                h('div', { key: i, class: 'relative border border-amber-100 rounded-lg p-3 bg-amber-50/40' }, [
                  h('div', { class: 'flex items-center justify-end mb-1.5' }, [
                    h('button', { class: 'text-gray-400 hover:text-red-500', onClick: () => updForm('guarantors', f.guarantors.filter((_: any, j: number) => j !== i)) }, h(X, { size: 12 })),
                  ]),
                  h(PersonBlock, { modelValue: g, 'onUpdate:modelValue': (v: any) => updForm('guarantors', f.guarantors.map((gg: any, j: number) => j === i ? v : gg)) }),
                  h('div', { class: 'mt-1.5' }, [
                    h('input', { class: 'input text-xs py-1.5', value: g.for_tenant, placeholder: 'Covers tenant (name)', onInput: (e: any) => updForm('guarantors', f.guarantors.map((gg: any, j: number) => j === i ? { ...gg, for_tenant: e.target.value } : gg)) }),
                  ]),
                ])
              )
            : [h('p', { class: 'text-xs text-gray-400' }, 'None')]),
        ])] : []),
      ])
    }
  },
})

// ── State ──────────────────────────────────────────────────────────────────

const step = ref(1)
const formTab = ref<'lease' | 'tenants'>('lease')
const formTabs = [
  { key: 'lease' as const, label: 'Lease Agreement' },
  { key: 'tenants' as const, label: 'Lessee' },
]
const properties = ref<any[]>([])
const selectedUnit = ref<SelectedUnit | null>(null)

// ── Property modal ────────────────────────────────────────────────────────
const propertyModal = ref(false)
const propertySearch = ref('')
const modalExpandedId = ref<number | null>(null)

const filteredModalProperties = computed(() => {
  if (!propertySearch.value) return properties.value
  const q = propertySearch.value.toLowerCase()
  return properties.value.filter(p =>
    p.name.toLowerCase().includes(q) ||
    (p.address ?? '').toLowerCase().includes(q) ||
    (p.city ?? '').toLowerCase().includes(q)
  )
})

function onModalPropertyClick(p: any) {
  // No units or single unit → auto-select and close
  if (!p.units?.length) {
    selectFromModal(p, null)
    return
  }
  if (p.units.length === 1) {
    selectFromModal(p, p.units[0])
    return
  }
  // Multi-unit → toggle expand
  modalExpandedId.value = modalExpandedId.value === p.id ? null : p.id
}

function selectFromModal(property: any, unit: any) {
  selectedUnit.value = {
    propertyId: property.id,
    propertyName: property.name,
    unitId: unit?.id ?? 0,
    unitNumber: unit?.unit_number ?? '',
    address: property.address,
    city: property.city,
    province: property.province,
  }
  propertyModal.value = false
  propertySearch.value = ''
  modalExpandedId.value = null
}

// ── Landlord selection ────────────────────────────────────────────────────
interface LandlordInfo {
  name: string; email: string; phone: string; id_number: string; address: string
  landlord_name: string
  bank_account: { bank_name: string; account_holder: string; account_number: string; branch_code: string; account_type: string } | null
}
const allLandlords = ref<any[]>([])
const selectedLandlordId = ref<number | null>(null)
const defaultLandlordId = ref<number | null>(null)
const landlordInfo = ref<LandlordInfo | null>(null)

async function loadAllLandlords() {
  try {
    const { data } = await api.get('/properties/landlords/')
    allLandlords.value = data.results ?? data
  } catch { /* non-fatal */ }
}

function landlordInfoFromRaw(ll: any): LandlordInfo & { raw: any } {
  const name = ll.representative_name || ll.name
  const email = ll.representative_email || ll.email
  const phone = ll.representative_phone || ll.phone
  const idNum = ll.representative_id_number || ll.registration_number || ll.id_number
  const addr = ll.address
  const addrStr = addr ? [addr.street, addr.city, addr.province, addr.postal_code].filter(Boolean).join(', ') : ''
  const defaultBank = (ll.bank_accounts ?? []).find((ba: any) => ba.is_default) ?? (ll.bank_accounts ?? [])[0] ?? null
  return {
    name, email, phone, id_number: idNum, address: addrStr,
    landlord_name: ll.name,
    bank_account: defaultBank ? {
      bank_name: defaultBank.bank_name, account_holder: defaultBank.account_holder,
      account_number: defaultBank.account_number, branch_code: defaultBank.branch_code,
      account_type: defaultBank.account_type,
    } : null,
    raw: ll,
  }
}

async function fetchLandlordForProperty(propertyId: number) {
  landlordInfo.value = null
  selectedLandlordId.value = null
  defaultLandlordId.value = null
  try {
    const { data } = await api.get(`/properties/ownerships/?property=${propertyId}`)
    const ownerships = data.results ?? data
    const ownership = ownerships.find((o: any) => o.is_current)
    if (!ownership) return
    if (ownership.landlord) {
      defaultLandlordId.value = ownership.landlord
      selectedLandlordId.value = ownership.landlord
      const ll = allLandlords.value.find(l => l.id === ownership.landlord)
      if (ll) {
        landlordInfo.value = landlordInfoFromRaw(ll)
      } else {
        const { data: llData } = await api.get(`/properties/landlords/${ownership.landlord}/`)
        landlordInfo.value = landlordInfoFromRaw(llData)
      }
    }
  } catch { /* non-fatal */ }
}

function onLandlordChange(id: number | null) {
  selectedLandlordId.value = id
  if (!id) { landlordInfo.value = null; return }
  const ll = allLandlords.value.find(l => l.id === id)
  if (ll) landlordInfo.value = landlordInfoFromRaw(ll)
}

// Sync selected property/unit into form fields for preview
watch(selectedUnit, (su) => {
  if (su) {
    form.value.property = {
      ...form.value.property,
      name: su.propertyName,
      address: su.address,
      city: su.city,
      province: su.province,
    }
    if (su.unitNumber) {
      form.value.unit = { ...form.value.unit, unit_number: su.unitNumber }
    }
    fetchLandlordForProperty(su.propertyId)
  }
})
const submitting = ref(false)
const generating = ref(false)
const savingDraft = ref(false)
const draftId = ref<number | null>(null)
const submitError = ref('')
const validationErrors = ref<string[]>([])
const createdLeaseNumber = ref('')
const createdLeaseId = ref<number | null>(null)

function emptyPerson() {
  return { full_name: '', id_number: '', phone: '', email: '' }
}

const form = ref({
  property: { name: '', address: '', city: '', province: '', postal_code: '', property_type: 'house' },
  unit: { unit_number: '1', bedrooms: 1, bathrooms: 1 },
  start_date: '', end_date: '',
  monthly_rent: '', deposit: '',
  payment_reference: '',
  max_occupants: 1,
  water_included: true,
  electricity_prepaid: true,
  water_limit_litres: 4000,
  notice_period_days: 30,
  early_termination_penalty_months: 3,
  primary_tenant: emptyPerson(),
  co_tenants: [] as any[],
  occupants: [] as any[],
  guarantors: [] as any[],
})

const additionalTerms = ref('')

// Clear validation errors when form changes
watch(form, () => { if (validationErrors.value.length) validationErrors.value = [] }, { deep: true })

// ── Template management ────────────────────────────────────────────────────

const templates = ref<any[]>([])
const loadingTemplates = ref(false)
const loadingContent = ref(false)
const templateFields = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const selectedTemplateName = computed(() =>
  templates.value.find(t => t.id === selectedTemplateId.value)?.name || ''
)
const templateHtml = ref('')

async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const { data } = await api.get('/leases/templates/')
    templates.value = data.results ?? data
    // Auto-select: prefer query param, then prop, then first active, then first
    const qTemplate = route.query.template ? Number(route.query.template) : null
    const preferredId = qTemplate || props.templateId
    const preferred = preferredId
      ? templates.value.find(t => t.id === preferredId)
      : templates.value.find(t => t.is_active) ?? templates.value[0]
    if (preferred) selectedTemplateId.value = preferred.id
  } catch { /* non-fatal */ }
  finally { loadingTemplates.value = false }
}

async function fetchTemplateContent(id: number) {
  loadingContent.value = true
  templateHtml.value = ''
  templateFields.value = []
  try {
    const { data } = await api.get(`/leases/templates/${id}/`)
    const raw = data.content_html ?? ''
    // Parse JSON format (v1) or fall back to legacy HTML
    try {
      const doc = JSON.parse(raw)
      if ((doc.v === 1 || doc.v === 2) && typeof doc.html === 'string') {
        templateHtml.value = doc.html
        templateFields.value = doc.fields ?? []
      } else {
        templateHtml.value = raw
      }
    } catch {
      templateHtml.value = raw
    }
  } catch { /* non-fatal */ }
  finally { loadingContent.value = false }
}

watch(selectedTemplateId, (id) => {
  if (id) fetchTemplateContent(id)
  else templateHtml.value = ''
})

// ── Template preview with filled values ───────────────────────────────────

function escHtml(s: string) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function _deriveFieldParty(fieldName: string): string {
  const lower = fieldName.toLowerCase()
  if (lower.startsWith('landlord')) return 'landlord'
  if (/^tenant\d?_/.test(lower) || lower === 'tenant_name') return 'tenant'
  if (lower.startsWith('occupant')) return 'occupant'
  if (lower.startsWith('witness')) return 'witness'
  if (/^(property|unit|address|city|suburb|area_code|province|postal)/.test(lower)) return 'property'
  if (/^(lease|start_date|end_date|notice|early_termination)/.test(lower)) return 'lease'
  if (/^(rent|monthly|deposit|escalation|payment|bank|account|branch)/.test(lower)) return 'financial'
  return 'general'
}

// ── Read-only TipTap preview editor ──────────────────────────────────────
const { editor: previewEditor } = useTiptapEditor({
  editable: false,
  placeholder: '',
})

// Provide merge field values to TipTap node views (MergeFieldComponent reads via inject)
const mergeFieldPreviewValues = computed(() => {
  const vals = buildDocxContext() as Record<string, string>
  // Filter out placeholder dashes so the component shows the chip instead
  const clean: Record<string, string> = {}
  for (const [k, v] of Object.entries(vals)) {
    if (v && String(v).trim() && String(v) !== '—') clean[k] = String(v)
  }
  return clean
})
provide('mergeFieldPreviewValues', mergeFieldPreviewValues)

onBeforeUnmount(() => {
  previewEditor.value?.destroy()
})

const previewHtml = computed(() => {
  if (!templateHtml.value) return ''
  const vals = buildDocxContext() as Record<string, any>

  let html = templateHtml.value

  // Replace <span data-merge-field="X">...</span> with filled value or placeholder
  html = html.replace(/<span[^>]*data-merge-field="([^"]+)"[^>]*>[\s\S]*?<\/span>/g, (_, field) => {
    const lower = field.toLowerCase()

    // Signing fields → render as visual boxes
    if (lower.endsWith('_signature')) {
      const label = field.replace(/_signature$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border:2px dashed #1e3a5f;border-radius:6px;padding:8px 16px;min-width:180px;text-align:center;color:#1e3a5f;font-size:9pt;font-weight:600;margin:4px 0;">✍ ${escHtml(label)} Signature</span>`
    }
    if (lower.endsWith('_initials')) {
      const label = field.replace(/_initials$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border:2px dashed #1e3a5f;border-radius:6px;padding:4px 12px;min-width:80px;text-align:center;color:#1e3a5f;font-size:8pt;font-weight:600;margin:4px 0;">AB ${escHtml(label)}</span>`
    }
    if (lower.endsWith('_date_signed')) {
      const label = field.replace(/_date_signed$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border-bottom:1px solid #999;padding:2px 8px;min-width:100px;color:#999;font-size:8pt;">Date (${escHtml(label)})</span>`
    }

    const party = _deriveFieldParty(field)
    const val = vals[field]
    if (val !== undefined && String(val).trim() && String(val) !== '—') {
      return `<span class="pf-filled" data-party="${party}">${escHtml(String(val))}</span>`
    }
    return `<span class="pf-empty" data-party="${party}">{{${field}}}</span>`
  })

  // Also replace bare {{ field }} jinja-style placeholders
  html = html.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, field) => {
    const lower = field.toLowerCase()

    // Signing fields → render as visual boxes (not data placeholders)
    if (lower.endsWith('_signature')) {
      const label = field.replace(/_signature$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border:2px dashed #1e3a5f;border-radius:6px;padding:8px 16px;min-width:180px;text-align:center;color:#1e3a5f;font-size:9pt;font-weight:600;margin:4px 0;">✍ ${escHtml(label)} Signature</span>`
    }
    if (lower.endsWith('_initials')) {
      const label = field.replace(/_initials$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border:2px dashed #1e3a5f;border-radius:6px;padding:4px 12px;min-width:80px;text-align:center;color:#1e3a5f;font-size:8pt;font-weight:600;margin:4px 0;">AB ${escHtml(label)}</span>`
    }
    if (lower.endsWith('_date_signed')) {
      const label = field.replace(/_date_signed$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      return `<span class="pf-sig-box" style="display:inline-block;border-bottom:1px solid #999;padding:2px 8px;min-width:100px;color:#999;font-size:8pt;">Date (${escHtml(label)})</span>`
    }

    const party = _deriveFieldParty(field)
    const val = vals[field]
    if (val !== undefined && String(val).trim() && String(val) !== '—') {
      return `<span class="pf-filled" data-party="${party}">${escHtml(String(val))}</span>`
    }
    return `<span class="pf-empty" data-party="${party}">{{${field}}}</span>`
  })

  // Append additional terms
  if (additionalTerms.value.trim()) {
    html += `<div class="pf-additional-terms"><strong>Additional Terms &amp; Conditions</strong><div class="pf-terms-body">${escHtml(additionalTerms.value)}</div></div>`
  }

  return html
})

// Sync previewHtml → read-only TipTap editor
watch(previewHtml, (html) => {
  if (previewEditor.value) {
    previewEditor.value.commands.setContent(html || '<p></p>')
  }
})

// ── Drafts state (must be before onMounted) ──────────────────────────────
const showDrafts = ref(false)
const drafts = ref<any[]>([])
const loadingDrafts = ref(false)

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(async () => {
  api.get('/properties/?page_size=500').then(({ data }) => {
    properties.value = data.results ?? data
  })
  loadAllLandlords()
  loadTemplates()
  await fetchDrafts()

  // Load draft from query param (?draft=ID)
  const qDraft = route.query.draft
  if (qDraft) {
    const id = Number(qDraft)
    const match = drafts.value.find((d: any) => d.id === id)
    if (match) {
      loadDraft(match)
    } else {
      // Fetch individually if not in list
      try {
        const { data } = await api.get(`/leases/builder/drafts/${id}/`)
        loadDraft(data)
      } catch { /* draft not found — ignore */ }
    }
  }
})

// Refresh drafts when panel opens
watch(showDrafts, (v) => { if (v) fetchDrafts() })

// ── Smart Form: create via import ──────────────────────────────────────────

async function doFormCreate() {
  submitError.value = ''
  validationErrors.value = []
  const f = form.value
  const errs: string[] = []
  if (!f.primary_tenant.full_name) errs.push('primary_tenant')
  if (!f.start_date) errs.push('start_date')
  if (!f.end_date) errs.push('end_date')
  if (!f.monthly_rent) errs.push('monthly_rent')
  if (errs.length) {
    validationErrors.value = errs
    if (errs.includes('primary_tenant')) { formTab.value = 'tenants' }
    else { formTab.value = 'lease' }
    submitError.value = 'Please fill in all required fields.'
    return
  }
  submitting.value = true
  try {
    const payload: any = { ...form.value }
    if (selectedUnit.value) {
      payload.property_id = selectedUnit.value.propertyId
      if (selectedUnit.value.unitId) payload.unit_id = selectedUnit.value.unitId
    }
    const { data } = await api.post('/leases/import/', payload)
    createdLeaseNumber.value = data.lease_number
    createdLeaseId.value = data.id
    step.value = 3
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.message ?? 'Failed to create lease'
    submitError.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    submitting.value = false
  }
}

// ── Draft save/load ─────────────────────────────────────────────────────────

function buildDraftState() {
  return {
    form: form.value,
    additionalTerms: additionalTerms.value,
    selectedUnit: selectedUnit.value,
    selectedTemplateId: selectedTemplateId.value,
  }
}

function loadDraftState(state: any) {
  if (state.form) form.value = state.form
  if (state.additionalTerms) additionalTerms.value = state.additionalTerms
  if (state.selectedUnit) selectedUnit.value = state.selectedUnit
  if (state.selectedTemplateId) selectedTemplateId.value = state.selectedTemplateId
}

async function fetchDrafts() {
  loadingDrafts.value = true
  try {
    const { data } = await api.get('/leases/builder/drafts/')
    drafts.value = data
  } catch { /* silent */ }
  finally { loadingDrafts.value = false }
}

async function saveDraft() {
  if (!selectedUnit.value?.propertyId) return
  savingDraft.value = true
  try {
    const payload = { form_state: buildDraftState(), template_id: selectedTemplateId.value }
    if (draftId.value) {
      await api.put(`/leases/builder/drafts/${draftId.value}/`, payload)
    } else {
      const { data } = await api.post('/leases/builder/drafts/new/', payload)
      draftId.value = data.id
    }
    await fetchDrafts()
  } catch { /* silent */ }
  finally { savingDraft.value = false }
}

function loadDraft(d: any) {
  draftId.value = d.id
  const state = d.current_state ?? d.form_state
  if (state) loadDraftState(state)
  showDrafts.value = false
}

async function deleteDraft(id: number) {
  try {
    await api.delete(`/leases/builder/drafts/${id}/`)
    drafts.value = drafts.value.filter(d => d.id !== id)
    if (draftId.value === id) draftId.value = null
  } catch { /* silent */ }
}

function formatDraftDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ── Smart Form: preview DOCX ───────────────────────────────────────────────

async function previewDocx() {
  generating.value = true
  try {
    const context = buildDocxContext()
    const resp = await api.post('/leases/generate/', { template_id: selectedTemplateId.value, context }, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `lease_preview_${form.value.primary_tenant.full_name || 'draft'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // silently ignore preview errors
  } finally {
    generating.value = false
  }
}

function numberToWords(n: number): string {
  if (!n && n !== 0) return ''
  if (n === 0) return 'Zero'
  const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
  function chunk(num: number): string {
    if (num === 0) return ''
    if (num < 20) return ones[num]
    if (num < 100) return tens[Math.floor(num / 10)] + (num % 10 ? '-' + ones[num % 10] : '')
    return ones[Math.floor(num / 100)] + ' Hundred' + (num % 100 ? ' and ' + chunk(num % 100) : '')
  }
  const val = Math.floor(Math.abs(n))
  const cents = Math.round((Math.abs(n) - val) * 100)
  const parts: string[] = []
  if (val >= 1_000_000) { parts.push(chunk(Math.floor(val / 1_000_000)) + ' Million'); }
  const remainder = val % 1_000_000
  if (remainder >= 1000) { parts.push(chunk(Math.floor(remainder / 1000)) + ' Thousand'); }
  const last = remainder % 1000
  if (last > 0) { if (parts.length && last < 100) parts.push('and'); parts.push(chunk(last)); }
  let result = parts.join(' ')
  if (cents > 0) result += ` and ${chunk(cents)} Cents`
  return result + ' Rand'
}

function buildDocxContext() {
  const f = form.value
  const su = selectedUnit.value
  return {
    // Landlord fields — cover all common template merge field names
    landlord_name: landlordInfo.value?.landlord_name || landlordInfo.value?.name || '—',
    landlord_full_name: landlordInfo.value?.landlord_name || landlordInfo.value?.name || '—',
    landlord_entity_name: landlordInfo.value?.landlord_name || '—',
    landlord_id: landlordInfo.value?.id_number || '—',
    landlord_id_number: landlordInfo.value?.id_number || '—',
    landlord_registration_no: landlordInfo.value?.raw?.registration_number || '—',
    landlord_registration_number: landlordInfo.value?.raw?.registration_number || '—',
    landlord_vat_no: landlordInfo.value?.raw?.vat_number || '—',
    landlord_vat_number: landlordInfo.value?.raw?.vat_number || '—',
    landlord_representative: landlordInfo.value?.raw?.representative_name || '—',
    landlord_representative_name: landlordInfo.value?.raw?.representative_name || '—',
    landlord_representative_id: landlordInfo.value?.raw?.representative_id_number || '—',
    landlord_title: landlordInfo.value?.raw?.landlord_type === 'company' ? 'Director' : landlordInfo.value?.raw?.landlord_type === 'trust' ? 'Trustee' : 'Owner',
    landlord_address: landlordInfo.value?.address || su?.address || f.property.address,
    landlord_physical_address: landlordInfo.value?.address || su?.address || f.property.address,
    landlord_phone: landlordInfo.value?.phone || '—',
    landlord_contact: landlordInfo.value?.phone || '—',
    landlord_contact_no: landlordInfo.value?.phone || '—',
    landlord_email: landlordInfo.value?.email || '—',
    property_address: su?.address || f.property.address,
    unit_number: su?.unitNumber || f.unit.unit_number,
    city: su?.city || f.property.city,
    province: su?.province || f.property.province,
    tenant_name: f.primary_tenant.full_name,
    tenant_id: f.primary_tenant.id_number,
    tenant_phone: f.primary_tenant.phone,
    tenant_email: f.primary_tenant.email,
    co_tenants: f.co_tenants.map((c: any) => c.full_name).filter(Boolean).join(', ') || '—',
    lease_start: f.start_date,
    lease_end: f.end_date,
    monthly_rent: f.monthly_rent ? `R ${Number(f.monthly_rent).toLocaleString('en-ZA')}` : '',
    monthly_rent_words: f.monthly_rent ? numberToWords(Number(f.monthly_rent)) : '',
    deposit: f.deposit ? `R ${Number(f.deposit).toLocaleString('en-ZA')}` : '',
    deposit_words: f.deposit ? numberToWords(Number(f.deposit)) : '',
    payment_reference: f.payment_reference,
    escalation_percent: '—',
    escalation_date: '—',
    notice_period_days: f.notice_period_days,
    early_termination_months: f.early_termination_penalty_months,
    water_included: f.water_included ? 'Included' : 'Excluded',
    water_limit: f.water_limit_litres,
    electricity_prepaid: f.electricity_prepaid ? 'Prepaid' : 'Included in rent',
    max_occupants: f.max_occupants,
    pets_allowed: '—',
    // Bank account (from landlord default) — both generic and landlord-prefixed
    bank_name: landlordInfo.value?.bank_account?.bank_name || '—',
    account_holder: landlordInfo.value?.bank_account?.account_holder || '—',
    account_number: landlordInfo.value?.bank_account?.account_number || '—',
    branch_code: landlordInfo.value?.bank_account?.branch_code || '—',
    account_type: landlordInfo.value?.bank_account?.account_type || '—',
    landlord_bank_name: landlordInfo.value?.bank_account?.bank_name || '—',
    landlord_bank_branch_code: landlordInfo.value?.bank_account?.branch_code || '—',
    landlord_bank_account_no: landlordInfo.value?.bank_account?.account_number || '—',
    landlord_bank_account_holder: landlordInfo.value?.bank_account?.account_holder || '—',
    landlord_bank_account_type: landlordInfo.value?.bank_account?.account_type || '—',
  }
}

// ── Reset ──────────────────────────────────────────────────────────────────

function reset() {
  step.value = 1
  submitError.value = ''
  createdLeaseNumber.value = ''
  createdLeaseId.value = null
  additionalTerms.value = ''
  selectedUnit.value = null
  form.value = {
    property: { name: '', address: '', city: '', province: '', postal_code: '', property_type: 'house' },
    unit: { unit_number: '1', bedrooms: 1, bathrooms: 1 },
    start_date: '', end_date: '', monthly_rent: '', deposit: '',
    payment_reference: '', max_occupants: 1,
    water_included: true, electricity_prepaid: true,
    water_limit_litres: 4000, notice_period_days: 30,
    early_termination_penalty_months: 3,
    primary_tenant: emptyPerson(),
    co_tenants: [], occupants: [], guarantors: [],
  }
}
</script>

<style scoped>
/* Preview fill/empty merge field styling handled by shared tiptap-editor.css */
</style>
