import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

// ── Types ─────────────────────────────────────────────────────────────────

export type BuilderStatus = 'drafting' | 'review' | 'finalized'
export type LeaseStatus = 'pending' | 'active' | 'expired' | 'terminated'
export type SigningStatus = 'pending' | 'in_progress' | 'completed' | 'declined' | 'expired'

export type LifecyclePhase = 'template' | 'build' | 'signing' | 'active' | 'complete'

export interface Person {
  id: number
  full_name: string
  person_type: 'individual' | 'company'
  id_number?: string
  company_reg?: string
  vat_number?: string
  phone?: string
  email?: string
}

export interface LeaseTemplate {
  id: number
  name: string
  version: string
  province: string
  is_active: boolean
  fields_schema: string[]
  content_html: string
  has_docx: boolean
}

export interface BuilderSession {
  id: number
  template: LeaseTemplate | null
  lease: { id: number } | null
  messages: { role: string; content: string }[]
  current_state: Record<string, any>
  rha_flags: string[]
  status: BuilderStatus
  created_at: string
  updated_at: string
}

export interface Lease {
  id: number
  unit: {
    id: number
    unit_number: string
    property: { id: number; name: string; address: string }
  }
  primary_tenant: Person | null
  start_date: string
  end_date: string
  monthly_rent: string
  deposit: string
  status: LeaseStatus
  max_occupants: number
  lease_number: string
  payment_reference: string
  created_at: string
}

export interface SigningSubmission {
  id: number
  lease: { id: number }
  docuseal_submission_id: string
  status: SigningStatus
  signing_mode: 'parallel' | 'sequential'
  signers: { id: number; name: string; email: string; status: string }[]
  signed_pdf_url: string
  created_at: string
  updated_at: string
}

export interface LeaseEvent {
  id: number
  event_type: string
  title: string
  description: string
  date: string
  status: string
  is_recurring: boolean
}

export interface OnboardingStep {
  id: number
  step_type: string
  title: string
  is_completed: boolean
  completed_at: string | null
  notes: string
  order: number
}

export interface LeaseDocument {
  id: number
  document_type: string
  file: string
  description: string
  uploaded_at: string
}

// ── GraphQL helpers ───────────────────────────────────────────────────────

const GQL_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/graphql/'

async function gql<T = any>(query: string, variables: Record<string, any> = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const res = await fetch(GQL_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query, variables }),
  })
  const json = await res.json()
  if (json.errors?.length) {
    console.error('[GraphQL]', json.errors)
    throw new Error(json.errors[0].message)
  }
  return json.data
}

// ── Fragments ─────────────────────────────────────────────────────────────

const LEASE_FIELDS = `
  id leaseNumber status startDate endDate monthlyRent deposit
  maxOccupants paymentReference createdAt
  unit { id unitNumber property { id name address city } }
  primaryTenant { id fullName personType idNumber companyReg phone email }
`

const BUILDER_FIELDS = `
  id status currentState rhaFlags createdAt updatedAt
  template { id name version }
  lease { id }
`

const SIGNING_FIELDS = `
  id status signingMode signers signedPdfUrl
  docusealSubmissionId createdAt updatedAt
`

// ── Store ─────────────────────────────────────────────────────────────────

