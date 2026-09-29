<template>
  <div ref="hostRef" class="code-editor" />
</template>

<script setup lang="ts">
import { indentWithTab } from '@codemirror/commands'
import { HighlightStyle, codeFolding, indentUnit, syntaxHighlighting } from '@codemirror/language'
import { Compartment, EditorState, Prec, type Extension } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { tags as t } from '@lezer/highlight'
import { basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 代码内容，双向绑定 */
    modelValue: string
    /** 语言标识，未知值按纯文本处理 */
    language?: string
    /** 只读态：流式输出时禁止编辑 */
    readonly?: boolean
  }>(),
  { language: 'python', readonly: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: string]; run: [] }>()

const hostRef = ref<HTMLElement | null>(null)
let view: EditorView | null = null
let resizeObserver: ResizeObserver | null = null

// 语言与只读态可运行时切换
const languageConf = new Compartment()
const readonlyConf = new Compartment()
// 字号独立成主题分槽，缩放时换实例才能触发重测行高
const zoomConf = new Compartment()

// 等宽字体栈，Windows 落 Consolas，macOS 落 SF Mono
const monoStack =
  "'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, 'Liberation Mono', monospace"

// 字号缩放区间
const zoomRange = { min: 11, max: 24 }
let fontSize = 13

function zoomTheme(size: number): Extension {
  return EditorView.theme({ '&': { fontSize: `${size}px` } })
}

function onWheel(event: WheelEvent): void {
  if (!event.ctrlKey || !view) return
  // 一并拦掉浏览器整页缩放与编辑器滚动
  event.preventDefault()
  const step = event.deltaY < 0 ? 1 : -1
  const next = Math.min(zoomRange.max, Math.max(zoomRange.min, fontSize + step))
  if (next === fontSize) return
  fontSize = next
  view.dispatch({ effects: zoomConf.reconfigure(zoomTheme(fontSize)) })
}

