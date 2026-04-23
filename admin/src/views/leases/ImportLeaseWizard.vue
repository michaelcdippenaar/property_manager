<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex flex-col bg-white overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <div class="flex items-center gap-3 min-w-0">
          <button
            @click="$emit('close')"
            class="w-9 h-9 -ml-2 rounded-lg flex items-center justify-center text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors flex-shrink-0"
            :aria-label="prefilledPropertyName ? `Back to ${prefilledPropertyName}` : 'Back'"
            :title="prefilledPropertyName ? `Back to ${prefilledPropertyName}` : 'Back (Esc)'"
          >
            <ArrowLeft :size="18" />
          </button>
          <div class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center flex-shrink-0">
            <Sparkles :size="14" class="text-white" />
          </div>
          <div class="min-w-0">
            <nav v-if="prefilledPropertyName" aria-label="Breadcrumb" class="flex items-center gap-1 text-xs text-gray-400 mb-0.5">
              <span class="truncate max-w-[200px]">{{ prefilledPropertyName }}</span>
              <ChevronRight :size="12" class="flex-shrink-0" />
              <span>Leases</span>
              <ChevronRight :size="12" class="flex-shrink-0" />
              <span class="text-gray-600 font-medium">Import</span>
            </nav>
            <div class="font-semibold text-gray-900 text-sm truncate">
              Import lease
              <span v-if="prefilledPropertyName" class="text-gray-500 font-normal">for {{ prefilledPropertyName }}</span>
              <span v-else class="text-gray-500 font-normal">from PDF</span>
            </div>
            <div class="text-xs text-gray-400">AI extracts tenants, occupants and terms automatically</div>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-1.5 text-xs text-gray-400">
            <span :class="step >= 1 ? 'text-navy font-medium' : ''">Upload</span>
            <ChevronRight :size="12" />
            <span :class="step >= 2 ? 'text-navy font-medium' : ''">Review</span>
            <ChevronRight :size="12" />
            <span :class="step >= 3 ? 'text-navy font-medium' : ''">Done</span>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 ml-2"><X :size="18" /></button>
        </div>
      </div>

      <!-- Step 1: Upload -->
      <div v-if="step === 1" class="flex-1 flex items-center justify-center p-6 sm:p-8 min-h-[50vh]">
        <div class="w-full max-w-xl space-y-6">

          <!-- Draft restore banner -->
          <div v-if="hasDraft" class="flex items-center justify-between gap-3 px-4 py-3 bg-warning-50 border border-warning-100 rounded-xl">
            <div class="flex items-center gap-2 text-sm text-warning-700">
              <Clock :size="14" class="text-warning-500 flex-shrink-0" />
              <span>Unsaved draft from <strong>{{ draftAge() }}</strong> — resume without re-parsing?</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <button @click="clearDraft" class="text-xs text-warning-600 hover:text-warning-700">Discard</button>
              <button @click="restoreDraft" class="text-xs font-semibold text-white bg-warning-500 hover:bg-warning-600 px-3 py-1 rounded-lg transition-colors">Resume</button>
            </div>
          </div>
          <div
            class="border-2 border-dashed rounded-2xl min-h-[220px] flex flex-col items-center justify-center p-10 sm:p-12 text-center transition-colors cursor-pointer select-none"
            :class="dragging ? 'border-navy bg-navy/5 ring-2 ring-navy/20' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/50'"
            @dragenter.prevent="onDragEnter"
            @dragleave.prevent="onDragLeave"
            @dragover.prevent="onDragOver"
            @drop.prevent="onDrop"
            @click="onDropzoneClick"
          >
            <div v-if="!parsing" class="space-y-3 pointer-events-none">
              <div class="w-14 h-14 rounded-2xl bg-lavender flex items-center justify-center mx-auto">
                <FileText :size="24" class="text-navy" />
              </div>
              <div>
                <div class="font-medium text-gray-800">Drag & drop your lease PDF here</div>
                <div class="text-sm text-gray-400 mt-1">or click anywhere in this box to browse</div>
              </div>
              <div class="text-xs text-gray-300 pt-2">Supports multi-tenant South African lease agreements</div>
            </div>
            <div v-else class="space-y-4">
              <div class="w-14 h-14 rounded-2xl bg-navy/10 flex items-center justify-center mx-auto">
                <Sparkles :size="24" class="text-navy animate-pulse" />
              </div>
              <div>
                <div class="font-medium text-gray-800">Reading your lease…</div>
                <div class="text-sm text-gray-400 mt-1">Claude is extracting all the details</div>
              </div>
              <div class="flex justify-center gap-1 pt-1">
                <span v-for="i in 3" :key="i" class="w-1.5 h-1.5 rounded-full bg-navy animate-bounce" :style="`animation-delay:${(i-1)*0.15}s`" />
              </div>
            </div>
          </div>
          <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelected" />

          <div v-if="parseError" class="flex items-start gap-2 p-3 bg-danger-50 border border-danger-100 rounded-xl text-sm">
            <AlertCircle :size="15" class="text-danger-500 mt-0.5 flex-shrink-0" />
            <div>
              <div class="font-medium text-danger-700">Parse failed</div>
              <div class="text-danger-600 text-xs mt-0.5 font-mono whitespace-pre-wrap">{{ parseError }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: Review — split layout -->
      <div v-if="step === 2" class="flex-1 flex overflow-hidden">

        <!-- Left: PDF viewer -->
        <div class="hidden lg:flex flex-col w-[52%] border-r border-gray-200 bg-gray-50">
          <div class="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-white flex-shrink-0">
            <span class="text-xs font-medium text-gray-500 flex items-center gap-1.5">
              <FileText :size="13" class="text-gray-400" />
              {{ pdfFileName }}
            </span>
            <span class="text-xs text-gray-400">Original document — verify against the form</span>
          </div>
          <iframe
            :src="pdfUrl"
            class="flex-1 w-full"
            style="border:none;"
            data-clarity-mask="true"
          />
        </div>

        <!-- Right: Editable form -->
        <div class="flex-1 overflow-y-auto">
          <div class="max-w-xl mx-auto px-6 py-8 space-y-8">

            <!-- Signed / historical toggle -->
            <div
              class="flex items-center justify-between gap-4 px-4 py-3 rounded-xl border cursor-pointer select-none transition-colors"
              :class="form.status === 'active' ? 'bg-success-50 border-success-200' : 'bg-warning-50 border-warning-100'"
              @click="form.status = form.status === 'active' ? 'pending' : 'active'"
            >
              <div>
                <div class="text-sm font-semibold" :class="form.status === 'active' ? 'text-success-700' : 'text-warning-700'">
                  {{ form.status === 'active' ? 'Already signed — mark as Active' : 'Not yet signed — mark as Pending' }}
                </div>
                <div class="text-xs mt-0.5" :class="form.status === 'active' ? 'text-success-600' : 'text-warning-600'">
                  {{ form.status === 'active' ? 'Historical lease — no e-signing required' : 'Will require e-signing before becoming active' }}
                </div>
              </div>
              <div
                class="w-10 h-6 rounded-full transition-colors flex-shrink-0 flex items-center px-0.5"
                :class="form.status === 'active' ? 'bg-success-500 justify-end' : 'bg-warning-100 justify-start'"
              >
                <div class="w-5 h-5 rounded-full bg-white shadow" />
              </div>
            </div>

            <!-- Property & Unit -->
            <section class="space-y-4">
              <SectionLabel text="Property" color="navy" />

              <!-- Locked: launched from a specific property page -->
              <div v-if="prefilledPropertyId" class="col-span-2 flex items-center gap-2 px-3 py-2 bg-navy/5 border border-navy/20 rounded-lg text-sm text-navy">
                <span class="font-medium">{{ properties.find(p => p.id === prefilledPropertyId)?.name || `Property #${prefilledPropertyId}` }}</span>
                <span class="text-xs text-gray-400 ml-auto">linked from property page</span>
              </div>

              <template v-else>
                <div class="grid grid-cols-2 gap-3">
                  <div class="col-span-2">
                    <label class="label">Match existing or create new</label>
                    <select v-model="useExistingProperty" class="input">
                      <option :value="false">+ Create new property</option>
                      <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
                    </select>
                  </div>
                  <template v-if="!useExistingProperty">
                    <div class="col-span-2">
                      <label class="label">Property name</label>
                      <input v-model="form.property.name" class="input" placeholder="e.g. 18 Irene Park" />
                    </div>
                    <div class="col-span-2">
                      <label class="label">Address</label>
                      <input v-model="form.property.address" class="input" placeholder="Street address" />
                    </div>
                    <div>
                      <label class="label">City</label>
                      <input v-model="form.property.city" class="input" />
                    </div>
                    <div>
                      <label class="label">Province</label>
                      <input v-model="form.property.province" class="input" />
                    </div>
                    <div>
                      <label class="label">Postal code</label>
                      <input v-model="form.property.postal_code" class="input" />
                    </div>
                    <div>
                      <label class="label">Type</label>
                      <select v-model="form.property.property_type" class="input">
                        <option value="house">House</option>
                        <option value="apartment">Apartment</option>
                        <option value="townhouse">Townhouse</option>
                        <option value="commercial">Commercial</option>
                      </select>
                    </div>
                  </template>
                </div>
              </template>

              <!-- Unit -->
              <div class="grid grid-cols-3 gap-3">
                <div :class="(!useExistingProperty || !useExistingUnit) ? 'col-span-1' : 'col-span-3'">
                  <label class="label">Unit</label>
                  <!-- Locked unit when launched from property page with a specific unit selected -->
                  <div v-if="prefilledUnitId" class="px-3 py-2 bg-navy/5 border border-navy/20 rounded-lg text-sm text-navy font-medium">
                    {{ unitsForProperty.find(u => u.id === prefilledUnitId)?.unit_number
                      ? `Unit ${unitsForProperty.find(u => u.id === prefilledUnitId)?.unit_number}`
                      : `Unit #${prefilledUnitId}` }}
                  </div>
                  <select v-else-if="useExistingProperty" v-model="useExistingUnit" class="input">
                    <option :value="false">+ Create new unit</option>
                    <option v-for="u in unitsForProperty" :key="u.id" :value="u.id">Unit {{ u.unit_number }}</option>
                  </select>
                  <input v-else v-model="form.unit.unit_number" class="input" placeholder="1" />
                </div>
                <template v-if="!useExistingProperty || !useExistingUnit">
                  <div>
                    <label class="label">Beds</label>
                    <input v-model.number="form.unit.bedrooms" type="number" class="input" />
                  </div>
                  <div>
                    <label class="label">Baths</label>
                    <input v-model.number="form.unit.bathrooms" type="number" class="input" />
                  </div>
                </template>
              </div>
            </section>

            <!-- Lease Terms -->
            <section class="space-y-3">
              <SectionLabel text="Lease Terms" color="purple" />
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="label">Start date</label>
                  <input v-model="form.start_date" type="date" class="input" />
                </div>
                <div>
                  <label class="label">End date</label>
                  <input v-model="form.end_date" type="date" class="input" />
                </div>
                <div>
                  <label class="label">Monthly rent (R)</label>
                  <input v-model="form.monthly_rent" type="number" class="input" />
                </div>
                <div>
                  <label class="label">Deposit (R)</label>
                  <input v-model="form.deposit" type="number" class="input" />
                </div>
                <div class="col-span-2">
                  <label class="label">Payment reference</label>
                  <input v-model="form.payment_reference" class="input" />
                </div>
                <div>
                  <label class="label">Max occupants</label>
                  <input v-model.number="form.max_occupants" type="number" class="input" />
                </div>
                <div class="flex items-end gap-5 pb-1">
                  <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input v-model="form.water_included" type="checkbox" class="rounded" /> Water incl.
                  </label>
                  <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input v-model="form.electricity_prepaid" type="checkbox" class="rounded" /> Prepaid elec.
                  </label>
                </div>
              </div>
            </section>

            <!-- Tenants — all equally liable signatories -->
            <section class="space-y-3">
              <div class="flex items-center justify-between">
                <SectionLabel text="Tenants — jointly & severally liable" color="navy" />
                <button v-if="form.co_tenants.length < 3" @click="form.co_tenants.push(emptyPerson())" class="btn-ghost text-xs px-2 py-1">
                  <Plus :size="12" /> Add tenant
                </button>
              </div>
              <!-- Tenant 1 (primary — first signatory) -->
              <div class="relative border border-navy/20 rounded-xl p-4 bg-navy/5">
                <span class="absolute top-3 left-4 text-micro font-semibold text-navy/50 uppercase tracking-wide">Tenant 1</span>
                <div class="pt-4">
                  <PersonBlock v-model="form.primary_tenant" />
                </div>
              </div>
              <!-- Tenant 2, 3, 4 -->
              <div v-for="(ct, i) in form.co_tenants" :key="i" class="relative border border-navy/20 rounded-xl p-4 bg-navy/5">
                <span class="absolute top-3 left-4 text-micro font-semibold text-navy/50 uppercase tracking-wide">Tenant {{ i + 2 }}</span>
                <button @click="form.co_tenants.splice(i, 1)" class="absolute top-2.5 right-3 text-gray-400 hover:text-danger-500"><X :size="14" /></button>
                <div class="pt-4">
                  <PersonBlock v-model="form.co_tenants[i]" compact />
                </div>
              </div>
            </section>

            <!-- Occupants -->
            <section class="space-y-3">
              <div class="flex items-center justify-between">
                <SectionLabel text="Occupants — physical residents" color="green" />
                <button @click="form.occupants.push({ ...emptyPerson(), relationship_to_tenant: 'self' })" class="btn-ghost text-xs px-2 py-1">
                  <Plus :size="12" /> Add
                </button>
              </div>
              <div v-for="(oc, i) in form.occupants" :key="i" class="relative border border-success-100 rounded-xl p-4 bg-success-50/40">
                <button @click="form.occupants.splice(i, 1)" class="absolute top-3 right-3 text-gray-400 hover:text-danger-500"><X :size="14" /></button>
                <PersonBlock v-model="form.occupants[i]" compact />
                <div class="mt-2">
                  <label class="label">Relationship to tenant</label>
                  <input v-model="form.occupants[i].relationship_to_tenant" class="input text-xs" placeholder="self, spouse, child…" />
                </div>
              </div>
              <p v-if="!form.occupants.length" class="text-xs text-gray-400">None</p>
            </section>

            <!-- Guarantors -->
            <section class="space-y-3">
              <div class="flex items-center justify-between">
                <SectionLabel text="Guarantors / Sureties" color="amber" />
                <button @click="form.guarantors.push({ ...emptyPerson(), for_tenant: '' })" class="btn-ghost text-xs px-2 py-1">
                  <Plus :size="12" /> Add
                </button>
              </div>
              <div v-for="(g, i) in form.guarantors" :key="i" class="relative border border-warning-100 rounded-xl p-4 bg-warning-50/40">
                <button @click="form.guarantors.splice(i, 1)" class="absolute top-3 right-3 text-gray-400 hover:text-danger-500"><X :size="14" /></button>
                <PersonBlock v-model="form.guarantors[i]" compact />
                <div class="mt-2">
                  <label class="label">Covers tenant</label>
                  <input v-model="form.guarantors[i].for_tenant" class="input text-xs" placeholder="Name of the tenant they cover" />
                </div>
              </div>
              <p v-if="!form.guarantors.length" class="text-xs text-gray-400">None</p>
            </section>

            <!-- Supporting Documents -->
            <section class="space-y-3">
              <div class="flex items-center justify-between">
                <SectionLabel text="Supporting Documents" color="gray" />
                <button
                  @click="extraDocs.push({ personRole: 'primary_tenant', type: 'id_copy', description: '', file: null })"
                  class="btn-ghost text-xs px-2 py-1"
                >
                  <Plus :size="12" /> Add document
                </button>
              </div>

              <div v-if="!extraDocs.length" class="text-xs text-gray-400">
                Optionally attach ID copies, proof of address or income. These are saved against the person and available for future leases.
              </div>

              <div
                v-for="(doc, i) in extraDocs"
                :key="i"
                class="relative border border-gray-200 rounded-xl p-4 bg-gray-50/40 space-y-2"
              >
                <button @click="extraDocs.splice(i, 1)" class="absolute top-3 right-3 text-gray-400 hover:text-danger-500">
                  <X :size="14" />
                </button>

                <div class="grid grid-cols-2 gap-2 pr-5">
                  <!-- Person selector -->
                  <div>
                    <label class="label">Person</label>
                    <select v-model="doc.personRole" class="input text-xs">
                      <option value="primary_tenant">
                        {{ form.primary_tenant.full_name || 'Tenant 1' }}
                      </option>
                      <option v-for="(ct, ci) in form.co_tenants" :key="'ct'+ci" :value="`co_tenant_${ci}`">
                        {{ ct.full_name || `Co-tenant ${ci + 2}` }}
                      </option>
                      <option v-for="(g, gi) in form.guarantors" :key="'g'+gi" :value="`guarantor_${gi}`">
                        {{ g.full_name || `Guarantor ${gi + 1}` }} (surety)
                      </option>
                    </select>
                  </div>

                  <!-- Document type -->
                  <div>
                    <label class="label">Type</label>
                    <select v-model="doc.type" class="input text-xs">
                      <option value="id_copy">ID / Passport Copy</option>
                      <option value="proof_of_address">Proof of Address</option>
                      <option value="proof_of_income">Proof of Income</option>
                      <option value="fica">FICA / KYC Document</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                <!-- Description -->
                <div>
                  <label class="label">Description <span class="text-gray-400 font-normal">(optional)</span></label>
                  <input v-model="doc.description" class="input text-xs" placeholder="e.g. Edwin Hanekom — SA ID" />
                </div>

                <!-- File picker -->
                <div>
                  <label class="label">File</label>
                  <div class="flex items-center gap-2">
                    <label
                      class="flex-1 flex items-center gap-2 px-3 py-2 border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-navy transition-colors text-xs text-gray-500"
                    >
                      <FileText :size="13" class="flex-shrink-0" />
                      <span class="truncate">{{ doc.file ? doc.file.name : 'Choose file (PDF, JPG, PNG)' }}</span>
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        class="hidden"
                        @change="(e: any) => { doc.file = e.target.files?.[0] ?? null; e.target.value = '' }"
                      />
                    </label>
                    <button v-if="doc.file" @click="doc.file = null" class="text-gray-400 hover:text-danger-500 flex-shrink-0">
                      <X :size="13" />
                    </button>
                  </div>
                </div>
              </div>
            </section>

          </div>
        </div>
      </div>

      <!-- Step 3: Done -->
      <div v-if="step === 3" class="flex-1 flex items-center justify-center">
        <div class="text-center space-y-4 max-w-sm">
          <div class="w-16 h-16 rounded-2xl bg-success-100 flex items-center justify-center mx-auto">
            <CheckCircle2 :size="32" class="text-success-600" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-lg">Lease imported!</div>
            <div class="text-sm text-gray-500 mt-1">Property, tenants and contract have been created.</div>
          </div>
          <div class="flex gap-2 justify-center pt-2">
            <button class="btn-ghost" @click="reset">Import another</button>
            <button class="btn-primary" @click="$emit('done')">View leases</button>
          </div>
        </div>
      </div>

      <!-- Footer (step 2 only) -->
      <div v-if="step === 2" class="flex items-center justify-between px-6 py-4 border-t border-gray-200 flex-shrink-0 bg-white">
        <div v-if="importError" class="flex items-center gap-2 text-sm text-danger-600">
          <AlertCircle :size="14" />
          {{ importError }}
        </div>
        <div v-else class="text-xs text-gray-400">Review details against the PDF, then create the lease</div>
        <div class="flex gap-2">
          <button class="btn-ghost" @click="step = 1">Back</button>
          <button class="btn-primary" :disabled="importing" @click="doImport">
            <Loader2 v-if="importing" :size="14" class="animate-spin" />
            {{ importing ? 'Creating…' : 'Create Lease' }}
          </button>
        </div>
      </div>

    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineComponent, h } from 'vue'
