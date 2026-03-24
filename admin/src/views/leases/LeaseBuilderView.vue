<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex flex-col bg-white overflow-hidden">

      <!-- ── Header ──────────────────────────────────────────────────────── -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center">
            <FileSignature :size="14" class="text-white" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-sm">Lease Builder</div>
            <div class="text-xs text-gray-400">Build a South African residential lease from scratch</div>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <!-- Step indicator -->
          <div class="hidden sm:flex items-center gap-1.5 text-xs text-gray-400">
            <span :class="step >= 1 ? 'text-navy font-medium' : ''">Mode</span>
            <ChevronRight :size="12" />
            <span :class="step >= 2 ? 'text-navy font-medium' : ''">
              {{ mode === 'chat' ? 'AI Chat' : 'Smart Form' }}
            </span>
            <ChevronRight :size="12" />
            <span :class="step >= 3 ? 'text-navy font-medium' : ''">Done</span>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <X :size="18" />
          </button>
        </div>
      </div>

      <!-- ── Step 1: Choose mode ─────────────────────────────────────────── -->
      <div v-if="step === 1" class="flex-1 flex items-center justify-center p-8">
        <div class="w-full max-w-2xl space-y-6">
          <div class="text-center space-y-1">
            <h2 class="text-xl font-semibold text-gray-900">How would you like to build this lease?</h2>
            <p class="text-sm text-gray-500">Both modes produce the same result — choose what suits you best.</p>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Smart Form -->
            <button
              @click="selectMode('form')"
              class="text-left border-2 rounded-2xl p-6 transition-all hover:shadow-md"
              :class="mode === 'form' ? 'border-navy bg-navy/5 shadow-md' : 'border-gray-200 hover:border-gray-300'"
            >
              <div class="w-10 h-10 rounded-xl bg-lavender flex items-center justify-center mb-4">
                <FormInput :size="20" class="text-navy" />
              </div>
              <div class="font-semibold text-gray-900">Smart Form</div>
              <div class="text-sm text-gray-500 mt-1">
                Fill in all fields directly. Instant, precise, full control.
                Best when you have all the details ready.
              </div>
            </button>

            <!-- AI Builder -->
            <button
              @click="selectMode('chat')"
              class="text-left border-2 rounded-2xl p-6 transition-all hover:shadow-md"
              :class="mode === 'chat' ? 'border-navy bg-navy/5 shadow-md' : 'border-gray-200 hover:border-gray-300'"
            >
              <div class="w-10 h-10 rounded-xl bg-lavender flex items-center justify-center mb-4">
                <Sparkles :size="20" class="text-navy" />
              </div>
              <div class="font-semibold text-gray-900">AI Builder</div>
              <div class="text-sm text-gray-500 mt-1">
                Chat with AI — describe the lease and it asks what's missing,
                flags RHA compliance issues, and fills the form for you.
              </div>
            </button>
          </div>

          <!-- Template -->
          <div class="border border-gray-200 rounded-2xl p-4 space-y-2 bg-gray-50">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <FileSignature :size="14" class="text-gray-400" />
                <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">DOCX Template</span>
              </div>
              <label
                class="btn-ghost text-xs cursor-pointer"
                :class="uploadingTemplate ? 'opacity-50 pointer-events-none' : ''"
              >
                <Loader2 v-if="uploadingTemplate" :size="12" class="animate-spin" />
                <Plus v-else :size="12" />
                {{ uploadingTemplate ? 'Uploading…' : 'Upload template' }}
                <input
                  ref="templateFileInput"
                  type="file"
                  accept=".docx,.pdf"
                  class="hidden"
                  @change="handleTemplateUpload"
                />
              </label>
            </div>
            <div v-if="templateUploadError" class="text-xs text-red-500">{{ templateUploadError }}</div>
            <div v-if="activeTemplate" class="flex items-center gap-2 text-sm text-gray-700">
              <div class="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0"></div>
              <span class="font-medium">{{ activeTemplate.name }}</span>
              <span class="text-gray-400 text-xs">v{{ activeTemplate.version }}</span>
              <span v-if="activeTemplate.fields_schema?.length" class="text-gray-400 text-xs">
                · {{ activeTemplate.fields_schema.length }} fields
              </span>
            </div>
            <div v-else class="text-xs text-amber-600 flex items-center gap-1.5">
              <AlertCircle :size="12" />
              No template uploaded yet — upload a .docx or .pdf to enable document generation.
            </div>
          </div>

          <div class="flex justify-center pt-2">
            <button
              class="btn-primary px-8"
              :disabled="!mode"
              @click="startMode"
            >
              Continue
              <ChevronRight :size="14" />
            </button>
          </div>
        </div>
      </div>

      <!-- ── Step 2a: Smart Form ─────────────────────────────────────────── -->
      <template v-if="step === 2 && mode === 'form'">
        <div class="flex-1 overflow-y-auto">
          <div class="max-w-xl mx-auto px-6 py-8 space-y-8">
            <LeaseFormFields
              v-model:form="form"
              v-model:useExistingProperty="useExistingProperty"
              v-model:useExistingUnit="useExistingUnit"
              :properties="properties"
            />
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 flex-shrink-0 bg-white">
          <div v-if="submitError" class="flex items-center gap-2 text-sm text-red-600">
            <AlertCircle :size="14" />
            {{ submitError }}
          </div>
          <div v-else class="flex items-center gap-3">
            <button
              class="btn-ghost"
              :disabled="generating"
              @click="previewDocx"
            >
              <Loader2 v-if="generating" :size="13" class="animate-spin" />
              {{ generating ? 'Generating…' : 'Preview DOCX' }}
            </button>
          </div>
          <div class="flex gap-2 ml-auto">
            <button class="btn-ghost" @click="step = 1">Back</button>
            <button class="btn-primary" :disabled="submitting" @click="doFormCreate">
              <Loader2 v-if="submitting" :size="14" class="animate-spin" />
              {{ submitting ? 'Creating…' : 'Create Lease' }}
            </button>
          </div>
        </div>
      </template>

      <!-- ── Step 2b: AI Chat ────────────────────────────────────────────── -->
      <template v-if="step === 2 && mode === 'chat'">
        <div class="flex-1 flex overflow-hidden">

          <!-- Left: Chat panel -->
          <div class="flex flex-col w-full lg:w-1/2 border-r border-gray-100">

            <!-- Chat messages -->
            <div ref="chatScrollEl" class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
              <div
                v-for="(msg, i) in chatMessages"
                :key="i"
                class="flex gap-2"
                :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
              >
                <!-- Avatar -->
                <div
                  class="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold mt-0.5"
                  :class="msg.role === 'assistant' ? 'bg-navy/10 text-navy' : 'bg-gray-200 text-gray-600'"
                >
                  {{ msg.role === 'assistant' ? 'AI' : 'You' }}
                </div>
                <div
                  class="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm"
                  :class="msg.role === 'user'
                    ? 'bg-navy text-white rounded-tr-sm'
                    : 'bg-gray-100 text-gray-800 rounded-tl-sm'"
                >
                  {{ msg.content }}
                </div>
              </div>

              <!-- Typing indicator -->
              <div v-if="chatThinking" class="flex gap-2">
                <div class="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold bg-navy/10 text-navy mt-0.5">AI</div>
                <div class="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1">
                  <span v-for="i in 3" :key="i" class="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" :style="`animation-delay:${(i-1)*0.15}s`" />
                </div>
              </div>
            </div>

            <!-- RHA flags -->
            <div v-if="rhaFlags.length" class="px-4 py-2 border-t border-orange-100 bg-orange-50 space-y-1">
              <div
                v-for="(flag, i) in rhaFlags"
                :key="i"
                class="flex items-start gap-2 text-xs"
                :class="flag.severity === 'error' ? 'text-red-700' : 'text-amber-700'"
              >
                <AlertCircle :size="12" class="mt-0.5 flex-shrink-0" />
                <span>{{ flag.message }}</span>
              </div>
            </div>

            <!-- Progress bar: required fields filled -->
            <div class="px-4 py-2 border-t border-gray-100 bg-gray-50 flex items-center gap-3">
              <div class="flex-1 bg-gray-200 rounded-full h-1.5 overflow-hidden">
                <div
                  class="h-full bg-navy rounded-full transition-all duration-500"
                  :style="`width:${fieldProgress}%`"
                />
              </div>
              <span class="text-xs text-gray-500 whitespace-nowrap">
                {{ filledCount }}/{{ requiredFields.length }} required fields
              </span>
            </div>

            <!-- Chat input -->
            <div class="border-t border-gray-200 p-3 flex gap-2">
              <textarea
                v-model="chatInput"
                rows="2"
                placeholder="Describe the lease or answer the question above…"
                class="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy/30"
                @keydown.enter.exact.prevent="sendMessage"
                :disabled="chatThinking || sessionFinalized"
              />
              <button
                class="btn-primary px-4 self-end"
                :disabled="!chatInput.trim() || chatThinking || sessionFinalized"
                @click="sendMessage"
              >
                <Send :size="14" />
              </button>
            </div>
          </div>

          <!-- Right: Live form preview -->
          <div class="hidden lg:flex flex-col w-1/2 overflow-y-auto">
            <div class="px-4 py-3 border-b border-gray-100 bg-gray-50 flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span class="text-xs font-medium text-gray-600">Live preview — updates as AI extracts fields</span>
            </div>
            <div class="px-5 py-5 space-y-6">
              <LeaseFormFields
                v-model:form="form"
                v-model:useExistingProperty="useExistingProperty"
                v-model:useExistingUnit="useExistingUnit"
                :properties="properties"
                :readonly-hint="true"
              />
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 flex-shrink-0 bg-white">
          <div v-if="submitError" class="flex items-center gap-2 text-sm text-red-600">
            <AlertCircle :size="14" />
            {{ submitError }}
          </div>
          <div v-else class="text-xs text-gray-400">
            {{ readyToFinalize ? 'All required fields collected — ready to create the lease.' : 'Chat with AI to fill in required fields.' }}
          </div>
          <div class="flex gap-2">
            <button class="btn-ghost" @click="step = 1">Back</button>
            <button
              class="btn-primary"
              :disabled="!readyToFinalize || submitting"
              @click="doFinalizeSession"
            >
              <Loader2 v-if="submitting" :size="14" class="animate-spin" />
              {{ submitting ? 'Creating…' : 'Create Lease' }}
            </button>
          </div>
        </div>
      </template>

      <!-- ── Step 3: Done ────────────────────────────────────────────────── -->
      <div v-if="step === 3" class="flex-1 flex items-center justify-center">
        <div class="text-center space-y-4 max-w-sm">
          <div class="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center mx-auto">
            <CheckCircle2 :size="32" class="text-emerald-600" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-lg">Lease created!</div>
            <div class="text-sm text-gray-500 mt-1">
              {{ createdLeaseNumber }} has been created and is ready for signing.
            </div>
          </div>
          <div class="flex gap-2 justify-center pt-2">
            <button class="btn-ghost" @click="reset">Build another</button>
            <button class="btn-primary" @click="$emit('done')">View leases</button>
          </div>
        </div>
      </div>

    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, defineComponent, h } from 'vue'
