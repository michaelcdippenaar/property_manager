<template>
  <div class="flex flex-col h-full -m-6 bg-white overflow-hidden">

      <!-- ── Header ── -->
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-200 flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center">
            <FileSignature :size="14" class="text-white" />
          </div>
          <div class="font-semibold text-gray-900 text-sm">New Lease</div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Template selector -->
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-400 hidden sm:block">Template:</span>
            <select
              v-model="selectedTemplateId"
              class="input text-sm py-1 px-2.5 min-w-[180px]"
            >
              <option :value="null" disabled>Select template…</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">
                {{ t.name }} v{{ t.version }}
              </option>
            </select>
            <button class="btn-ghost btn-xs" @click="router.push('/leases/templates')">
              <Plus :size="12" /> New
            </button>
          </div>
        </div>
      </div>

      <!-- ── Done screen ── -->
      <div v-if="step === 3" class="flex-1 flex items-center justify-center">
        <div class="text-center space-y-4">
          <div class="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
            <CheckCircle2 :size="28" class="text-emerald-500" />
          </div>
          <div class="font-semibold text-gray-900 text-lg">Lease created!</div>
          <div class="text-sm text-gray-500">{{ createdLeaseNumber }} is ready.</div>
          <div class="flex gap-2 justify-center pt-2">
            <button class="btn-ghost" @click="reset">Build another</button>
            <button class="btn-primary" @click="router.push('/leases')">View leases</button>
          </div>
        </div>
      </div>

      <!-- ── Main split panel ── -->
      <div v-else class="flex flex-1 min-h-0">

        <!-- Left: Form -->
        <div class="w-[400px] flex-shrink-0 border-r border-gray-200 flex flex-col overflow-hidden">
          <div class="flex-1 overflow-y-auto px-5 py-5 space-y-8">
            <LeaseFormFields
              v-model:form="form"
              v-model:useExistingProperty="useExistingProperty"
              v-model:useExistingUnit="useExistingUnit"
              :properties="properties"
            />

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
          </div>

          <!-- Form footer -->
          <div class="border-t border-gray-200 px-5 py-3 flex items-center gap-2 bg-white flex-shrink-0">
            <div v-if="submitError" class="flex items-center gap-1.5 text-xs text-red-600 flex-1 min-w-0">
              <AlertCircle :size="12" class="flex-shrink-0" />
              <span class="truncate">{{ submitError }}</span>
            </div>
            <div class="flex gap-2 ml-auto">
              <button
                class="btn-ghost text-xs"
                :disabled="generating || !selectedTemplateId"
                @click="previewDocx"
              >
                <Loader2 v-if="generating" :size="12" class="animate-spin" />
                {{ generating ? 'Generating…' : 'Download DOCX' }}
              </button>
              <button class="btn-primary" :disabled="submitting" @click="doFormCreate">
                <Loader2 v-if="submitting" :size="14" class="animate-spin" />
                {{ submitting ? 'Creating…' : 'Create Lease' }}
              </button>
            </div>
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

        <DocumentPage
          v-else-if="templateHtml"
          :html="previewHtml"
          show-footer
          :footer-left="selectedTemplateName"
        />
      </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import DocumentPage from '../../components/DocumentPage.vue'
import {
  FileSignature, AlertCircle, Loader2, CheckCircle2, Plus,
} from 'lucide-vue-next'

const router = useRouter()

const props = defineProps<{ existingLeaseId?: number | null; templateId?: number | null }>()

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

