<template>
  <div class="signing-document-viewer" style="background:#f1f3f4;">
    <div class="max-w-[816px] mx-auto py-6 px-4">
      <editor-content
        :editor="editor"
        class="tiptap-editor bg-white"
        style="box-shadow: 0 0 0 1px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { provide, reactive, onBeforeUnmount } from 'vue'
import { EditorContent } from '@tiptap/vue-3'
import { useTiptapEditor } from '../../composables/useTiptapEditor'

const props = defineProps<{
  html: string
  signerRole: string
  signedFields: Map<string, { imageData: string; signedAt: string }>
  alreadySigned: Array<{ fieldName: string; fieldType: string; signerName: string; signedAt: string }>
  onFieldClick: (fieldName: string, fieldType: string) => void
  capturedFields: Record<string, string>
  onMergeFieldChange: (fieldName: string, value: string) => void
}>()

const { editor } = useTiptapEditor({
  content: props.html,
  editable: false,
})

// Provide signing context to SignatureBlockComponent via inject
const signingContext = reactive({
  signerRole: props.signerRole,
  signedFields: props.signedFields,
  alreadySigned: props.alreadySigned,
  onFieldClick: props.onFieldClick,
  capturedFields: props.capturedFields,
  onMergeFieldChange: props.onMergeFieldChange,
})

provide('signingContext', signingContext)

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style>
@import '../../styles/tiptap-editor.css';

.signing-document-viewer {
  min-height: 100%;
}

/* Hide drag handles and resize controls in signing mode */
.signing-document-viewer .tiptap-editor [data-drag-handle] {
  cursor: default !important;
}
.signing-document-viewer .tiptap-editor .column-resize-handle {
  display: none;
}

/* Hide page break labels in signing mode */
.signing-document-viewer .tiptap-editor .tiptap div[data-page-break]::after {
  display: none;
}
</style>