import api from '../../api'
import {
  X, ChevronRight, FileSignature, Sparkles, FormInput, AlertCircle,
  Loader2, CheckCircle2, Send, Plus,
} from 'lucide-vue-next'

const props = defineProps<{ existingLeaseId?: number | null; startMode?: 'form' | 'chat' | null; templateId?: number | null }>()
const emit = defineEmits<{ close: []; done: [] }>()

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
  props: { modelValue: Object, compact: Boolean },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function upd(field: string, val: string) {
      emit('update:modelValue', { ...props.modelValue, [field]: val })
    }
    return () => {
      const p = props.modelValue as any
      const cls = 'input' + (props.compact ? ' text-xs' : '')
      return h('div', { class: 'grid grid-cols-2 gap-2' }, [
        h('div', { class: 'col-span-2' }, [
          h('label', { class: 'label' }, 'Full name'),
          h('input', { class: cls, value: p.full_name, placeholder: 'Full name', onInput: (e: any) => upd('full_name', e.target.value) }),
        ]),
        h('div', [
          h('label', { class: 'label' }, 'ID / Passport'),
          h('input', { class: cls + ' font-mono', value: p.id_number, placeholder: 'ID number', onInput: (e: any) => upd('id_number', e.target.value) }),
        ]),
        h('div', [
          h('label', { class: 'label' }, 'Phone'),
          h('input', { class: cls, value: p.phone, placeholder: 'Phone', onInput: (e: any) => upd('phone', e.target.value) }),
        ]),
        h('div', { class: 'col-span-2' }, [
          h('label', { class: 'label' }, 'Email'),
          h('input', { class: cls, value: p.email, type: 'email', placeholder: 'Email', onInput: (e: any) => upd('email', e.target.value) }),
        ]),
      ])
    }
  },
})

