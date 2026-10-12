<!--回复正文消息-->
<template>
  <div
    ref="messageRoot"
    class="message-chunk"
    v-html="renderedHtml"
    @click="onCodeClick"
    @keydown="onDiagramKeydown"
  />
  <Teleport to="body">
    <dialog
      v-if="dialogVisible"
      ref="diagramDialog"
      class="mermaid-dialog"
      aria-label="流程图大图"
      @close="onDialogClose"
    >
      <div class="mermaid-dialog-head">
        <div class="mermaid-dialog-title">
          <span class="mermaid-dialog-title-icon"><Workflow :size="17" :stroke-width="1.8" /></span>
          <span>流程图</span>
        </div>
        <div class="mermaid-dialog-actions">
          <div class="mermaid-zoom-controls" role="group" aria-label="流程图缩放控制">
            <button
              type="button"
              class="mermaid-tool-button"
              aria-label="缩小流程图"
              title="缩小"
              @click="zoomDiagram(1 / 1.2)"
            >
              <Minus :size="16" :stroke-width="1.8" />
            </button>
            <span class="mermaid-zoom-value" aria-live="off">{{ diagramZoomPercent }}%</span>
            <button
              type="button"
              class="mermaid-tool-button"
              aria-label="放大流程图"
              title="放大"
              @click="zoomDiagram(1.2)"
            >
              <Plus :size="16" :stroke-width="1.8" />
            </button>
            <span class="mermaid-tool-divider" aria-hidden="true" />
            <button
              type="button"
              class="mermaid-tool-button"
              aria-label="适应画布"
              title="适应画布"
              @click="resetDiagramView"
            >
              <Scan :size="16" :stroke-width="1.8" />
            </button>
          </div>
          <button
            type="button"
            class="mermaid-dialog-close"
            aria-label="关闭大图"
            title="关闭"
            @click="closeDialog"
          >
            <X :size="18" :stroke-width="1.8" />
          </button>
        </div>
      </div>
      <div
        ref="diagramViewport"
        class="mermaid-dialog-body"
        :class="{ 'is-dragging': isDiagramDragging }"
        aria-label="流程图画布：拖动平移，滚轮或双指缩放"
        @wheel.prevent="onDiagramWheel"
        @pointerdown="onDiagramPointerDown"
        @pointermove="onDiagramPointerMove"
        @pointerup="onDiagramPointerEnd"
        @pointercancel="onDiagramPointerEnd"
        @lostpointercapture="onDiagramPointerEnd"
      >
        <div ref="fullscreenDiagram" class="mermaid-fullscreen-diagram" />
      </div>
    </dialog>
  </Teleport>
</template>

<script setup lang="ts">
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github.css'
import MarkdownIt from 'markdown-it'
import type { RendererRule } from 'markdown-it'
import { ElMessage } from 'element-plus'
import { Minus, Plus, Scan, Workflow, X } from 'lucide-vue-next'
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { createUuid } from '@/utils/uuidUtil'
import CodeRunView from '@/views/chat/pages/CodeRunView.vue'
import { copyToClipboard } from '@/utils/clipboardUtil'
import { createMermaidPng } from './mermaidPng'
import { loadMermaid } from './mermaidRenderer'

const props = withDefaults(defineProps<{ content: string; streaming?: boolean }>(), {
  streaming: false,
})

type OpenDrawer = (page: Component, title: string, pageProps?: Record<string, unknown>) => void
const openDrawer = inject<OpenDrawer | null>('chat-drawer-open', null)

const iconAttrs =
  'viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
const iconCopy = `<svg class="icon-copy" ${iconAttrs}><rect x="8" y="8" width="14" height="14" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`
const iconCheck = `<svg class="icon-check" ${iconAttrs}><path d="M20 6 9 17l-5-5"/></svg>`
const iconUp = `<svg class="icon-up" ${iconAttrs}><path d="m18 15-6-6-6 6"/></svg>`
const iconDown = `<svg class="icon-down" ${iconAttrs}><path d="m6 9 6 6 6-6"/></svg>`
const iconRun = `<svg class="icon-run" ${iconAttrs}><polygon points="5 3 19 12 5 21 5 3"/></svg>`
const iconExport = `<svg class="icon-export" ${iconAttrs}><path d="M12 3v12m-5-5 5 5 5-5"/><path d="M4 17v3h16v-3"/></svg>`