// 代码区度量用 em 跟随字号，浮层控件固定 px，配色对齐消息区代码框
const harnessTheme = EditorView.theme(
  {
    '&': {
      height: '100%',
      background: '#fbfcfd',
      color: '#24292e',
    },
    '.cm-scroller': {
      fontFamily: monoStack,
      lineHeight: '1.65',
      fontVariantLigatures: 'none',
      scrollbarWidth: 'thin',
      scrollbarColor: '#d6dbe1 transparent',
    },
    '.cm-scroller::-webkit-scrollbar': { width: '10px', height: '10px' },
    '.cm-scroller::-webkit-scrollbar-thumb': {
      background: '#d6dbe1',
      borderRadius: '5px',
      border: '3px solid transparent',
      backgroundClip: 'content-box',
    },
    '.cm-scroller::-webkit-scrollbar-track': { background: 'transparent' },
    // 原生光标由 drawSelection 强制隐藏，可见光标走 .cm-cursor
    '.cm-content': { padding: '0.92em 0' },
    '.cm-line': { padding: '0 1.08em' },
    '.cm-gutters': { background: '#fbfcfd', border: 'none', color: '#c4cad1' },
    // 基础主题用三层选择器画线号槽右边框，此处同权重覆盖
    '.cm-gutters.cm-gutters-before': { borderRight: '1px solid #f0f3f6' },
    '.cm-lineNumbers .cm-gutterElement': { padding: '0 0.77em 0 1.08em' },
    // 折叠箭头用两条边框拼成人字，不靠默认字形，两态只转角度
    '.cm-foldGutter .cm-gutterElement': {
      position: 'relative',
      padding: '0 0.45em',
    },
    // 原字形只留占位撑宽槽位，两态无类名可辨，靠 marker 的 title 区分
    '.cm-foldGutter .cm-gutterElement span': { color: 'transparent' },
    // 活动行也会拿到一个空槽位，箭头和手型只给真正带 marker 的行
    '.cm-foldGutter .cm-gutterElement:has(span)': { cursor: 'pointer' },
    '.cm-foldGutter .cm-gutterElement:has(span)::before': {
      content: '""',
      position: 'absolute',
      left: '50%',
      top: '0.83em',
      boxSizing: 'border-box',
      width: '0.44em',
      height: '0.44em',
      borderTop: '0.12em solid currentColor',
      borderRight: '0.12em solid currentColor',
      color: '#8b929a',
      opacity: '0',
      transform: 'translate(-50%, -50%) rotate(135deg)',
      transition: 'opacity 120ms, color 120ms',
    },
    '.cm-foldGutter .cm-gutterElement:has(span[title^="Unfold"])::before': {
      transform: 'translate(-50%, -50%) rotate(45deg)',
    },
    // 默认收起，鼠标进到行号区域才现出箭头
    '.cm-gutters:hover .cm-foldGutter .cm-gutterElement:has(span)::before': { opacity: '1' },
    '.cm-foldGutter .cm-gutterElement:hover::before': { color: '#202327' },
    '.cm-activeLine, .cm-activeLineGutter': { background: 'rgba(20, 24, 29, 0.032)' },
    '.cm-activeLineGutter': { color: '#5b636c' },
    '.cm-cursor, .cm-dropCursor': { borderLeft: '2px solid #3369aa', marginLeft: '-1px' },
    '.cm-selectionBackground': { background: 'rgba(51, 105, 170, 0.15)' },
    // 聚焦态基础主题选择器更深，需同样写满层级才压得住
    '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
      background: 'rgba(51, 105, 170, 0.2)',
    },
    '.cm-selectionMatch': { background: 'rgba(51, 105, 170, 0.12)' },
    '.cm-searchMatch': { background: '#ffeaa7', outline: '1px solid rgba(200, 150, 0, 0.3)' },
    '.cm-searchMatch.cm-searchMatch-selected': { background: '#ffd769' },
    '.cm-foldPlaceholder': {
      margin: '0 0.23em',
      padding: '0 0.46em',
      border: '1px solid #dfe4ea',
      borderRadius: '4px',
      background: '#eef1f5',
      color: '#6d757e',
    },
    '.cm-panels': { border: 'none', background: '#f5f7fa', color: '#202327' },
    '.cm-panels-bottom': { borderTop: '1px solid #e6e9ec' },
    '.cm-panel': { padding: '0' },
    '.cm-panel.cm-search': {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '6px 8px',
      padding: '8px 12px',
      fontSize: '12px',
    },
    '.cm-panel.cm-search br': { display: 'none' },
    '.cm-panel.cm-search input.cm-textfield': {
      boxSizing: 'border-box',
      flex: '1 1 10em',
      minWidth: '0',
      height: '24px',
      padding: '0 8px',
      border: '1px solid #dfe4ea',
      borderRadius: '4px',
      background: '#fff',
      color: '#202327',
      fontSize: '12px',
      lineHeight: '22px',
    },
    '.cm-panel.cm-search input.cm-textfield:focus': {
      border: '1px solid #3369aa',
      outline: 'none',
    },
    '.cm-panel.cm-search button': {
      boxSizing: 'border-box',
      flex: '0 0 auto',
      height: '24px',
      padding: '0 9px',
      border: '1px solid #dfe4ea',
      borderRadius: '4px',
      background: '#fff',
      color: '#4b535b',
      fontSize: '12px',
      lineHeight: '22px',
      cursor: 'pointer',
    },
    '.cm-panel.cm-search button:hover': { background: '#eef1f5', color: '#202327' },
    // 关闭按钮不带 cm-button 类，单独收成方形
    '.cm-panel.cm-search button[name="close"]': {
      width: '24px',
      padding: '0',
      border: 'none',
      background: 'none',
      color: '#8b929a',
    },
    '.cm-panel.cm-search label': {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      color: '#6d757e',
    },
    '.cm-panel.cm-search input[type="checkbox"]': { margin: '0', accentColor: '#3369aa' },
    '.cm-tooltip': {
      border: '1px solid #e6e9ec',
      borderRadius: '4px',
      background: '#fff',
      boxShadow: '0 4px 14px rgba(20, 24, 29, 0.1)',
      color: '#202327',
      fontSize: '12px',
    },
    '.cm-tooltip.cm-tooltip-autocomplete > ul': { fontFamily: monoStack, maxHeight: '168px' },
    '.cm-tooltip.cm-tooltip-autocomplete > ul > li': { padding: '3px 9px', lineHeight: '18px' },
    '.cm-tooltip.cm-tooltip-autocomplete > ul > li[aria-selected="true"]': {
      background: 'rgba(51, 105, 170, 0.1)',
      color: '#202327',
    },
    '.cm-completionDetail': { marginLeft: '8px', color: '#98a0a8', fontStyle: 'normal' },
    '.cm-completionIcon': { opacity: '0.75' },
  },
  { dark: false },
)

// 语法色沿用消息区的 github.css 取值
const githubHighlight = HighlightStyle.define([
  {
    tag: [t.comment, t.lineComment, t.blockComment, t.docComment],
    color: '#6a737d',
    fontStyle: 'italic',
  },
  { tag: [t.keyword, t.controlKeyword, t.operatorKeyword, t.definitionKeyword], color: '#d73a49' },
  { tag: [t.string, t.special(t.string), t.regexp, t.character, t.docString], color: '#032f62' },
  { tag: [t.number, t.bool, t.null, t.atom], color: '#005cc5' },
  { tag: [t.function(t.variableName), t.function(t.propertyName), t.macroName], color: '#6f42c1' },
  { tag: [t.typeName, t.className, t.namespace, t.tagName], color: '#22863a' },
  { tag: [t.propertyName, t.attributeName, t.constant(t.variableName)], color: '#005cc5' },
  {
    tag: [t.operator, t.arithmeticOperator, t.logicOperator, t.compareOperator, t.updateOperator],
    color: '#d73a49',
  },
  { tag: [t.punctuation, t.separator, t.bracket], color: '#24292e' },
  { tag: [t.meta, t.annotation], color: '#6f42c1' },
  { tag: t.invalid, color: '#b31d28' },
])

