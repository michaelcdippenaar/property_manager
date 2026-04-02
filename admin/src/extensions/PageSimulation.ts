/**
 * PageSimulation — TipTap extension that renders Google Docs-style page breaks.
 *
 * Reflow-based approach:
 * 1. Detects block elements that straddle page boundaries
 * 2. Pushes them to the next page via margin-top (content reflows naturally)
 * 3. Renders visual gap overlays in the created empty space
 *
 * No content is ever hidden — gaps only cover space we deliberately created.
 */
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'

export const A4_HEIGHT = 1061  // px — A4 at 96 DPI
const PAGE_GAP = 40            // px — visual gap between pages ("desk")

const pluginKey = new PluginKey('pageSimulation')

export const PageSimulation = Extension.create({
  name: 'pageSimulation',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: pluginKey,
        view(editorView) {
          const dom = editorView.dom
          dom.classList.add('tiptap-paged')

          // Overlay container — sibling of editor, for gap visuals
          const overlay = document.createElement('div')
          overlay.className = 'page-overlays-container'
          overlay.style.cssText = 'position:absolute;top:0;left:0;right:0;pointer-events:none;z-index:10;'

          const parent = dom.parentElement
          if (parent) {
            parent.style.position = 'relative'
            parent.appendChild(overlay)
          }

          let timerId: number | null = null

          function schedule() {
            if (timerId) clearTimeout(timerId)
            timerId = window.setTimeout(run, 60)
          }

          function run() {
            timerId = null
            const { pageCount, gapYs, totalHeight } = reflow(dom)
            dom.setAttribute('data-page-count', String(pageCount))
            dom.dispatchEvent(new CustomEvent('pagecount', { detail: pageCount }))
            render(overlay, pageCount, gapYs, totalHeight)
          }

          /**
           * Push straddling blocks away from page boundaries.
           * Returns the screen-Y positions of each gap and final page count.
           */
          function reflow(el: HTMLElement) {
            const blocks = Array.from(el.children) as HTMLElement[]

            // 1. Clear previous adjustments
            for (const b of blocks) {
              if (b.dataset.pb) {
                b.style.marginTop = b.dataset.pbOrig ?? ''
                delete b.dataset.pb
                delete b.dataset.pbOrig
              }
            }
            void el.offsetHeight // force layout after reset

            const gapYs: number[] = []
            let page = 1

            for (let safe = 0; safe < 80; safe++) {
              // Screen-Y where page `page` content ends
              const gapY = page * A4_HEIGHT + gapYs.length * PAGE_GAP

              if (gapY >= el.scrollHeight) break

              // 2. Find block that straddles this boundary
              let handled = false
              for (const b of blocks) {
                const top = b.offsetTop
                const bot = top + b.offsetHeight

                if (top < gapY && bot > gapY) {
                  // Straddles — push to next page (skip blocks taller than a page)
                  if (b.offsetHeight < A4_HEIGHT * 0.8) {
                    const push = gapY - top + PAGE_GAP
                    if (b.dataset.pbOrig === undefined) b.dataset.pbOrig = b.style.marginTop
                    const orig = parseFloat(b.dataset.pbOrig || '0') || 0
                    b.style.marginTop = (orig + push) + 'px'
                    b.dataset.pb = '1'
                    void el.offsetHeight
                  }
                  gapYs.push(gapY)
                  handled = true
                  break
                }
              }

              if (!handled) {
                // Boundary falls between blocks — insert gap space
                for (const b of blocks) {
                  if (b.offsetTop >= gapY - 1) {
                    if (b.dataset.pbOrig === undefined) b.dataset.pbOrig = b.style.marginTop
                    const orig = parseFloat(b.dataset.pbOrig || '0') || 0
                    b.style.marginTop = (orig + PAGE_GAP) + 'px'
                    b.dataset.pb = '1'
                    void el.offsetHeight
                    break
                  }
                }
                gapYs.push(gapY)
              }

              page++
            }

            const pageCount = page
            const minH = pageCount * A4_HEIGHT + gapYs.length * PAGE_GAP
            const totalHeight = Math.max(el.scrollHeight, minH)
            el.style.minHeight = totalHeight + 'px'

            return { pageCount, gapYs, totalHeight }
          }

          /** Render visual gap overlays and page numbers */
          function render(
            container: HTMLElement,
            pageCount: number,
            gapYs: number[],
            totalHeight: number,
          ) {
            container.innerHTML = ''
            container.style.height = totalHeight + 'px'

            for (let i = 0; i < gapYs.length; i++) {
              const y = gapYs[i]
              const gap = document.createElement('div')
              gap.className = 'page-sim-gap'
              gap.style.cssText = `
                position:absolute;left:-60px;right:-60px;
                top:${y}px;height:${PAGE_GAP}px;
                pointer-events:none;z-index:3;
                background:var(--page-bg,#f1f3f4);
                border-top:1px solid #c4c7c5;
                border-bottom:1px solid #c4c7c5;
                display:flex;align-items:center;justify-content:center;
              `
              const lbl = document.createElement('span')
              lbl.style.cssText = 'font-size:11px;color:#9aa0a6;font-family:Arial,Helvetica,sans-serif;'
              lbl.textContent = `${i + 1} / ${pageCount}`
              gap.appendChild(lbl)
              container.appendChild(gap)
            }

            // Last page number at the bottom
            const last = document.createElement('div')
            last.style.cssText = `
              position:absolute;left:0;right:0;
              top:${totalHeight - 30}px;height:24px;
              pointer-events:none;z-index:2;
              display:flex;align-items:center;justify-content:center;
            `
            const num = document.createElement('span')
            num.style.cssText = 'font-size:11px;color:#b0b0b0;font-family:Arial,Helvetica,sans-serif;'
            num.textContent = `${pageCount} / ${pageCount}`
            last.appendChild(num)
            container.appendChild(last)
          }

          setTimeout(schedule, 100)

          return {
            update() { schedule() },
            destroy() {
              if (timerId) clearTimeout(timerId)
              dom.classList.remove('tiptap-paged')
              overlay.remove()
            },
          }
        },
      }),
    ]
  },
})

export default PageSimulation