// LeaseFormFields is a render-function component wrapping all the form sections
const LeaseFormFields = defineComponent({
  props: {
    form: Object,
    useExistingProperty: [Number, Boolean],
    useExistingUnit: [Number, Boolean],
    properties: Array,
    readonlyHint: Boolean,
  },
  emits: ['update:form', 'update:useExistingProperty', 'update:useExistingUnit'],
  setup(props, { emit }) {
    function updForm(field: string, val: any) {
      emit('update:form', { ...props.form, [field]: val })
    }
    function updProp(field: string, val: any) {
      emit('update:form', { ...props.form, property: { ...(props.form as any).property, [field]: val } })
    }
    function updUnit(field: string, val: any) {
      emit('update:form', { ...props.form, unit: { ...(props.form as any).unit, [field]: val } })
    }

    const unitsForProp = computed(() => {
      const pid = props.useExistingProperty
      if (!pid) return []
      return (props.properties as any[])?.find((p: any) => p.id === pid)?.units ?? []
    })

    return () => {
      const f = props.form as any
      const ro = props.readonlyHint
      const inputCls = `input${ro ? ' bg-gray-50' : ''}`

      return h('div', { class: 'space-y-8' }, [
        // Property
        h('section', { class: 'space-y-4' }, [
          h(SectionLabel, { text: 'Property', color: 'navy' }),
          h('div', { class: 'grid grid-cols-2 gap-3' }, [
            h('div', { class: 'col-span-2' }, [
              h('label', { class: 'label' }, 'Match existing or create new'),
              h('select', {
                class: inputCls,
                value: props.useExistingProperty,
                onChange: (e: any) => emit('update:useExistingProperty', e.target.value === 'false' ? false : Number(e.target.value)),
              }, [
                h('option', { value: false }, '+ Create new property'),
                ...(props.properties as any[])?.map((p: any) => h('option', { key: p.id, value: p.id }, p.name)) ?? [],
              ]),
            ]),
            ...(!props.useExistingProperty ? [
              h('div', { class: 'col-span-2' }, [
                h('label', { class: 'label' }, 'Property name'),
                h('input', { class: inputCls, value: f.property?.name, placeholder: 'e.g. 18 Irene Park', onInput: (e: any) => updProp('name', e.target.value) }),
              ]),
              h('div', { class: 'col-span-2' }, [
                h('label', { class: 'label' }, 'Address'),
                h('input', { class: inputCls, value: f.property?.address, placeholder: 'Street address', onInput: (e: any) => updProp('address', e.target.value) }),
              ]),
              h('div', [
                h('label', { class: 'label' }, 'City'),
                h('input', { class: inputCls, value: f.property?.city, onInput: (e: any) => updProp('city', e.target.value) }),
              ]),
              h('div', [
                h('label', { class: 'label' }, 'Province'),
                h('input', { class: inputCls, value: f.property?.province, onInput: (e: any) => updProp('province', e.target.value) }),
              ]),
            ] : []),
          ]),
          // Unit
          h('div', { class: 'grid grid-cols-3 gap-3' }, [
            h('div', { class: !props.useExistingProperty || !props.useExistingUnit ? 'col-span-1' : 'col-span-3' }, [
              h('label', { class: 'label' }, 'Unit'),
              props.useExistingProperty
                ? h('select', {
                    class: inputCls,
                    value: props.useExistingUnit,
                    onChange: (e: any) => emit('update:useExistingUnit', e.target.value === 'false' ? false : Number(e.target.value)),
                  }, [
                    h('option', { value: false }, '+ Create new unit'),
                    ...unitsForProp.value.map((u: any) => h('option', { key: u.id, value: u.id }, `Unit ${u.unit_number}`)),
                  ])
                : h('input', { class: inputCls, value: f.unit?.unit_number, placeholder: '1', onInput: (e: any) => updUnit('unit_number', e.target.value) }),
            ]),
            ...(!props.useExistingProperty || !props.useExistingUnit ? [
              h('div', [
                h('label', { class: 'label' }, 'Beds'),
                h('input', { class: inputCls, type: 'number', value: f.unit?.bedrooms, onInput: (e: any) => updUnit('bedrooms', Number(e.target.value)) }),
              ]),
              h('div', [
                h('label', { class: 'label' }, 'Baths'),
                h('input', { class: inputCls, type: 'number', value: f.unit?.bathrooms, onInput: (e: any) => updUnit('bathrooms', Number(e.target.value)) }),
              ]),
            ] : []),
          ]),
        ]),

        // Lease Terms
        h('section', { class: 'space-y-3' }, [
          h(SectionLabel, { text: 'Lease Terms', color: 'purple' }),
          h('div', { class: 'grid grid-cols-2 gap-3' }, [
            h('div', [h('label', { class: 'label' }, 'Start date'), h('input', { class: inputCls, type: 'date', value: f.start_date, onInput: (e: any) => updForm('start_date', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'End date'), h('input', { class: inputCls, type: 'date', value: f.end_date, onInput: (e: any) => updForm('end_date', e.target.value) })]),
            h('div', [h('label', { class: 'label' }, 'Monthly rent (R)'), h('input', { class: inputCls, type: 'number', value: f.monthly_rent, onInput: (e: any) => updForm('monthly_rent', e.target.value) })]),
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
        ]),

        // Tenants
        h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Tenants — jointly & severally liable', color: 'navy' }),
            !ro && f.co_tenants?.length < 3
              ? h('button', {
                  class: 'btn-ghost text-xs px-2 py-1',
                  onClick: () => updForm('co_tenants', [...(f.co_tenants ?? []), emptyPerson()]),
                }, '+ Add tenant')
              : null,
          ]),
          h('div', { class: 'relative border border-navy/20 rounded-xl p-4 bg-navy/5' }, [
            h('span', { class: 'absolute top-3 left-4 text-[10px] font-semibold text-navy/50 uppercase tracking-wide' }, 'Tenant 1'),
            h('div', { class: 'pt-4' }, [h(PersonBlock, { modelValue: f.primary_tenant, 'onUpdate:modelValue': (v: any) => updForm('primary_tenant', v) })]),
          ]),
          ...(f.co_tenants ?? []).map((ct: any, i: number) =>
            h('div', { key: i, class: 'relative border border-navy/20 rounded-xl p-4 bg-navy/5' }, [
              h('span', { class: 'absolute top-3 left-4 text-[10px] font-semibold text-navy/50 uppercase tracking-wide' }, `Tenant ${i + 2}`),
              !ro && h('button', {
                class: 'absolute top-2.5 right-3 text-gray-400 hover:text-red-500',
                onClick: () => updForm('co_tenants', f.co_tenants.filter((_: any, j: number) => j !== i)),
              }, h(X, { size: 14 })),
              h('div', { class: 'pt-4' }, [
                h(PersonBlock, {
                  modelValue: ct, compact: true,
                  'onUpdate:modelValue': (v: any) => updForm('co_tenants', f.co_tenants.map((c: any, j: number) => j === i ? v : c)),
                }),
              ]),
            ])
          ),
        ]),

        // Occupants
        h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Occupants', color: 'green' }),
            !ro && h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('occupants', [...(f.occupants ?? []), { ...emptyPerson(), relationship_to_tenant: 'self' }]),
            }, '+ Add'),
          ]),
          ...(f.occupants?.length
            ? f.occupants.map((oc: any, i: number) =>
                h('div', { key: i, class: 'relative border border-emerald-100 rounded-xl p-4 bg-emerald-50/40' }, [
                  !ro && h('button', { class: 'absolute top-3 right-3 text-gray-400 hover:text-red-500', onClick: () => updForm('occupants', f.occupants.filter((_: any, j: number) => j !== i)) }, h(X, { size: 14 })),
                  h(PersonBlock, { modelValue: oc, compact: true, 'onUpdate:modelValue': (v: any) => updForm('occupants', f.occupants.map((o: any, j: number) => j === i ? v : o)) }),
                  h('div', { class: 'mt-2' }, [
                    h('label', { class: 'label' }, 'Relationship'),
                    h('input', { class: 'input text-xs', value: oc.relationship_to_tenant, placeholder: 'self, spouse, child…', onInput: (e: any) => updForm('occupants', f.occupants.map((o: any, j: number) => j === i ? { ...o, relationship_to_tenant: e.target.value } : o)) }),
                  ]),
                ])
              )
            : [h('p', { class: 'text-xs text-gray-400' }, 'None')]),
        ]),

        // Guarantors
        h('section', { class: 'space-y-3' }, [
          h('div', { class: 'flex items-center justify-between' }, [
            h(SectionLabel, { text: 'Guarantors / Sureties', color: 'amber' }),
            !ro && h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('guarantors', [...(f.guarantors ?? []), { ...emptyPerson(), for_tenant: '' }]),
            }, '+ Add'),
          ]),
          ...(f.guarantors?.length
            ? f.guarantors.map((g: any, i: number) =>
                h('div', { key: i, class: 'relative border border-amber-100 rounded-xl p-4 bg-amber-50/40' }, [
                  !ro && h('button', { class: 'absolute top-3 right-3 text-gray-400 hover:text-red-500', onClick: () => updForm('guarantors', f.guarantors.filter((_: any, j: number) => j !== i)) }, h(X, { size: 14 })),
                  h(PersonBlock, { modelValue: g, compact: true, 'onUpdate:modelValue': (v: any) => updForm('guarantors', f.guarantors.map((gg: any, j: number) => j === i ? v : gg)) }),
                  h('div', { class: 'mt-2' }, [
                    h('label', { class: 'label' }, 'Covers tenant'),
                    h('input', { class: 'input text-xs', value: g.for_tenant, placeholder: 'Name of tenant they cover', onInput: (e: any) => updForm('guarantors', f.guarantors.map((gg: any, j: number) => j === i ? { ...gg, for_tenant: e.target.value } : gg)) }),
                  ]),
                ])
              )
            : [h('p', { class: 'text-xs text-gray-400' }, 'None')]),
        ]),
      ])
    }
  },
})