import api from '../../api'
import {
  Sparkles, X, FileText, AlertCircle, CheckCircle2,
  Loader2, Plus, ChevronRight, Clock, ArrowLeft,
} from 'lucide-vue-next'
import { usePropertiesStore } from '../../stores/properties'
import { useLeasesStore } from '../../stores/leases'

const DRAFT_KEY = 'lease_import_draft'

const props = defineProps<{
  prefilledPropertyId?: number
  prefilledPropertyName?: string
  prefilledUnitId?: number
}>()

const emit = defineEmits<{ close: []; done: [] }>()

// ── Inline sub-components ──────────────────────────────────────────────────

const SectionLabel = defineComponent({
  props: { text: String, color: String },
  setup(props) {
    const colors: Record<string, string> = {
      navy: 'text-navy', blue: 'text-info-600', green: 'text-success-600',
      amber: 'text-warning-600', purple: 'text-violet-600',
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
          h('input', { class: cls + ' font-mono', value: p.id_number, placeholder: 'ID number', 'data-clarity-mask': 'true', onInput: (e: any) => upd('id_number', e.target.value) }),
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

// ── Draft persistence ───────────────────────────────────────────────────────

const hasDraft = ref(false)
const draftSavedAt = ref('')

function saveDraft() {
  localStorage.setItem(DRAFT_KEY, JSON.stringify({
    form: form.value,
    rawParsed: rawParsed.value,
    pdfFileName: pdfFileName.value,
    useExistingProperty: useExistingProperty.value,
    useExistingUnit: useExistingUnit.value,
    savedAt: new Date().toISOString(),
  }))
}

function restoreDraft() {
  const raw = localStorage.getItem(DRAFT_KEY)
  if (!raw) return
  try {
    const d = JSON.parse(raw)
    form.value = d.form
    rawParsed.value = d.rawParsed
    pdfFileName.value = d.pdfFileName ?? ''
    useExistingProperty.value = d.useExistingProperty ?? false
    useExistingUnit.value = d.useExistingUnit ?? false
    hasDraft.value = false
    step.value = 2
  } catch { /* ignore corrupt draft */ }
}

function clearDraft() {
  localStorage.removeItem(DRAFT_KEY)
  hasDraft.value = false
  draftSavedAt.value = ''
}

function draftAge() {
  if (!draftSavedAt.value) return ''
  const diff = Date.now() - new Date(draftSavedAt.value).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ── State ──────────────────────────────────────────────────────────────────

const step = ref(1)
const dragging = ref(false)
/** Nested dragenter/dragleave on children would flicker without a counter */
let dragDepth = 0
const parsing = ref(false)
const importing = ref(false)
const parseError = ref('')
const importError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const propertiesStore = usePropertiesStore()
const leasesStore = useLeasesStore()
const properties = computed(() => propertiesStore.list)
const useExistingProperty = ref<number | false>(false)
const useExistingUnit = ref<number | false>(false)
const rawParsed = ref<any>(null)
const pdfUrl = ref('')
const pdfFileName = ref('')
const pdfFile = ref<File | null>(null)  // keep the original File for auto-upload

interface ExtraDoc {
  personRole: string  // 'primary_tenant' | 'co_tenant_0' | 'guarantor_0' | etc.
  type: string
  description: string
  file: File | null
}
const extraDocs = ref<ExtraDoc[]>([])

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
  notice_period_days: 20,
  early_termination_penalty_months: 3,
  status: 'active' as 'active' | 'pending',
  primary_tenant: emptyPerson(),
  co_tenants: [] as any[],
  occupants: [] as any[],
  guarantors: [] as any[],
})

const unitsForProperty = computed(() => {
  if (!useExistingProperty.value) return []
  return properties.value.find((p: any) => p.id === useExistingProperty.value)?.units ?? []
})

async function loadProperties() {
  await propertiesStore.fetchAll()
}

onMounted(() => {
  loadProperties()
  // Pre-fill property/unit when launched from the property detail page
  if (props.prefilledPropertyId) {
    useExistingProperty.value = props.prefilledPropertyId
    if (props.prefilledUnitId) useExistingUnit.value = props.prefilledUnitId
    // Skip draft restore when context is already provided
    return
  }
  // Check for an unsubmitted draft
  const raw = localStorage.getItem(DRAFT_KEY)
  if (raw) {
    try {
      const d = JSON.parse(raw)
      hasDraft.value = true
      draftSavedAt.value = d.savedAt ?? ''
    } catch { localStorage.removeItem(DRAFT_KEY) }
  }
})

onUnmounted(() => {
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
})

// ── Upload / parse ─────────────────────────────────────────────────────────

function isPdfFile(f: File): boolean {
  const t = (f.type || '').toLowerCase()
  if (t === 'application/pdf' || t === 'application/x-pdf') return true
  return f.name.toLowerCase().endsWith('.pdf')
}

function onDragEnter() {
  dragDepth += 1
  dragging.value = true
}

function onDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragging.value = false
}

function onDragOver(e: DragEvent) {
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function onDrop(e: DragEvent) {
  dragDepth = 0
  dragging.value = false
  const list = e.dataTransfer?.files
  if (!list?.length) return
  const file = Array.from(list).find(isPdfFile)
  if (!file) {
    parseError.value =
      'Please drop a PDF file. (Some browsers hide the file type — we also accept any file named .pdf)'
    return
  }
  parseError.value = ''
  parsePDF(file)
}

function onDropzoneClick() {
  if (parsing.value) return
  fileInput.value?.click()
}

function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file && isPdfFile(file)) {
    parseError.value = ''
    parsePDF(file)
  } else if (file) {
    parseError.value = 'Please choose a PDF file (.pdf).'
  }
}

async function parsePDF(file: File) {
  // Keep the file for auto-upload after import
  pdfFile.value = file
  // Create object URL immediately so it's ready when step 2 renders
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
  pdfUrl.value = URL.createObjectURL(file)
  pdfFileName.value = file.name

  parsing.value = true
  parseError.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await api.post('/leases/parse-document/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    rawParsed.value = data
    applyParsed(data)
    saveDraft()
    step.value = 2
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.response?.data ?? e?.message ?? 'Unknown error'
    parseError.value = typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2)
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  } finally {
    parsing.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function applyParsed(d: any) {
  if (d.monthly_rent)        form.value.monthly_rent = d.monthly_rent
  if (d.deposit)             form.value.deposit = d.deposit
  if (d.start_date)          form.value.start_date = d.start_date
  if (d.end_date)            form.value.end_date = d.end_date
  if (d.payment_reference)   form.value.payment_reference = d.payment_reference
  if (d.max_occupants)       form.value.max_occupants = d.max_occupants
  if (d.water_included != null)      form.value.water_included = d.water_included
  if (d.electricity_prepaid != null) form.value.electricity_prepaid = d.electricity_prepaid
  if (d.water_limit_litres)  form.value.water_limit_litres = d.water_limit_litres
  if (d.notice_period_days)  form.value.notice_period_days = d.notice_period_days
  if (d.early_termination_penalty_months) form.value.early_termination_penalty_months = d.early_termination_penalty_months

  const p = d.property
  if (p && typeof p === 'object') {
    if (p.name) form.value.property.name = String(p.name)
    if (p.address || p.full_address) form.value.property.address = String(p.address || p.full_address)
    if (p.city) form.value.property.city = String(p.city)
    if (p.province) form.value.property.province = String(p.province)
    if (p.postal_code != null && p.postal_code !== '') form.value.property.postal_code = String(p.postal_code)
    if (p.property_type) form.value.property.property_type = String(p.property_type)
  }

  if (d.property_name) form.value.property.name = String(d.property_name)
  if (d.property_address) form.value.property.address = String(d.property_address)
  if (d.property_city) form.value.property.city = String(d.property_city)
  if (d.property_province) form.value.property.province = String(d.property_province)
  if (d.property_postal_code != null && d.property_postal_code !== '') {
    form.value.property.postal_code = String(d.property_postal_code)
  }
  if (d.property_type) form.value.property.property_type = String(d.property_type)

  if (form.value.property.address && !form.value.property.name.trim()) {
    form.value.property.name = form.value.property.address.split(',')[0].trim()
  }

  if (d.unit_number) form.value.unit.unit_number = String(d.unit_number)

  if (d.primary_tenant) form.value.primary_tenant = pick(d.primary_tenant)
  if (d.co_tenants?.length)  form.value.co_tenants  = d.co_tenants.map(pick)
  if (d.occupants?.length)   form.value.occupants   = d.occupants.map((o: any) => ({ ...pick(o), relationship_to_tenant: o.relationship_to_tenant || 'self' }))
  if (d.guarantors?.length)  form.value.guarantors  = d.guarantors.map((g: any) => ({ ...pick(g), for_tenant: g.for_tenant || '' }))
}

function pick(p: any) {
  return { full_name: p.full_name || '', id_number: p.id_number || '', phone: p.phone || '', email: p.email || '' }
}

// ── Import ─────────────────────────────────────────────────────────────────

async function doImport() {
  importing.value = true
  importError.value = ''
  try {
    const payload: any = { ...form.value, ai_parse_result: rawParsed.value }
    if (useExistingProperty.value) {
      payload.property_id = useExistingProperty.value
      if (useExistingUnit.value) payload.unit_id = useExistingUnit.value
    }
    const created = await leasesStore.importLease(payload)

    // Auto-attach the original PDF as a signed_lease document
    if (pdfFile.value && created.id) {
      const fd = new FormData()
      fd.append('file', pdfFile.value)
      fd.append('document_type', 'signed_lease')
      fd.append('description', pdfFileName.value)
      await api.post(`/leases/${created.id}/documents/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    }

    // Upload supporting documents to the correct Person record
    if (extraDocs.value.length) {
      const personIdMap: Record<string, number> = {
        primary_tenant: created.primary_tenant_id,
        ...(created.co_tenant_person_ids ?? []).reduce((acc: Record<string, number>, id: number, i: number) => {
          acc[`co_tenant_${i}`] = id
          return acc
        }, {}),
        ...(created.guarantor_person_ids ?? []).reduce((acc: Record<string, number>, id: number, i: number) => {
          acc[`guarantor_${i}`] = id
          return acc
        }, {}),
      }
      for (const doc of extraDocs.value) {
        if (!doc.file) continue
        const personId = personIdMap[doc.personRole]
        if (!personId) continue
        const fd = new FormData()
        fd.append('file', doc.file)
        fd.append('document_type', doc.type)
        fd.append('description', doc.description)
        await api.post(`/auth/persons/${personId}/documents/`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
    }

    clearDraft()
    step.value = 3
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.response?.data ?? e?.message ?? 'Import failed'
    importError.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    importing.value = false
  }
}

function reset() {
  if (pdfUrl.value) { URL.revokeObjectURL(pdfUrl.value); pdfUrl.value = '' }
  pdfFileName.value = ''
  pdfFile.value = null
  clearDraft()
  step.value = 1
  loadProperties()  // refresh so newly created properties appear
  parseError.value = ''
  importError.value = ''
  rawParsed.value = null
  useExistingProperty.value = false
  useExistingUnit.value = false
  extraDocs.value = []
  form.value = {
    property: { name: '', address: '', city: '', province: '', postal_code: '', property_type: 'house' },
    unit: { unit_number: '1', bedrooms: 1, bathrooms: 1 },
    start_date: '', end_date: '', monthly_rent: '', deposit: '',
    payment_reference: '', max_occupants: 1, status: 'active' as 'active' | 'pending',
    water_included: true, electricity_prepaid: true,
    water_limit_litres: 4000, notice_period_days: 20,
    early_termination_penalty_months: 3,
    primary_tenant: emptyPerson(),
    co_tenants: [], occupants: [], guarantors: [],
  }
}
</script>