// 代码块折叠状态
const collapsedFences = new Set<number>()

// 图表渲染与全屏状态
const messageRoot = ref<HTMLElement | null>(null)
const dialogVisible = ref(false)
const diagramDialog = ref<HTMLDialogElement | null>(null)
const diagramViewport = ref<HTMLElement | null>(null)
const fullscreenDiagram = ref<HTMLElement | null>(null)
const diagramZoomPercent = ref(100)
const isDiagramDragging = ref(false)
const diagramPointers = new Map<number, { x: number; y: number }>()
let fenceCursor = 0
let renderGeneration = 0
let diagramObserver: IntersectionObserver | null = null
let thumbnailObserver: ResizeObserver | null = null
let thumbnailFrame: number | null = null
const pendingThumbnails = new Set<HTMLElement>()
let renderQueue: Promise<void> = Promise.resolve()
let fullscreenGeneration = 0
let activeDiagram: HTMLElement | null = null
let activeSvg: SVGSVGElement | null = null
let activeSvgStyle: string | null = null

// 全屏平移缩放状态
let diagramWidth = 0
let diagramHeight = 0
let diagramFitZoom = 1
let diagramZoom = 1
let diagramX = 0
let diagramY = 0
let diagramFrame: number | null = null
let diagramViewportRect: DOMRect | null = null

// 未知语言默认转义
function highlightCode(code: string, lang: string): string {
  if (!lang || !hljs.getLanguage(lang)) return ''
  return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
}

// 消息正文 HTML 禁用
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: highlightCode,
})

// 代码框头部操作
const defaultFence = markdown.renderer.rules.fence as RendererRule
markdown.renderer.rules.fence = (tokens, idx, options, env, renderer) => {
  const index = fenceCursor++
  const lang = tokens[idx]?.info.trim().split(/\s+/)[0] ?? ''
  const isMermaid = lang.toLowerCase() === 'mermaid'
  const collapsed = collapsedFences.has(index)
  const toggleTip = collapsed ? '展开代码' : '收起代码'
  return [
    `<div class="code-block${collapsed ? ' is-collapsed' : ''}" data-fence="${index}">`,
    '<div class="code-head">',
    `<span class="code-lang">${markdown.utils.escapeHtml(lang || '代码')}</span>`,
    `<button type="button" class="code-toggle" data-action="toggle" aria-expanded="${!collapsed}" aria-label="${toggleTip}" data-tip="${toggleTip}">${iconUp}${iconDown}</button>`,
    isMermaid
      ? `<button type="button" class="code-export" data-action="export-png" aria-label="导出 PNG" data-tip="流程图渲染中" disabled>${iconExport}</button>`
      : '',
    `<button type="button" class="code-copy" data-action="copy" aria-label="复制代码" data-tip="复制代码">${iconCopy}${iconCheck}</button>`,
    isMermaid
      ? ''
      : `<button type="button" class="code-run" data-action="run" aria-label="运行代码" data-tip="运行代码">${iconRun}</button>`,
    '</div>',
    defaultFence(tokens, idx, options, env, renderer),
    isMermaid && !props.streaming
      ? '<div class="mermaid-diagram" role="button" tabindex="0" aria-label="全屏查看流程图"></div>'
      : '',
    '</div>',
  ].join('')
}

const renderedHtml = computed(() => {
  fenceCursor = 0
  return markdown.render(props.content)
})

// 窄屏宽图预览
function updateMermaidThumbnail(diagram: HTMLElement): void {
  const svg = diagram.querySelector<SVGSVGElement>('svg')
  const viewBox = svg?.viewBox.baseVal
  if (!viewBox?.width || !viewBox.height) return
  const styles = window.getComputedStyle(diagram)
  const availableWidth =
    diagram.clientWidth - parseFloat(styles.paddingLeft) - parseFloat(styles.paddingRight)
  const isWide = window.innerWidth <= 600 && (availableWidth * viewBox.height) / viewBox.width < 70
  diagram.classList.toggle('is-wide', isWide)
  const hint = diagram.querySelector<HTMLElement>('.mermaid-expand-hint')
  if (hint) hint.textContent = isWide ? '左右滑动 · 点击查看大图' : '点击查看大图'
}