const LeaseFormFields = defineComponent({
  props: {
    form: Object,
    useExistingProperty: [Number, Boolean],
    useExistingUnit: [Number, Boolean],
    properties: Array,
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
      const inputCls = 'input'

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
            f.co_tenants?.length < 3
              ? h('button', {
                  class: 'btn-ghost text-xs px-2 py-1',
                  onClick: () => updForm('co_tenants', [...(f.co_tenants ?? []), emptyPerson()]),
                }, '+ Add tenant')
              : null,
          ]),
          h('div', { class: 'relative border border-navy/20 rounded-xl p-4 bg-navy/5' }, [
            h('span', { class: 'absolute top-3 left-4 text-micro font-semibold text-navy/50 uppercase tracking-wide' }, 'Tenant 1'),
            h('div', { class: 'pt-4' }, [h(PersonBlock, { modelValue: f.primary_tenant, 'onUpdate:modelValue': (v: any) => updForm('primary_tenant', v) })]),
          ]),
          ...(f.co_tenants ?? []).map((ct: any, i: number) =>
            h('div', { key: i, class: 'relative border border-navy/20 rounded-xl p-4 bg-navy/5' }, [
              h('span', { class: 'absolute top-3 left-4 text-micro font-semibold text-navy/50 uppercase tracking-wide' }, `Tenant ${i + 2}`),
              h('button', {
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
            h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('occupants', [...(f.occupants ?? []), { ...emptyPerson(), relationship_to_tenant: 'self' }]),
            }, '+ Add'),
          ]),
          ...(f.occupants?.length
            ? f.occupants.map((oc: any, i: number) =>
                h('div', { key: i, class: 'relative border border-emerald-100 rounded-xl p-4 bg-emerald-50/40' }, [
                  h('button', { class: 'absolute top-3 right-3 text-gray-400 hover:text-red-500', onClick: () => updForm('occupants', f.occupants.filter((_: any, j: number) => j !== i)) }, h(X, { size: 14 })),
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
            h('button', {
              class: 'btn-ghost text-xs px-2 py-1',
              onClick: () => updForm('guarantors', [...(f.guarantors ?? []), { ...emptyPerson(), for_tenant: '' }]),
            }, '+ Add'),
          ]),
          ...(f.guarantors?.length
            ? f.guarantors.map((g: any, i: number) =>
                h('div', { key: i, class: 'relative border border-amber-100 rounded-xl p-4 bg-amber-50/40' }, [
                  h('button', { class: 'absolute top-3 right-3 text-gray-400 hover:text-red-500', onClick: () => updForm('guarantors', f.guarantors.filter((_: any, j: number) => j !== i)) }, h(X, { size: 14 })),
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

const additionalTerms = ref('')

// ── Template management ────────────────────────────────────────────────────

const templates = ref<any[]>([])
const loadingTemplates = ref(false)
const loadingContent = ref(false)
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
    // Auto-select: prefer templateId prop, then first active, then first
    const preferred = props.templateId
      ? templates.value.find(t => t.id === props.templateId)
      : templates.value.find(t => t.is_active) ?? templates.value[0]
    if (preferred) selectedTemplateId.value = preferred.id
  } catch { /* non-fatal */ }
  finally { loadingTemplates.value = false }
}

async function fetchTemplateContent(id: number) {
  loadingContent.value = true
  templateHtml.value = ''
  try {
    const { data } = await api.get(`/leases/templates/${id}/`)
    const raw = data.content_html ?? ''
    // Parse JSON format (v1) or fall back to legacy HTML
    try {
      const doc = JSON.parse(raw)
      if (doc.v === 1 && typeof doc.html === 'string') {
        templateHtml.value = doc.html
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

const previewHtml = computed(() => {
  if (!templateHtml.value) return ''
  const vals = buildDocxContext() as Record<string, any>

  let html = templateHtml.value

  // Replace <span data-merge-field="X">...</span> with filled value or placeholder
  html = html.replace(/<span[^>]*data-merge-field="([^"]+)"[^>]*>[\s\S]*?<\/span>/g, (_, field) => {
    const val = vals[field]
    if (val !== undefined && String(val).trim() && String(val) !== '—') {
      return `<span class="pf-filled">${escHtml(String(val))}</span>`
    }
    return `<span class="pf-empty">{{${field}}}</span>`
  })

  // Also replace bare {{ field }} jinja-style placeholders
  html = html.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, field) => {
    const val = vals[field]
    if (val !== undefined && String(val).trim() && String(val) !== '—') {
      return `<span class="pf-filled">${escHtml(String(val))}</span>`
    }
    return `<span class="pf-empty">{{${field}}}</span>`
  })

  // Append additional terms
  if (additionalTerms.value.trim()) {
    html += `<div class="pf-additional-terms"><strong>Additional Terms &amp; Conditions</strong><div class="pf-terms-body">${escHtml(additionalTerms.value)}</div></div>`
  }

  return html
})

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(() => {
  api.get('/properties/?page_size=500').then(({ data }) => {
    properties.value = data.results ?? data
  })
  loadTemplates()
})

// ── Smart Form: create via import ──────────────────────────────────────────

async function doFormCreate() {
  submitError.value = ''
  const f = form.value
  if (!f.primary_tenant.full_name) { submitError.value = 'Primary tenant name is required.'; return }
  if (!f.start_date) { submitError.value = 'Lease start date is required.'; return }
  if (!f.end_date)   { submitError.value = 'Lease end date is required.'; return }
  if (!f.monthly_rent) { submitError.value = 'Monthly rent is required.'; return }
  submitting.value = true
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
    monthly_rent: f.monthly_rent ? `R ${Number(f.monthly_rent).toLocaleString('en-ZA')}` : '',
    deposit: f.deposit ? `R ${Number(f.deposit).toLocaleString('en-ZA')}` : '',
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

// ── Reset ──────────────────────────────────────────────────────────────────

function reset() {
  step.value = 1
  submitError.value = ''
  createdLeaseNumber.value = ''
  additionalTerms.value = ''
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

<style scoped>
/* Additional terms block */
:deep(.pf-additional-terms) {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.9em;
}
:deep(.pf-terms-body) {
  margin-top: 0.5rem;
  white-space: pre-wrap;
  color: #374151;
}

/* Table styles */
:deep(table) {
  width: 100%; border-collapse: collapse; margin: 0.75rem 0;
}
:deep(td),
:deep(th) {
  border: 1px solid #e5e7eb; padding: 6px 10px; font-size: 12px;
}
.lease-preview-page :deep(th) {
  background: #f9fafb; font-weight: 600;
}
</style>