// ── State ──────────────────────────────────────────────────────────────────

const step = ref(1)
const mode = ref<'form' | 'chat' | null>(null)
const properties = ref<any[]>([])
const useExistingProperty = ref<number | false>(false)
const useExistingUnit = ref<number | false>(false)
const submitting = ref(false)
const generating = ref(false)
const submitError = ref('')
const createdLeaseNumber = ref('')

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

// ── Template management ────────────────────────────────────────────────────

const templates = ref<any[]>([])
const activeTemplate = computed(() => templates.value.find(t => t.is_active) ?? templates.value[0] ?? null)
const uploadingTemplate = ref(false)
const templateUploadError = ref('')
const templateFileInput = ref<HTMLInputElement | null>(null)

async function loadTemplates() {
  try {
    const { data } = await api.get('/leases/templates/')
    templates.value = data.results ?? data
  } catch { /* non-fatal */ }
}

async function handleTemplateUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const lower = file.name.toLowerCase()
  if (!lower.endsWith('.docx') && !lower.endsWith('.pdf')) {
    templateUploadError.value = 'Only .docx or .pdf files are accepted.'
    return
  }
  templateUploadError.value = ''
  uploadingTemplate.value = true
  try {
    const fd = new FormData()
    fd.append('name', file.name.replace(/\.(docx|pdf)$/i, ''))
    fd.append('template_file', file)
    await api.post('/leases/templates/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    await loadTemplates()
  } catch (err: any) {
    templateUploadError.value = err?.response?.data?.error ?? 'Upload failed.'
  } finally {
    uploadingTemplate.value = false
    if (templateFileInput.value) templateFileInput.value.value = ''
  }
}