// 合并尺寸变更
function queueThumbnailUpdate(diagram: HTMLElement): void {
  pendingThumbnails.add(diagram)
  if (thumbnailFrame !== null) return
  thumbnailFrame = window.requestAnimationFrame(() => {
    thumbnailFrame = null
    for (const pending of pendingThumbnails) updateMermaidThumbnail(pending)
    pendingThumbnails.clear()
  })
}

// 流式预加载 Mermaid
watch(
  () => [props.content, props.streaming] as const,
  ([content, streaming]) => {
    if (streaming && /(?:^|\n) {0,3}(?:`{3,}|~{3,})[ \t]*mermaid\b/i.test(content)) {
      void loadMermaid().catch(() => undefined)
    }
  },
  { immediate: true },
)

async function renderMermaidBlock(block: HTMLElement, generation: number): Promise<void> {
  const root = messageRoot.value
  const diagram = block.querySelector<HTMLElement>('.mermaid-diagram')
  const source = block.querySelector('code')?.textContent ?? ''
  if (!root || !diagram || !source.trim() || generation !== renderGeneration) return

  try {
    const mermaid = await loadMermaid()
    if (generation !== renderGeneration || !root.contains(diagram)) return

    const { svg, bindFunctions } = await mermaid.render(`mermaid-${createUuid()}`, source)
    if (generation !== renderGeneration || !root.contains(diagram)) return
    diagram.innerHTML = svg
    bindFunctions?.(diagram)
    const hint = document.createElement('span')
    hint.className = 'mermaid-expand-hint'
    hint.textContent = '点击查看大图'
    diagram.append(hint)
    block.classList.add('has-mermaid')
    updateMermaidThumbnail(diagram)
    thumbnailObserver?.observe(diagram)
    const exportButton = block.querySelector<HTMLButtonElement>('.code-export')
    if (exportButton) {
      exportButton.disabled = false
      exportButton.dataset.tip = '导出 PNG'
    }
  } catch {
    // 渲染失败时保留原始代码块
  }
}

// 图表顺序渲染队列
function queueMermaidBlock(block: HTMLElement, generation: number): void {
  renderQueue = renderQueue.then(() => renderMermaidBlock(block, generation)).catch(() => undefined)
}

// 可见图表观察器
function renderMermaidBlocks(): void {
  const generation = ++renderGeneration
  diagramObserver?.disconnect()
  diagramObserver = null
  thumbnailObserver?.disconnect()
  thumbnailObserver = null
  if (thumbnailFrame !== null) window.cancelAnimationFrame(thumbnailFrame)
  thumbnailFrame = null
  pendingThumbnails.clear()
  const root = messageRoot.value
  const diagrams = root?.querySelectorAll<HTMLElement>('.mermaid-diagram')
  if (!root || !diagrams?.length) return
  if (typeof ResizeObserver !== 'undefined') {
    thumbnailObserver = new ResizeObserver((entries) => {
      for (const entry of entries) queueThumbnailUpdate(entry.target as HTMLElement)
    })
  }
  const blocks = Array.from(diagrams, (diagram) =>
    diagram.closest<HTMLElement>('.code-block'),
  ).filter((block): block is HTMLElement => block !== null)

  if (typeof IntersectionObserver === 'undefined') {
    blocks.forEach((block) => queueMermaidBlock(block, generation))
    return
  }

  // 视野附近延迟渲染
  const scrollRoot = root.closest<HTMLElement>('.delegation-body, .message-scroll')
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        observer.unobserve(entry.target)
        queueMermaidBlock(entry.target as HTMLElement, generation)
      }
    },
    { root: scrollRoot, rootMargin: '500px 0px' },
  )
  diagramObserver = observer
  blocks.forEach((block) => observer.observe(block))
}

onMounted(renderMermaidBlocks)
watch(
  renderedHtml,
  () => {
    if (activeDiagram && !messageRoot.value?.contains(activeDiagram)) closeDialog()
    renderMermaidBlocks()
  },
  { flush: 'post' },
)
onUnmounted(() => {
  diagramObserver?.disconnect()
  thumbnailObserver?.disconnect()
  if (thumbnailFrame !== null) window.cancelAnimationFrame(thumbnailFrame)
  pendingThumbnails.clear()
  window.removeEventListener('resize', resetDiagramView)
  if (diagramFrame !== null) window.cancelAnimationFrame(diagramFrame)
  renderGeneration++
  fullscreenGeneration++
})

// 代码区操作分发
function onCodeClick(event: MouseEvent): void {
  const diagram = (event.target as Element).closest<HTMLElement>('.mermaid-diagram')
  if (diagram && messageRoot.value?.contains(diagram)) {
    void openDiagram(diagram)
    return
  }

  const button = (event.target as Element).closest<HTMLElement>('[data-action]')
  const block = button?.closest<HTMLElement>('.code-block')
  if (!button || !block) return
  if (button.dataset.action === 'export-png') {
    void exportDiagramPng(block, button as HTMLButtonElement)
    return
  }
  if (button.dataset.action === 'copy') {
    void copyCode(block.querySelector('code')?.textContent ?? '', button)
    return
  }
  if (button.dataset.action === 'run') {
    const code = block.querySelector('code')?.textContent ?? ''
    openDrawer?.(CodeRunView, '运行代码', { code })
    return
  }
  const index = Number(block.dataset.fence)
  const collapsed = block.classList.toggle('is-collapsed')
  if (collapsed) collapsedFences.add(index)
  else collapsedFences.delete(index)
  const toggleTip = collapsed ? '展开代码' : '收起代码'
  button.setAttribute('aria-expanded', String(!collapsed))
  button.setAttribute('aria-label', toggleTip)
  button.dataset.tip = toggleTip
}

function onDiagramKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const diagram = (event.target as Element).closest<HTMLElement>('.mermaid-diagram')
  if (!diagram || !messageRoot.value?.contains(diagram)) return
  event.preventDefault()
  void openDiagram(diagram)
}

// 复用 SVG 展示大图
async function openDiagram(diagram: HTMLElement): Promise<void> {
  const svg = diagram.querySelector<SVGSVGElement>('svg')
  if (!svg) return

  const generation = ++fullscreenGeneration
  dialogVisible.value = true
  await nextTick()
  const dialog = diagramDialog.value
  const target = fullscreenDiagram.value
  if (generation !== fullscreenGeneration || !dialog || !target || !diagram.isConnected) return

  activeDiagram = diagram
  activeSvg = svg
  activeSvgStyle = svg.getAttribute('style')
  if (!dialog.open) dialog.showModal()
  target.append(svg)
  diagramWidth = svg.viewBox.baseVal.width || svg.getBoundingClientRect().width
  diagramHeight = svg.viewBox.baseVal.height || svg.getBoundingClientRect().height
  svg.style.maxWidth = 'none'
  svg.style.width = `${diagramWidth}px`
  svg.style.height = `${diagramHeight}px`
  target.style.width = `${diagramWidth}px`
  target.style.height = `${diagramHeight}px`
  resetDiagramView()
  window.addEventListener('resize', resetDiagramView)
}

// 每帧合并平移缩放更新
function applyDiagramView(): void {
  if (diagramFrame !== null) return
  diagramFrame = window.requestAnimationFrame(() => {
    diagramFrame = null
    const target = fullscreenDiagram.value
    if (!target || !activeSvg) return
    target.style.transform = `translate3d(${diagramX}px, ${diagramY}px, 0) scale(${diagramZoom})`
    const percent = Math.round(diagramZoom * 100)
    if (diagramZoomPercent.value !== percent) diagramZoomPercent.value = percent
  })
}

// 适应全屏画布
function resetDiagramView(): void {
  const viewport = diagramViewport.value
  if (!viewport || !diagramWidth || !diagramHeight) return
  diagramViewportRect = viewport.getBoundingClientRect()
  diagramFitZoom = Math.min(
    1,
    (viewport.clientWidth - 48) / diagramWidth,
    (viewport.clientHeight - 48) / diagramHeight,
  )
  diagramZoom = Math.max(0.001, diagramFitZoom)
  diagramX = (viewport.clientWidth - diagramWidth * diagramZoom) / 2
  diagramY = (viewport.clientHeight - diagramHeight * diagramZoom) / 2
  applyDiagramView()
}

// 围绕指定点缩放
function zoomDiagramAt(factor: number, x: number, y: number): void {
  if (!activeSvg) return
  const nextZoom = Math.min(4, Math.max(Math.min(0.1, diagramFitZoom), diagramZoom * factor))
  const ratio = nextZoom / diagramZoom
  diagramX = x - (x - diagramX) * ratio
  diagramY = y - (y - diagramY) * ratio
  diagramZoom = nextZoom
  applyDiagramView()
}

function zoomDiagram(factor: number): void {
  const viewport = diagramViewport.value
  if (!viewport) return
  zoomDiagramAt(factor, viewport.clientWidth / 2, viewport.clientHeight / 2)
}

function onDiagramWheel(event: WheelEvent): void {
  const viewport = diagramViewport.value
  if (!viewport) return
  const bounds = diagramViewportRect ?? viewport.getBoundingClientRect()
  const factor = Math.min(1.25, Math.max(0.8, Math.exp(-event.deltaY * 0.0015)))
  zoomDiagramAt(factor, event.clientX - bounds.left, event.clientY - bounds.top)
}

function onDiagramPointerDown(event: PointerEvent): void {
  const viewport = diagramViewport.value
  if (!viewport || (event.pointerType === 'mouse' && event.button !== 0)) return
  event.preventDefault()
  viewport.setPointerCapture(event.pointerId)
  const bounds = diagramViewportRect ?? viewport.getBoundingClientRect()
  diagramPointers.set(event.pointerId, {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  })
  isDiagramDragging.value = true
}

// 单指平移与双指缩放
function onDiagramPointerMove(event: PointerEvent): void {
  if (!diagramPointers.has(event.pointerId)) return
  const viewport = diagramViewport.value
  if (!viewport) return
  const before = [...diagramPointers.values()]
  const bounds = diagramViewportRect ?? viewport.getBoundingClientRect()
  diagramPointers.set(event.pointerId, {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  })
  const after = [...diagramPointers.values()]
  if (after.length === 1) {
    diagramX += after[0]!.x - before[0]!.x
    diagramY += after[0]!.y - before[0]!.y
  } else if (after.length >= 2) {
    const oldMidX = (before[0]!.x + before[1]!.x) / 2
    const oldMidY = (before[0]!.y + before[1]!.y) / 2
    const newMidX = (after[0]!.x + after[1]!.x) / 2
    const newMidY = (after[0]!.y + after[1]!.y) / 2
    const oldDistance = Math.hypot(before[0]!.x - before[1]!.x, before[0]!.y - before[1]!.y)
    const newDistance = Math.hypot(after[0]!.x - after[1]!.x, after[0]!.y - after[1]!.y)
    const nextZoom = oldDistance
      ? Math.min(
          4,
          Math.max(Math.min(0.1, diagramFitZoom), (diagramZoom * newDistance) / oldDistance),
        )
      : diagramZoom
    const ratio = nextZoom / diagramZoom
    diagramX = newMidX - (oldMidX - diagramX) * ratio
    diagramY = newMidY - (oldMidY - diagramY) * ratio
    diagramZoom = nextZoom
  }
  applyDiagramView()
}

function onDiagramPointerEnd(event: PointerEvent): void {
  diagramPointers.delete(event.pointerId)
  const viewport = diagramViewport.value
  if (viewport?.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId)
  isDiagramDragging.value = diagramPointers.size > 0
}

function closeDialog(): void {
  diagramDialog.value?.close()
}

// SVG 归位与交互清理
function onDialogClose(): void {
  fullscreenGeneration++
  window.removeEventListener('resize', resetDiagramView)
  if (diagramFrame !== null) window.cancelAnimationFrame(diagramFrame)
  diagramFrame = null
  diagramViewportRect = null
  diagramPointers.clear()
  isDiagramDragging.value = false
  if (activeSvg && activeDiagram?.isConnected) {
    if (activeSvgStyle === null) activeSvg.removeAttribute('style')
    else activeSvg.setAttribute('style', activeSvgStyle)
    activeDiagram.prepend(activeSvg)
  }
  activeDiagram = null
  activeSvg = null
  activeSvgStyle = null
  fullscreenDiagram.value?.replaceChildren()
  dialogVisible.value = false
}

async function copyCode(code: string, button: HTMLElement): Promise<void> {
  if (!(await copyToClipboard(code))) return
  button.classList.add('is-copied')
  button.dataset.tip = '已复制'
  window.setTimeout(() => {
    button.classList.remove('is-copied')
    button.dataset.tip = '复制代码'
  }, 1600)
}

// 流程图 PNG 下载
async function exportDiagramPng(block: HTMLElement, button: HTMLButtonElement): Promise<void> {
  const svg = block.querySelector<SVGSVGElement>('.mermaid-diagram svg')
  if (!svg || button.disabled) return
  button.disabled = true
  button.dataset.tip = '导出中…'
  try {
    const png = await createMermaidPng(svg)
    const url = URL.createObjectURL(png)
    const link = document.createElement('a')
    link.href = url
    link.download = `流程图-${Date.now()}.png`
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    console.error('流程图导出 PNG 失败', error)
    ElMessage.error({ message: '导出 PNG 失败', plain: true })
  } finally {
    button.disabled = false
    button.dataset.tip = '导出 PNG'
  }
}
</script>

<style scoped>
.message-chunk {
  min-width: 0;
  color: #292d32;
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.message-chunk :deep(p),
.message-chunk :deep(ul),
.message-chunk :deep(ol),
.message-chunk :deep(blockquote),
.message-chunk :deep(pre),
.message-chunk :deep(table) {
  margin: 0 0 1em;
}
.message-chunk :deep(> :last-child) {
  margin-bottom: 0;
}
.message-chunk :deep(h1),
.message-chunk :deep(h2),
.message-chunk :deep(h3),
.message-chunk :deep(h4),
.message-chunk :deep(h5),
.message-chunk :deep(h6) {
  margin: 1.25em 0 0.55em;
  color: #202327;
  font-weight: 600;
  line-height: 1.4;
}
.message-chunk :deep(h1) {
  font-size: 1.45em;
}
.message-chunk :deep(h2) {
  font-size: 1.3em;
}
.message-chunk :deep(h3) {
  font-size: 1.15em;
}
.message-chunk :deep(h4),
.message-chunk :deep(h5),
.message-chunk :deep(h6) {
  font-size: 1em;
}
.message-chunk :deep(ul),
.message-chunk :deep(ol) {
  padding-left: 1.6em;
}
.message-chunk :deep(ul) {
  list-style: disc;
}
.message-chunk :deep(ol) {
  list-style: decimal;
}
.message-chunk :deep(li + li) {
  margin-top: 0.35em;
}
.message-chunk :deep(li > ul),
.message-chunk :deep(li > ol) {
  margin-top: 0.35em;
  margin-bottom: 0;
}
.message-chunk :deep(a) {
  color: #3369aa;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.message-chunk :deep(a:focus-visible) {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
@media (hover: hover) {
  .message-chunk :deep(a:hover) {
    color: #1e4d87;
  }
}
.message-chunk :deep(blockquote) {
  padding: 2px 0 2px 12px;
  border-left: 3px solid #d6dce4;
  color: #65707b;
}
.message-chunk :deep(code) {
  padding: 0.15em 0.35em;
  border-radius: 4px;
  background: #f1f3f5;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 0.9em;
}
.message-chunk :deep(pre) {
  max-width: 100%;
  padding: 12px 14px;
  overflow-x: auto;
  border: 1px solid #e9ebee;
  border-radius: 8px;
  background: #f7f8fa;
}
.message-chunk :deep(pre code) {
  padding: 0;
  background: transparent;
  font-size: 13px;
  line-height: 1.55;
}
.message-chunk :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}
.message-chunk :deep(th),
.message-chunk :deep(td) {
  padding: 7px 10px;
  border: 1px solid #e1e5e9;
  text-align: left;
}
.message-chunk :deep(th) {
  background: #f7f8fa;
  font-weight: 600;
}
.message-chunk :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}
.message-chunk :deep(hr) {
  margin: 1.2em 0;
  border: 0;
  border-top: 1px solid #e8e9eb;
}
/* 代码框容器样式 */
.message-chunk :deep(.code-block) {
  margin: 0 0 1em;
  border: 1px solid #e6e9ec;
  background: #fbfcfd;
}
.message-chunk :deep(.code-block:last-child) {
  margin-bottom: 0;
}
.message-chunk :deep(.code-block pre) {
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
.message-chunk :deep(.code-block.is-collapsed pre) {
  display: none;
}
.message-chunk :deep(.mermaid-diagram) {
  display: none;
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 300px;
  padding: 12px 14px;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  background-image: radial-gradient(circle, #dcdfe6 1.2px, transparent 1.2px);
  background-size: 14px 14px;
  cursor: zoom-in;
}
.message-chunk :deep(.code-block.has-mermaid pre),
.message-chunk :deep(.code-block.is-collapsed .mermaid-diagram) {
  display: none;
}
.message-chunk :deep(.code-block.has-mermaid:not(.is-collapsed) .mermaid-diagram) {
  display: flex;
}
.message-chunk :deep(.mermaid-diagram svg) {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: 100%;
  height: 100%;
}
@media (max-width: 600px) {
  .message-chunk :deep(.mermaid-diagram.is-wide) {
    justify-content: flex-start;
    overflow-x: auto;
  }
  .message-chunk :deep(.mermaid-diagram.is-wide svg) {
    flex: none;
    width: auto;
    height: 150px;
    min-width: 100%;
    max-width: none;
  }
}
.message-chunk :deep(.mermaid-expand-hint) {
  position: absolute;
  right: 10px;
  bottom: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgb(32 35 39 / 70%);
  color: #fff;
  font-size: 12px;
  line-height: 18px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}
.message-chunk :deep(.mermaid-diagram:focus-visible) {
  outline: 2px solid #8b9fc7;
  outline-offset: -3px;
}
.message-chunk :deep(.mermaid-diagram:focus-visible .mermaid-expand-hint) {
  opacity: 1;
}
@media (hover: hover) {
  .message-chunk :deep(.mermaid-diagram:hover .mermaid-expand-hint) {
    opacity: 1;
  }
}
@media (hover: none) {
  .message-chunk :deep(.mermaid-expand-hint) {
    opacity: 1;
  }
}
.mermaid-dialog {
  position: fixed;
  inset: 0;
  box-sizing: border-box;
  width: 100vw;
  max-width: 100vw;
  height: 100vh;
  max-height: 100vh;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  padding: 0;
  border: 0;
  background: #fff;
  color: #292d32;
}
.mermaid-dialog::backdrop {
  background: rgb(20 25 30 / 65%);
}
.mermaid-dialog-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
  height: 56px;
  padding: 0 18px;
  border-bottom: 1px solid #eceef2;
  background: #fff;
  box-shadow: 0 1px 8px rgb(35 39 47 / 4%);
}
.mermaid-dialog-title {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #29313d;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}
.mermaid-dialog-title-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: #f1ecff;
  color: #7c5acb;
}
.mermaid-dialog-actions,
.mermaid-zoom-controls {
  display: flex;
  align-items: center;
}
.mermaid-dialog-actions {
  gap: 10px;
}
.mermaid-zoom-controls {
  gap: 2px;
  padding: 3px;
  border: 1px solid #e7e9ef;
  border-radius: 11px;
  background: #f8f9fc;
}
.mermaid-tool-button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #657082;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}
.mermaid-zoom-value {
  min-width: 48px;
  color: #3d4654;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.mermaid-tool-divider {
  width: 1px;
  height: 18px;
  margin: 0 3px;
  background: #e1e4eb;
}
.mermaid-tool-button:focus-visible,
.mermaid-dialog-close:focus-visible {
  outline: 2px solid #a78bfa;
  outline-offset: 1px;
}
@media (hover: hover) {
  .mermaid-tool-button:hover,
  .mermaid-dialog-close:hover {
    background: #eee9fc;
    color: #7654c7;
  }
  .mermaid-dialog-close:hover {
    border-color: #d8cdf6;
  }
}
.mermaid-dialog-close {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid #e7e9ef;
  border-radius: 10px;
  background: #fff;
  color: #657082;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}
.mermaid-dialog-body {
  position: relative;
  box-sizing: border-box;
  height: calc(100% - 56px);
  overflow: hidden;
  background-color: #fff;
  background-image: radial-gradient(circle, #dcdfe6 1.2px, transparent 1.2px);
  background-size: 14px 14px;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.mermaid-dialog-body.is-dragging {
  cursor: grabbing;
}
.mermaid-fullscreen-diagram {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  will-change: transform;
}
.mermaid-fullscreen-diagram :deep(svg) {
  display: block;
  max-width: none;
}
@media (any-pointer: coarse) {
  .mermaid-tool-button {
    width: 40px;
    height: 40px;
  }
  .mermaid-dialog-close {
    width: 40px;
    height: 40px;
  }
}
@media (max-width: 600px) {
  .mermaid-dialog-head {
    padding: 0 12px;
  }
  .mermaid-dialog-actions {
    gap: 8px;
  }
  .mermaid-zoom-value {
    min-width: 40px;
  }
}
@media (max-width: 360px) {
  .mermaid-dialog-title > span:last-child {
    display: none;
  }
}
.message-chunk :deep(.code-block.is-collapsed .code-head) {
  border-bottom-color: transparent;
}
.message-chunk :deep(.code-head) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px 6px 14px;
  border-bottom: 1px solid #e6e9ec;
  background: #f2f4f7;
}
.message-chunk :deep(.code-lang) {
  color: #24292f;
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
}
.message-chunk :deep(.code-toggle),
.message-chunk :deep(.code-export),
.message-chunk :deep(.code-copy),
.message-chunk :deep(.code-run) {
  position: relative;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: none;
  color: #8b929a;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}
.message-chunk :deep(.code-copy) {
  margin-left: auto;
}
.message-chunk :deep(.code-export) {
  margin-left: auto;
}
.message-chunk :deep(.code-export + .code-copy) {
  margin-left: 0;
}
.message-chunk :deep(.code-export:disabled) {
  cursor: not-allowed;
  opacity: 0.55;
}
@media (any-pointer: coarse) {
  .message-chunk :deep(.code-toggle),
  .message-chunk :deep(.code-export),
  .message-chunk :deep(.code-copy),
  .message-chunk :deep(.code-run) {
    width: 40px;
    height: 40px;
  }
}
@media (hover: hover) {
  .message-chunk :deep(.code-toggle:hover),
  .message-chunk :deep(.code-export:not(:disabled):hover),
  .message-chunk :deep(.code-copy:hover),
  .message-chunk :deep(.code-run:hover) {
    background: #e6eaf0;
    color: #24292f;
  }
}
.message-chunk :deep(.code-toggle:focus-visible),
.message-chunk :deep(.code-export:focus-visible),
.message-chunk :deep(.code-copy:focus-visible),
.message-chunk :deep(.code-run:focus-visible) {
  outline: 2px solid #8b9fc7;
  outline-offset: 1px;
}
/* 代码按钮提示气泡 */
.message-chunk :deep([data-tip])::before,
.message-chunk :deep([data-tip])::after {
  position: absolute;
  z-index: 3;
  content: '';
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}
.message-chunk :deep([data-tip])::after {
  top: calc(100% + 6px);
  left: 50%;
  padding: 5px 11px;
  border: 1px solid var(--el-text-color-primary, #303133);
  border-radius: 4px;
  background: var(--el-text-color-primary, #303133);
  color: var(--el-bg-color, #fff);
  content: attr(data-tip);
  font-size: 12px;
  font-weight: 400;
  line-height: 20px;
  transform: translateX(-50%);
  white-space: nowrap;
}
.message-chunk :deep([data-tip])::before {
  top: calc(100% + 2px);
  left: 50%;
  width: 8px;
  height: 8px;
  background: var(--el-text-color-primary, #303133);
  transform: translateX(-50%) rotate(45deg);
}
/* 最右侧气泡对齐 */
.message-chunk :deep(.code-run)::after {
  left: auto;
  right: -1px;
  transform: none;
}
.message-chunk :deep(.code-run)::before {
  left: auto;
  right: 8px;
  transform: rotate(45deg);
}
.message-chunk :deep([data-tip]:focus-visible)::before,
.message-chunk :deep([data-tip]:focus-visible)::after {
  opacity: 1;
  transition-delay: 0.35s;
}
@media (hover: hover) {
  .message-chunk :deep([data-tip]:hover)::before,
  .message-chunk :deep([data-tip]:hover)::after {
    opacity: 1;
    transition-delay: 0.35s;
  }
}
.message-chunk :deep(.code-block.is-collapsed .icon-up),
.message-chunk :deep(.code-block:not(.is-collapsed) .icon-down),
.message-chunk :deep(.code-copy:not(.is-copied) .icon-check),
.message-chunk :deep(.code-copy.is-copied .icon-copy) {
  display: none;
}
@media (prefers-reduced-motion: reduce) {
  .mermaid-tool-button,
  .mermaid-dialog-close,
  .message-chunk :deep(.mermaid-expand-hint),
  .message-chunk :deep(.code-toggle),
  .message-chunk :deep(.code-export),
  .message-chunk :deep(.code-copy),
  .message-chunk :deep(.code-run) {
    transition: none;
  }
}
</style>