export const useContractStore = defineStore('contract', () => {
  // ── State ───────────────────────────────────────────────────────────
  const templates = ref<LeaseTemplate[]>([])
  const currentTemplate = ref<LeaseTemplate | null>(null)
  const builderSession = ref<BuilderSession | null>(null)
  const lease = ref<Lease | null>(null)
  const signing = ref<SigningSubmission | null>(null)
  const events = ref<LeaseEvent[]>([])
  const onboarding = ref<OnboardingStep[]>([])
  const documents = ref<LeaseDocument[]>([])
  const coTenants = ref<Person[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Computed ────────────────────────────────────────────────────────

  const phase = computed<LifecyclePhase>(() => {
    if (signing.value?.status === 'completed') return 'complete'
    if (signing.value) return 'signing'
    if (lease.value && lease.value.status === 'active') return 'active'
    if (builderSession.value) return 'build'
    return 'template'
  })

  const leaseId = computed(() => lease.value?.id ?? null)
  const templateId = computed(() => currentTemplate.value?.id ?? null)

  const onboardingProgress = computed(() => {
    if (!onboarding.value.length) return 0
    const done = onboarding.value.filter(s => s.is_completed).length
    return Math.round((done / onboarding.value.length) * 100)
  })

  const signerProgress = computed(() => {
    if (!signing.value?.signers?.length) return { completed: 0, total: 0 }
    const total = signing.value.signers.length
    const completed = signing.value.signers.filter(s => s.status === 'completed').length
    return { completed, total }
  })

  // ── Template actions ────────────────────────────────────────────────

  async function fetchTemplates() {
    const data = await gql<{ allLeaseTemplates: LeaseTemplate[] }>(`
      query { allLeaseTemplates { id name version province isActive fieldsSchema } }
    `)
    templates.value = data.allLeaseTemplates
  }

  async function fetchTemplate(id: number) {
    const data = await gql<{ leaseTemplate: LeaseTemplate }>(`
      query($id: ID!) {
        leaseTemplate(id: $id) { id name version province isActive fieldsSchema contentHtml headerHtml footerHtml }
      }
    `, { id })
    currentTemplate.value = data.leaseTemplate
  }

  async function updateTemplate(id: number, input: Partial<LeaseTemplate>) {
    const data = await gql<{ updateLeaseTemplate: { leaseTemplate: LeaseTemplate } }>(`
      mutation($id: ID!, $input: LeaseTemplateInput!) {
        updateLeaseTemplate(id: $id, input: $input) { leaseTemplate { id name version isActive } }
      }
    `, { id, input })
    currentTemplate.value = data.updateLeaseTemplate.leaseTemplate
  }

  // ── Builder actions ─────────────────────────────────────────────────

  async function fetchBuilderSession(id: number) {
    const data = await gql<{ builderSession: BuilderSession }>(`
      query($id: ID!) { builderSession(id: $id) { ${BUILDER_FIELDS} } }
    `, { id })
    builderSession.value = data.builderSession
  }

  async function updateBuilderState(id: number, currentState: Record<string, any>) {
    const data = await gql<{ updateBuilderSession: { builderSession: BuilderSession } }>(`
      mutation($id: ID!, $currentState: JSONString) {
        updateBuilderSession(id: $id, currentState: $currentState) {
          builderSession { ${BUILDER_FIELDS} }
        }
      }
    `, { id, currentState: JSON.stringify(currentState) })
    builderSession.value = data.updateBuilderSession.builderSession
  }

  async function finalizeBuilder(id: number) {
    const data = await gql<{ updateBuilderSession: { builderSession: BuilderSession } }>(`
      mutation($id: ID!) {
        updateBuilderSession(id: $id, status: "finalized") {
          builderSession { ${BUILDER_FIELDS} }
        }
      }
    `, { id })
    builderSession.value = data.updateBuilderSession.builderSession
  }

  // ── Lease actions ───────────────────────────────────────────────────

  async function fetchLease(id: number) {
    loading.value = true
    try {
      const data = await gql<{ lease: Lease }>(`
        query($id: ID!) { lease(id: $id) { ${LEASE_FIELDS} } }
      `, { id })
      lease.value = data.lease
    } finally {
      loading.value = false
    }
  }

  async function fetchLeaseLifecycle(id: number) {
    loading.value = true
    try {
      const data = await gql<{
        lease: Lease
        signingSubmissionsForLease: SigningSubmission[]
        leaseEvents: LeaseEvent[]
        onboardingSteps: OnboardingStep[]
        leaseDocuments: LeaseDocument[]
        leaseCoTenants: { person: Person }[]
      }>(`
        query($id: ID!) {
          lease(id: $id) { ${LEASE_FIELDS} }
          signingSubmissionsForLease(leaseId: $id) { ${SIGNING_FIELDS} }
          leaseEvents(leaseId: $id) { id eventType title description date status isRecurring }
          onboardingSteps(leaseId: $id) { id stepType title isCompleted completedAt notes order }
          leaseDocuments(leaseId: $id) { id documentType file description uploadedAt }
          leaseCoTenants(leaseId: $id) { person { id fullName phone email } }
        }
      `, { id })

      lease.value = data.lease
      signing.value = data.signingSubmissionsForLease?.[0] ?? null
      events.value = data.leaseEvents
      onboarding.value = data.onboardingSteps
      documents.value = data.leaseDocuments
      coTenants.value = data.leaseCoTenants.map(ct => ct.person)
    } finally {
      loading.value = false
    }
  }

  async function updateLeaseStatus(id: number, status: LeaseStatus) {
    const data = await gql<{ updateLeaseStatus: { lease: Lease } }>(`
      mutation($id: ID!, $status: String!) {
        updateLeaseStatus(id: $id, status: $status) { lease { ${LEASE_FIELDS} } }
      }
    `, { id, status })
    lease.value = data.updateLeaseStatus.lease
  }

  // ── Signing actions ─────────────────────────────────────────────────

  async function fetchSigning(leaseId: number) {
    const data = await gql<{ signingSubmissionsForLease: SigningSubmission[] }>(`
      query($id: ID!) { signingSubmissionsForLease(leaseId: $id) { ${SIGNING_FIELDS} } }
    `, { id: leaseId })
    signing.value = data.signingSubmissionsForLease?.[0] ?? null
  }

  async function refreshSigningStatus() {
    if (!signing.value) return
    const data = await gql<{ signingSubmission: SigningSubmission }>(`
      query($id: ID!) { signingSubmission(id: $id) { ${SIGNING_FIELDS} } }
    `, { id: signing.value.id })
    signing.value = data.signingSubmission
  }

  // ── Onboarding actions ──────────────────────────────────────────────

  async function completeOnboardingStep(stepId: number, notes?: string) {
    const data = await gql<{ completeOnboardingStep: { step: OnboardingStep } }>(`
      mutation($id: ID!, $notes: String) {
        completeOnboardingStep(id: $id, notes: $notes) {
          step { id stepType title isCompleted completedAt notes order }
        }
      }
    `, { id: stepId, notes })
    const updated = data.completeOnboardingStep.step
    const idx = onboarding.value.findIndex(s => s.id === updated.id)
    if (idx >= 0) onboarding.value[idx] = updated
  }

  // ── Reset ───────────────────────────────────────────────────────────

  function $reset() {
    currentTemplate.value = null
    builderSession.value = null
    lease.value = null
    signing.value = null
    events.value = []
    onboarding.value = []
    documents.value = []
    coTenants.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    templates, currentTemplate, builderSession, lease, signing,
    events, onboarding, documents, coTenants, loading, error,
    // Computed
    phase, leaseId, templateId, onboardingProgress, signerProgress,
    // Template
    fetchTemplates, fetchTemplate, updateTemplate,
    // Builder
    fetchBuilderSession, updateBuilderState, finalizeBuilder,
    // Lease
    fetchLease, fetchLeaseLifecycle, updateLeaseStatus,
    // Signing
    fetchSigning, refreshSigningStatus,
    // Onboarding
    completeOnboardingStep,
    // Reset
    $reset,
  }
})