// ── AI Chat state ─────────────────────────────────────────────────────────

const chatMessages = ref<{ role: string; content: string }[]>([])
const chatInput = ref('')
const chatThinking = ref(false)
const chatScrollEl = ref<HTMLElement | null>(null)
const sessionId = ref<number | null>(null)
const sessionFinalized = ref(false)
const readyToFinalize = ref(false)
const rhaFlags = ref<any[]>([])

const requiredFields = [
  'landlord_name', 'property_address', 'unit_number', 'tenant_name',
  'lease_start', 'lease_end', 'monthly_rent', 'deposit', 'notice_period_days',
]
const missingFields = ref<string[]>([...requiredFields])
const filledCount = computed(() => requiredFields.length - missingFields.value.length)
const fieldProgress = computed(() => Math.round((filledCount.value / requiredFields.length) * 100))

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(() => {
  api.get('/properties/?page_size=500').then(({ data }) => {
    properties.value = data.results ?? data
  })
  loadTemplates()
  // Skip mode selection if startMode prop is provided
  if (props.startMode) {
    mode.value = props.startMode
    step.value = 2
    if (props.startMode === 'chat') startChatSession()
  }
})

// ── Mode selection ────────────────────────────────────────────────────────

function selectMode(m: 'form' | 'chat') {
  mode.value = m
}

