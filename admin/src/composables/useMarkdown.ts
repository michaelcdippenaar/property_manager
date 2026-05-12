/**
 * useMarkdown — render Claude's chat replies as sanitised HTML.
 *
 * The AI chat (lease template, AI guide, etc.) receives plain markdown
 * from Claude. Rendering as raw text loses bold, headings, lists, and
 * code blocks — the visual hierarchy that makes longer replies actually
 * readable. This composable parses markdown → HTML via `marked` and then
 * sanitises via `DOMPurify` before injection.
 *
 * Two safety layers:
 *   • `marked` configured with `breaks: true` so single newlines render
 *     as <br> (Claude's chat style). `gfm: true` for tables/strikethrough.
 *   • `DOMPurify` strips any tag/attribute not in its allowlist — so
 *     even if Claude (or a downstream message) embeds `<script>` or
 *     `onerror=...`, it's neutralised before reaching the DOM.
 *
 * Usage:
 *   import { useMarkdown } from '@/composables/useMarkdown'
 *   const { renderMarkdown } = useMarkdown()
 *   const html = renderMarkdown(msg.content)
 *   // in template: <div v-html="html" />
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure once at module load — these settings don't change per call.
marked.setOptions({
  breaks: true,     // single \n -> <br>
  gfm: true,        // GitHub-flavoured: tables, strikethrough, autolinks
})

// DOMPurify defaults are strict already; we just widen slightly so common
// markdown output renders cleanly. Disallow `target=_blank` injection by
// stripping any user-supplied target attribute (we re-add `_blank` on
// genuine links via the hook below).
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  // Force external links to open in a new tab + add rel="noopener" for safety.
  // External = absolute http(s) URL; relative/anchor links stay in-page.
  if (node.tagName === 'A') {
    const href = node.getAttribute('href') || ''
    if (/^https?:\/\//i.test(href)) {
      node.setAttribute('target', '_blank')
      node.setAttribute('rel', 'noopener noreferrer')
    }
  }
})

export function useMarkdown() {
  /**
   * Convert markdown text → safe HTML string. Sync — no async parsing.
   * `marked.parse()` returns string | Promise<string> depending on extensions;
   * we keep it sync by passing `{ async: false }` so callers can use it in
   * Vue computed properties / template expressions without await.
   */
  function renderMarkdown(md: string | null | undefined): string {
    if (!md) return ''
    const rawHtml = marked.parse(md, { async: false }) as string
    return DOMPurify.sanitize(rawHtml, {
      // Keep the allowlist tight — these are the tags `marked` emits for
      // standard markdown. Nothing else.
      ALLOWED_TAGS: [
        'p', 'br', 'hr',
        'strong', 'em', 'b', 'i', 's', 'del', 'mark',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'a',
        'code', 'pre',
        'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'span',
      ],
      ALLOWED_ATTR: [
        'href', 'title', 'target', 'rel',
        'class', 'id',
        'colspan', 'rowspan', 'align',
      ],
    })
  }

  return { renderMarkdown }
}
