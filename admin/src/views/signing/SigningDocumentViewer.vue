<template>
  <div class="signing-document-viewer">
    <editor-content :editor="editor" class="signing-editor-content" />
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
})

provide('signingContext', signingContext)

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style>
.signing-document-viewer {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px;
}

.signing-editor-content .tiptap {
  padding: 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  font-family: Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #111;
}

.signing-editor-content .tiptap h1 {
  font-size: 14pt;
  font-weight: bold;
  text-align: center;
  margin-bottom: 12pt;
}

.signing-editor-content .tiptap h2 {
  font-size: 11pt;
  font-weight: bold;
  margin: 8pt 0 3pt;
}

.signing-editor-content .tiptap table {
  border-collapse: collapse;
  width: 100%;
  margin: 4pt 0;
}

.signing-editor-content .tiptap td,
.signing-editor-content .tiptap th {
  border: 1px solid #d1d5db;
  padding: 5pt 7pt;
  font-size: 10pt;
}
</style>