async function startMode() {
  if (!mode.value) return
  if (mode.value === 'chat') {
    await startChatSession()
  }
  step.value = 2
}

// ── AI Chat ───────────────────────────────────────────────────────────────

async function startChatSession() {
  try {
    const payload: Record<string, unknown> = {}
    if (props.existingLeaseId) payload.existing_lease_id = props.existingLeaseId
    if (props.templateId) payload.template_id = props.templateId
    const { data } = await api.post('/leases/builder/sessions/', payload)
    sessionId.value = data.session_id
    chatMessages.value = [{ role: 'assistant', content: data.message }]
    missingFields.value = data.missing_fields ?? data.required_fields ?? [...requiredFields]
    if (data.current_state) applyStateToForm(data.current_state)
  } catch {
    chatMessages.value = [{ role: 'assistant', content: 'Hi! Tell me about the lease you want to create.' }]
  }
}

async function sendMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatThinking.value || !sessionId.value) return

  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  chatThinking.value = true
  scrollChat()

  try {
    const { data } = await api.post(`/leases/builder/sessions/${sessionId.value}/message/`, { message: msg })

    chatMessages.value.push({ role: 'assistant', content: data.reply })
    rhaFlags.value = data.rha_flags ?? []
    missingFields.value = data.missing_fields ?? []
    readyToFinalize.value = data.ready_to_finalize ?? false

    // Sync form from current_state
    if (data.current_state) applyStateToForm(data.current_state)
  } catch (e: any) {
    chatMessages.value.push({ role: 'assistant', content: 'Sorry, something went wrong. Please try again.' })
  } finally {
    chatThinking.value = false
    scrollChat()
  }
}

