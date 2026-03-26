import { ref, type Ref } from 'vue'

export const A4_PAGE_HEIGHT = 1061  // px – A4 at 96 DPI
export const PAGE_GAP = 16         // px – gap between pages
export const PAGE_PAD_TOP = 24     // px – top padding on each new page

export function usePageBreaks(
  containerEl: Ref<HTMLElement | null>,
  options?: {
    footerLeft?: Ref<string>
    onUpdate?: () => void
  },
) {
  const pageCount = ref(1)
  let _updating = false
  let _rafId: number | null = null

  function schedule() {
    if (_rafId) cancelAnimationFrame(_rafId)
    _rafId = requestAnimationFrame(update)
  }

  function update() {
    _rafId = null
    const el = containerEl.value
    if (!el || _updating) return
    _updating = true

    // 1. Remove existing auto breaks
    el.querySelectorAll('[data-auto-page-break]').forEach(n => n.remove())

    // 2. Measure children
    const children = Array.from(el.children) as HTMLElement[]
    if (children.length === 0) { _updating = false; return }

    const padTop = parseFloat(getComputedStyle(el).paddingTop) || 0

    // 3. Find page-break insertion points
    const breaks: { idx: number; spacer: number }[] = []
    let used = padTop

    for (let i = 0; i < children.length; i++) {
      const child = children[i]
      if (child.hasAttribute('data-page-break')) {
        used = padTop
        continue
      }
      const h = child.offsetHeight
      if (h === 0) continue
      const cs = getComputedStyle(child)
      const mt = parseFloat(cs.marginTop) || 0
      const mb = parseFloat(cs.marginBottom) || 0
      const total = h + mt + mb

      // Don't break if this is the first real content on the page
      if (used <= padTop + 60) {
        used += total
        while (used > A4_PAGE_HEIGHT) used -= (A4_PAGE_HEIGHT - padTop)
        if (used < padTop) used = padTop
        continue
      }

      if (used + total > A4_PAGE_HEIGHT) {
        const remaining = Math.max(0, A4_PAGE_HEIGHT - used)
        breaks.push({ idx: i, spacer: remaining + PAGE_GAP + PAGE_PAD_TOP })
        used = padTop + total
        while (used > A4_PAGE_HEIGHT) used -= (A4_PAGE_HEIGHT - padTop)
        if (used < padTop) used = padTop
      } else {
        used += total
      }
    }

    // 4. Insert spacer divs (reverse order keeps indices valid)
    const totalPages = breaks.length + 1
    const footerText = options?.footerLeft?.value || ''
    for (let b = breaks.length - 1; b >= 0; b--) {
      const { idx, spacer } = breaks[b]
      const pageNum = b + 1
      const child = children[idx]
      const div = document.createElement('div')
      div.setAttribute('data-auto-page-break', 'true')
      div.setAttribute('contenteditable', 'false')
      div.style.height = `${spacer}px`
      div.innerHTML = `<span class="apb-left">${footerText}</span><span class="apb-right">Page ${pageNum} of ${totalPages}</span>`
      child.parentNode!.insertBefore(div, child)
    }

    pageCount.value = totalPages
    _updating = false
    options?.onUpdate?.()
  }

  function isUpdating() {
    return _updating
  }

  function destroy() {
    if (_rafId) cancelAnimationFrame(_rafId)
  }

  return { pageCount, schedule, update, isUpdating, destroy }
}
