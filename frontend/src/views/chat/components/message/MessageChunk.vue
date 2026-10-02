<template>
  <div class="message-chunk" v-html="renderedHtml" @click="onCodeClick" />
</template>

<script setup lang="ts">
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github.css'
import MarkdownIt from 'markdown-it'
import type { RendererRule } from 'markdown-it'
import { computed, inject, ref } from 'vue'
import type { Component } from 'vue'
import CodeRunView from '@/views/chat/pages/CodeRunView.vue'

const props = defineProps<{ content: string }>()

// 打开抽屉的方法
type OpenDrawer = (page: Component, title: string, pageProps?: Record<string, unknown>) => void
const openDrawer = inject<OpenDrawer | null>('chat-drawer-open', null)

const iconAttrs =
  'viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'
const iconCopy = `<svg class="icon-copy" ${iconAttrs}><rect x="8" y="8" width="14" height="14" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`
const iconCheck = `<svg class="icon-check" ${iconAttrs}><path d="M20 6 9 17l-5-5"/></svg>`
const iconUp = `<svg class="icon-up" ${iconAttrs}><path d="m18 15-6-6-6 6"/></svg>`
const iconDown = `<svg class="icon-down" ${iconAttrs}><path d="m6 9 6 6 6-6"/></svg>`
const iconRun = `<svg class="icon-run" ${iconAttrs}><polygon points="5 3 19 12 5 21 5 3"/></svg>`

// 折叠状态按围栏序号记录，重渲染后仍保持
const collapsedFences = ref<number[]>([])
let fenceCursor = 0

// 未知语言返回空串，交回 markdown-it 默认转义
function highlightCode(code: string, lang: string): string {
  if (!lang || !hljs.getLanguage(lang)) return ''
  return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
}

// 正文来自消息事件，禁用原始 HTML，避免将其作为页面元素插入
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: highlightCode,
})

// 代码框头部：语言名 + 折叠 + 复制 + 运行
const defaultFence = markdown.renderer.rules.fence as RendererRule
markdown.renderer.rules.fence = (tokens, idx, options, env, renderer) => {
  const index = fenceCursor++
  const lang = tokens[idx]?.info.trim().split(/\s+/)[0] ?? ''
  const collapsed = (env?.collapsed as number[] | undefined)?.includes(index) ?? false
  const toggleTip = collapsed ? '展开代码' : '收起代码'
  return [
    `<div class="code-block${collapsed ? ' is-collapsed' : ''}" data-fence="${index}">`,
    '<div class="code-head">',
    `<span class="code-lang">${markdown.utils.escapeHtml(lang || '代码')}</span>`,
    `<button type="button" class="code-toggle" data-action="toggle" aria-expanded="${!collapsed}" aria-label="${toggleTip}" data-tip="${toggleTip}">${iconUp}${iconDown}</button>`,
    `<button type="button" class="code-copy" data-action="copy" aria-label="复制代码" data-tip="复制代码">${iconCopy}${iconCheck}</button>`,
    `<button type="button" class="code-run" data-action="run" aria-label="运行代码" data-tip="运行代码">${iconRun}</button>`,
    '</div>',
    defaultFence(tokens, idx, options, env, renderer),
    '</div>',
  ].join('')
}

const renderedHtml = computed(() => {
  fenceCursor = 0
  return markdown.render(props.content, { collapsed: collapsedFences.value })
})

function onCodeClick(event: MouseEvent): void {
  const button = (event.target as Element).closest<HTMLElement>('[data-action]')
  const block = button?.closest<HTMLElement>('.code-block')
  if (!button || !block) return
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
  collapsedFences.value = collapsedFences.value.includes(index)
    ? collapsedFences.value.filter((item) => item !== index)
    : [...collapsedFences.value, index]
}

async function copyCode(code: string, button: HTMLElement): Promise<void> {
  try {
    await navigator.clipboard.writeText(code)
  } catch {
    return
  }
  button.classList.add('is-copied')
  button.dataset.tip = '已复制'
  window.setTimeout(() => {
    button.classList.remove('is-copied')
    button.dataset.tip = '复制代码'
  }, 1600)
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
/* 代码框：外框接管边框和底色，pre 只留内边距 */
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
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}
.message-chunk :deep(.code-copy) {
  margin-left: auto;
}
.message-chunk :deep(.code-toggle:hover),
.message-chunk :deep(.code-copy:hover),
.message-chunk :deep(.code-run:hover) {
  background: #e6eaf0;
  color: #24292f;
}
.message-chunk :deep(.code-toggle:focus-visible),
.message-chunk :deep(.code-copy:focus-visible),
.message-chunk :deep(.code-run:focus-visible) {
  outline: 2px solid #8b9fc7;
  outline-offset: 1px;
}
/* 悬停气泡：对齐 ElTooltip 深色主题的配色、内距、字号和 350ms 延迟 */
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
/* 最右侧按钮气泡靠右，避免超出代码框 */
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
.message-chunk :deep([data-tip]:hover)::before,
.message-chunk :deep([data-tip]:hover)::after,
.message-chunk :deep([data-tip]:focus-visible)::before,
.message-chunk :deep([data-tip]:focus-visible)::after {
  opacity: 1;
  transition-delay: 0.35s;
}
.message-chunk :deep(.code-block.is-collapsed .icon-up),
.message-chunk :deep(.code-block:not(.is-collapsed) .icon-down),
.message-chunk :deep(.code-copy:not(.is-copied) .icon-check),
.message-chunk :deep(.code-copy.is-copied .icon-copy) {
  display: none;
}
@media (prefers-reduced-motion: reduce) {
  .message-chunk :deep(.code-toggle),
  .message-chunk :deep(.code-copy),
  .message-chunk :deep(.code-run) {
    transition: none;
  }
}
</style>