function applyStateToForm(state: any) {
  if (state.property_address) form.value.property.address = state.property_address
  if (state.property_name) form.value.property.name = state.property_name
  if (state.city) form.value.property.city = state.city
  if (state.province) form.value.property.province = state.province
  if (state.unit_number) form.value.unit.unit_number = String(state.unit_number)
  if (state.lease_start) form.value.start_date = state.lease_start
  if (state.lease_end) form.value.end_date = state.lease_end
  if (state.monthly_rent) form.value.monthly_rent = state.monthly_rent
  if (state.deposit) form.value.deposit = state.deposit
  if (state.notice_period_days) form.value.notice_period_days = state.notice_period_days
  if (state.early_termination_months) form.value.early_termination_penalty_months = state.early_termination_months
  if (state.max_occupants) form.value.max_occupants = state.max_occupants
  if (state.payment_reference) form.value.payment_reference = state.payment_reference
  if (state.tenant_name) form.value.primary_tenant.full_name = state.tenant_name
  if (state.tenant_id) form.value.primary_tenant.id_number = state.tenant_id
  if (state.tenant_phone) form.value.primary_tenant.phone = state.tenant_phone
  if (state.tenant_email) form.value.primary_tenant.email = state.tenant_email
  if (state.water_included != null) form.value.water_included = state.water_included !== false && state.water_included !== 'Excluded'
  if (state.electricity_prepaid != null) form.value.electricity_prepaid = state.electricity_prepaid !== false && state.electricity_prepaid !== 'Included'
}

