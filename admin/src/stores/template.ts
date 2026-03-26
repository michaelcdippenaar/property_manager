import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

// ── Types ─────────────────────────────────────────────────────────────────
export interface DocField {
  name: string
  type: string        // text, date, number, signature, initials, checkbox, etc.
  party?: string      // Landlord, Tenant, Witness, etc.
  position?: { top: string; left: string; width: string; height: string }
}

export interface DocJson {
  v: 1
  html: string        // clean HTML with {{ref}} markers
  fields: DocField[]  // structured field metadata
}

export interface TemplateInfo {
  id: number
  name: string
  version: string
  is_active: boolean
  fields_schema: string[]
  content_html: string
  docx_file: string | null
  detected_variables?: Record<string, string[]>
}

export interface PreviewData {
  type: 'docx' | 'pdf'
  name: string
  fields: string[]
  paragraphs: { style: string; text: string }[]
  content_html: string
  pdf_url?: string
}

// ── Store ─────────────────────────────────────────────────────────────────
export const useTemplateStore = defineStore('template', () => {
  // State
  const template = ref<TemplateInfo | null>(null)
  const preview = ref<PreviewData | null>(null)
  const document = ref<DocJson>({ v: 1, html: '', fields: [] })
  const savedDocument = ref<DocJson>({ v: 1, html: '', fields: [] })
  const loading = ref(false)
  const saving = ref(false)
  const headerHtml = ref('')
  const footerHtml = ref('')

  // Computed
  const isDirty = computed(() =>
    document.value.html !== savedDocument.value.html ||
    JSON.stringify(document.value.fields) !== JSON.stringify(savedDocument.value.fields)
  )
  const templateId = computed(() => template.value?.id ?? null)
  const allFields = computed(() => document.value.fields)
  const fieldNames = computed(() => document.value.fields.map(f => f.name))

  // ── Parse stored content (JSON or legacy HTML) ────────────────────────
  function parseStoredContent(raw: string): DocJson {
    if (!raw) return { v: 1, html: '', fields: [] }
    try {
      const doc = JSON.parse(raw) as DocJson
      if (doc.v === 1 && typeof doc.html === 'string') return doc
    } catch { /* not JSON — legacy HTML */ }
    return { v: 1, html: raw, fields: [] }
  }

  // ── Load template from backend ────────────────────────────────────────
  async function loadTemplate(id: number) {
    loading.value = true
    try {
      const { data } = await api.get(`/leases/templates/${id}/`)
      template.value = data

      if (data.header_html) headerHtml.value = data.header_html
      else if (data.name) headerHtml.value = data.name
      if (data.footer_html) footerHtml.value = data.footer_html

      if (data.content_html) {
        const doc = parseStoredContent(data.content_html)
        document.value = doc
        savedDocument.value = { ...doc, fields: [...doc.fields] }
      }
    } finally {
      loading.value = false
    }
  }

  // ── Load preview from backend ─────────────────────────────────────────
  async function loadPreview(id: number) {
    try {
      const { data } = await api.get(`/leases/templates/${id}/preview/`)
      preview.value = data
      return data
    } catch {
      return null
    }
  }

  // ── Update document in store (called by editor on every change) ───────
  function updateDocument(doc: DocJson) {
    document.value = doc
  }

  function updateHtml(html: string) {
    document.value = { ...document.value, html }
  }

  function updateFields(fields: DocField[]) {
    document.value = { ...document.value, fields }
  }

  // ── Save to backend ───────────────────────────────────────────────────
  let _saveTimer: ReturnType<typeof setTimeout> | null = null

  async function save() {
    if (!template.value) return false
    saving.value = true
    try {
      const json = JSON.stringify(document.value)
      await api.patch(`/leases/templates/${template.value.id}/`, {
        content_html: json,
        header_html: headerHtml.value,
        footer_html: footerHtml.value,
      })
      savedDocument.value = { ...document.value, fields: [...document.value.fields] }
      if (template.value) template.value.content_html = json
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }

  function debouncedSave(ms = 2000) {
    if (_saveTimer) clearTimeout(_saveTimer)
    _saveTimer = setTimeout(() => save(), ms)
  }

  function cancelPendingSave() {
    if (_saveTimer) { clearTimeout(_saveTimer); _saveTimer = null }
  }

  // ── Reset state ───────────────────────────────────────────────────────
  function $reset() {
    cancelPendingSave()
    template.value = null
    preview.value = null
    document.value = { v: 1, html: '', fields: [] }
    savedDocument.value = { v: 1, html: '', fields: [] }
    headerHtml.value = ''
    footerHtml.value = ''
    loading.value = false
    saving.value = false
  }

  return {
    // State
    template,
    preview,
    document,
    savedDocument,
    loading,
    saving,
    headerHtml,
    footerHtml,
    // Computed
    isDirty,
    templateId,
    allFields,
    fieldNames,
    // Actions
    parseStoredContent,
    loadTemplate,
    loadPreview,
    updateDocument,
    updateHtml,
    updateFields,
    save,
    debouncedSave,
    cancelPendingSave,
    $reset,
  }
})