// 语言包按名动态加载，新增语言在此登记；别名共用同一加载器
const jsLoader = (typescript: boolean) => () =>
  import('@codemirror/lang-javascript').then(({ javascript }) => javascript({ typescript }))

const languageLoaders: Record<string, () => Promise<Extension>> = {
  python: () => import('@codemirror/lang-python').then(({ python }) => python()),
  javascript: jsLoader(false),
  js: jsLoader(false),
  typescript: jsLoader(true),
  ts: jsLoader(true),
  json: () => import('@codemirror/lang-json').then(({ json }) => json()),
  html: () => import('@codemirror/lang-html').then(({ html }) => html()),
  css: () => import('@codemirror/lang-css').then(({ css }) => css()),
  sql: () => import('@codemirror/lang-sql').then(({ sql }) => sql()),
  java: () => import('@codemirror/lang-java').then(({ java }) => java()),
  cpp: () => import('@codemirror/lang-cpp').then(({ cpp }) => cpp()),
  go: () => import('@codemirror/lang-go').then(({ go }) => go()),
  rust: () => import('@codemirror/lang-rust').then(({ rust }) => rust()),
}

// 分槽令牌，慢加载不能覆盖后选的语言
let languageToken = 0

async function applyLanguage(name: string): Promise<void> {
  const token = ++languageToken
  const loader = languageLoaders[name.toLowerCase()]
  // 语言块加载失败就留在纯文本，不影响编辑
  const lang = loader ? await loader().catch(() => null) : null
  if (token !== languageToken || !view) return
  view.dispatch({
    effects: languageConf.reconfigure([lang ?? [], indentUnit.of('    ')]),
  })
}

function readonlyExt(readonly: boolean): Extension {
  return readonly ? [EditorState.readOnly.of(true), EditorView.editable.of(false)] : []
}

// 被折叠掉的行数，占位符用来提示藏了多少内容
function foldedLines(state: EditorState, { from, to }: { from: number; to: number }): number {
  return state.doc.lineAt(to).number - state.doc.lineAt(from).number
}

function foldPlaceholderDOM(
  view: EditorView,
  onclick: (event: Event) => void,
  lines: number,
): HTMLElement {
  const span = document.createElement('span')
  span.className = 'cm-foldPlaceholder'
  span.setAttribute('aria-label', view.state.phrase('folded code'))
  span.title = view.state.phrase('unfold')
  span.textContent = lines > 1 ? `… ${lines} 行` : '…'
  span.addEventListener('click', onclick)
  return span
}

function createState(): EditorState {
  return EditorState.create({
    doc: props.modelValue,
    extensions: [
      basicSetup,
      // 折叠配置只是往 foldConfig 加值，foldState 同实例会被去重
      codeFolding({ preparePlaceholder: foldedLines, placeholderDOM: foldPlaceholderDOM }),
      Prec.high(
        keymap.of([
          indentWithTab,
          {
            key: 'Mod-Enter',
            preventDefault: true,
            run: () => {
              emit('run')
              return true
            },
          },
        ]),
      ),
      EditorView.lineWrapping,
      EditorState.tabSize.of(4),
      syntaxHighlighting(githubHighlight),
      languageConf.of([indentUnit.of('    ')]),
      readonlyConf.of(readonlyExt(props.readonly)),
      harnessTheme,
      zoomConf.of(zoomTheme(fontSize)),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
      }),
    ],
  })
}

onMounted(() => {
  const host = hostRef.value
  if (!host) return
  view = new EditorView({ parent: host, state: createState() })
  // 高亮按语言动态加载
  void applyLanguage(props.language)
  view.focus()
  // Ctrl+滚轮缩放字号，挂宿主才覆盖得到行号槽和面板区
  host.addEventListener('wheel', onWheel, { passive: false })
  // 抽屉拖拽变宽后重新测量
  resizeObserver = new ResizeObserver(() => view?.requestMeasure())
  resizeObserver.observe(host)
})

onBeforeUnmount(() => {
  hostRef.value?.removeEventListener('wheel', onWheel)
  resizeObserver?.disconnect()
  resizeObserver = null
  view?.destroy()
  view = null
})

// 外部整体灌入代码时替换全文档
watch(
  () => props.modelValue,
  (value) => {
    if (!view || value === view.state.doc.toString()) return
    view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
  },
)

watch(
  () => props.language,
  (value) => {
    void applyLanguage(value)
  },
)

watch(
  () => props.readonly,
  (value) => view?.dispatch({ effects: readonlyConf.reconfigure(readonlyExt(value)) }),
)
</script>

<style scoped>
.code-editor {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
</style>