function scrollChat() {
  nextTick(() => {
    if (chatScrollEl.value) {
      chatScrollEl.value.scrollTop = chatScrollEl.value.scrollHeight
    }
  })
}

// ── Smart Form: create via import ──────────────────────────────────────────

async function doFormCreate() {
  submitting.value = true
  submitError.value = ''
  try {
    const payload: any = { ...form.value }
    if (useExistingProperty.value) {
      payload.property_id = useExistingProperty.value
      if (useExistingUnit.value) payload.unit_id = useExistingUnit.value
    }
    const { data } = await api.post('/leases/import/', payload)
    createdLeaseNumber.value = data.lease_number
    step.value = 3
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.message ?? 'Failed to create lease'
    submitError.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    submitting.value = false
  }
}

// ── Smart Form: preview DOCX ───────────────────────────────────────────────

async function previewDocx() {
  generating.value = true
  try {
    const context = buildDocxContext()
    const resp = await api.post('/leases/generate/', { context }, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `lease_preview_${form.value.primary_tenant.full_name || 'draft'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // silently ignore preview errors — main action is still Create Lease
  } finally {
    generating.value = false
  }
}

function buildDocxContext() {
  const f = form.value
  return {
    landlord_name: '—',
    landlord_id: '—',
    landlord_address: f.property.address,
    landlord_phone: '—',
    landlord_email: '—',
    property_address: f.property.address,
    unit_number: f.unit.unit_number,
    city: f.property.city,
    province: f.property.province,
    tenant_name: f.primary_tenant.full_name,
    tenant_id: f.primary_tenant.id_number,
    tenant_phone: f.primary_tenant.phone,
    tenant_email: f.primary_tenant.email,
    co_tenants: f.co_tenants.map((c: any) => c.full_name).filter(Boolean).join(', ') || '—',
    lease_start: f.start_date,
    lease_end: f.end_date,
    monthly_rent: `R ${Number(f.monthly_rent).toLocaleString('en-ZA')}`,
    deposit: `R ${Number(f.deposit).toLocaleString('en-ZA')}`,
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
  }
}

// ── AI Chat: finalize ──────────────────────────────────────────────────────

async function doFinalizeSession() {
  if (!sessionId.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const { data } = await api.post(`/leases/builder/sessions/${sessionId.value}/finalize/`)
    createdLeaseNumber.value = data.lease_number
    sessionFinalized.value = true
    step.value = 3
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.message ?? 'Failed to create lease'
    submitError.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    submitting.value = false
  }
}

// ── Reset ──────────────────────────────────────────────────────────────────

function reset() {
  step.value = 1
  mode.value = null
  sessionId.value = null
  sessionFinalized.value = false
  readyToFinalize.value = false
  rhaFlags.value = []
  chatMessages.value = []
  chatInput.value = ''
  submitError.value = ''
  createdLeaseNumber.value = ''
  missingFields.value = [...requiredFields]
  useExistingProperty.value = false
  useExistingUnit.value = false
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
