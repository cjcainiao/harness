<!--聊天消息编辑器-->
<template>
  <div
    ref="hostRef"
    class="chat-composer-editor"
    :class="{
      'has-command': hasCommand,
      'is-manual': manualHeight !== null,
      'is-readonly': readonly,
    }"
    :style="hostStyle"
    @keydown.capture="emit('keydown', $event)"
  />
</template>

<script setup lang="ts">
import { history, historyKeymap } from '@codemirror/commands'
import { Compartment, EditorState } from '@codemirror/state'
import type { Range } from '@codemirror/state'
import { Decoration, EditorView, keymap, MatchDecorator, ViewPlugin } from '@codemirror/view'
import type { DecorationSet, ViewUpdate } from '@codemirror/view'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
    hasCommand?: boolean
    commandMenuOpen?: boolean
    manualHeight?: number | null
    readonly?: boolean
  }>(),
  {
    placeholder: '',
    hasCommand: false,
    commandMenuOpen: false,
    manualHeight: null,
    readonly: false,
  },
)
const emit = defineEmits<{
  'update:modelValue': [value: string]
  input: []
  keydown: [event: KeyboardEvent]
}>()

const hostRef = ref<HTMLElement | null>(null)
const accessibilityConfig = new Compartment()
let view: EditorView | null = null

// 外部同步时阻断重复回写
let applyingModelValue = false

// 提示文案交给伪元素，文档里不留可跨越的对象
const hostStyle = computed<Record<string, string>>(() => ({
  '--chat-placeholder': JSON.stringify(props.placeholder),
  ...(props.manualHeight === null ? {} : { height: `${props.manualHeight}px` }),
}))

// 链接与命令仅改变显示样式
const styledText = new MatchDecorator({
  regexp: /(?:https?:\/\/|www\.)[^\s<>"'`]+|^\/[A-Za-z][A-Za-z0-9_-]*(?=\s|$)/g,
  decorate(add, from, to, match) {
    if (match[0].startsWith('/')) {
      add(from, to, Decoration.mark({ class: 'cm-chat-command' }))
      return
    }
    const trimmed = match[0].replace(/[.,!?;:)\]\}，。！？、；：]+$/u, '')
    if (trimmed) add(from, from + trimmed.length, Decoration.mark({ class: 'cm-chat-url' }))
  },
})
const styledTextPlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet

    constructor(editor: EditorView) {
      this.decorations = styledText.createDeco(editor)
    }

    update(update: ViewUpdate): void {
      this.decorations = styledText.updateDeco(update, this.decorations)
    }
  },
  { decorations: (plugin) => plugin.decorations },
)

const markdown = new MarkdownIt({ html: false, linkify: true })

// 行首结构记号
const HEADING_MARK = /^ {0,3}#{1,6}[ \t]+/
const QUOTE_MARK = /^ {0,3}>[ \t]?/

// 行内标记，定界符长度一致，隐藏后样式只落在正文上
const inlineRules = [
  { pattern: /`[^`\n]+`/g, className: 'cm-chat-inline-code', delimiter: 1 },
  { pattern: /\*\*[^*]+\*\*|__[^_]+__/g, className: 'cm-chat-strong', delimiter: 2 },
  {
    pattern: /(?<!\*)\*[^*]+\*(?!\*)|(?<!_)_[^_]+_(?!_)/g,
    className: 'cm-chat-emphasis',
    delimiter: 1,
  },
] as const

// 按 Markdown 结构显示渲染样式，语法记号本身藏掉
function markdownDecorations(state: EditorState): DecorationSet {
  const ranges: Range<Decoration>[] = []
  const lineClasses = new Map<number, Set<string>>()
  const codeLines = new Set<number>()
  const tokens = markdown.parse(state.doc.toString(), {})

  for (const token of tokens) {
    if (!token.map) continue
    const [start, end] = token.map
    let className = ''
    if (token.type === 'heading_open') className = `cm-chat-heading-${token.tag.slice(1)}`
    else if (token.type === 'fence' || token.type === 'code_block') className = 'cm-chat-code-line'
    else if (token.type === 'blockquote_open') className = 'cm-chat-quote-line'
    if (!className) continue

    for (let index = start; index < end && index < state.doc.lines; index += 1) {
      const lineNumber = index + 1
      const classes = lineClasses.get(lineNumber) ?? new Set<string>()
      classes.add(className)
      lineClasses.set(lineNumber, classes)
      if (className === 'cm-chat-code-line') codeLines.add(lineNumber)
    }
  }

  for (const [lineNumber, classes] of lineClasses) {
    const line = state.doc.line(lineNumber)
    ranges.push(Decoration.line({ class: [...classes].join(' ') }).range(line.from))
    if (codeLines.has(lineNumber)) continue

    let offset = 0
    if (classes.has('cm-chat-quote-line')) {
      const match = QUOTE_MARK.exec(line.text)
      if (match) {
        ranges.push(Decoration.replace({}).range(line.from, line.from + match[0].length))
        offset = match[0].length
      }
    }
    if ([...classes].some((name) => name.startsWith('cm-chat-heading-'))) {
      const match = HEADING_MARK.exec(line.text.slice(offset))
      if (match) {
        const from = line.from + offset
        ranges.push(Decoration.replace({}).range(from, from + match[0].length))
      }
    }
  }

  for (let lineNumber = 1; lineNumber <= state.doc.lines; lineNumber += 1) {
    if (codeLines.has(lineNumber)) continue
    const line = state.doc.line(lineNumber)
    for (const rule of inlineRules) {
      for (const match of line.text.matchAll(rule.pattern)) {
        const start = line.from + (match.index ?? 0)
        const end = start + match[0].length
        ranges.push(
          Decoration.replace({}).range(start, start + rule.delimiter),
          Decoration.mark({ class: rule.className }).range(
            start + rule.delimiter,
            end - rule.delimiter,
          ),
          Decoration.replace({}).range(end - rule.delimiter, end),
        )
      }
    }
  }

  return Decoration.set(ranges, true)
}

const markdownPlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet

    constructor(editor: EditorView) {
      this.decorations = markdownDecorations(editor.state)
    }

    update(update: ViewUpdate): void {
      if (update.docChanged) this.decorations = markdownDecorations(update.state)
    }
  },
  { decorations: (plugin) => plugin.decorations },
)

// 空文档时给首行挂提示类
function emptyLineDeco(state: EditorState): DecorationSet {
  return state.doc.length
    ? Decoration.none
    : Decoration.set([Decoration.line({ class: 'cm-chat-empty' }).range(0)])
}

const emptyLinePlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet

    constructor(editor: EditorView) {
      this.decorations = emptyLineDeco(editor.state)
    }

    update(update: ViewUpdate): void {
      if (update.docChanged) this.decorations = emptyLineDeco(update.state)
    }
  },
  { decorations: (plugin) => plugin.decorations },
)

// 输入框无障碍属性切换
function contentAttributes(): Record<string, string> {
  if (props.readonly) return { 'aria-label': '消息内容' }
  return {
    'aria-label': '消息输入框',
    'aria-placeholder': props.placeholder,
    'aria-haspopup': 'listbox',
    'aria-expanded': String(props.commandMenuOpen),
    ...(props.commandMenuOpen ? { 'aria-controls': 'slash-command-menu' } : {}),
  }
}

onMounted(() => {
  if (!hostRef.value) return
  view = new EditorView({
    parent: hostRef.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        history(),
        keymap.of(historyKeymap),
        EditorView.lineWrapping,
        EditorView.editable.of(!props.readonly),
        emptyLinePlugin,
        accessibilityConfig.of(EditorView.contentAttributes.of(contentAttributes())),
        styledTextPlugin,
        markdownPlugin,
        EditorView.updateListener.of((update) => {
          if (!update.docChanged || applyingModelValue) return
          emit('update:modelValue', update.state.doc.toString())
          emit('input')
        }),
      ],
    }),
  })
})

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})

// 外部内容同步至编辑器
watch(
  () => props.modelValue,
  (value) => {
    if (!view || value === view.state.doc.toString()) return
    applyingModelValue = true
    try {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
    } finally {
      applyingModelValue = false
    }
  },
)

watch([() => props.placeholder, () => props.commandMenuOpen], () =>
  view?.dispatch({
    effects: accessibilityConfig.reconfigure(EditorView.contentAttributes.of(contentAttributes())),
  }),
)

function focus(): void {
  view?.focus()
}

function focusAtEnd(): void {
  if (!view) return
  view.dispatch({ selection: { anchor: view.state.doc.length }, scrollIntoView: true })
  view.focus()
}

function isCursorAtStart(): boolean {
  const selection = view?.state.selection.main
  return selection?.from === 0 && selection.to === 0
}

function getHeight(): number {
  return hostRef.value?.getBoundingClientRect().height ?? 0
}

defineExpose({ focus, focusAtEnd, isCursorAtStart, getHeight })
</script>

<style scoped>
.chat-composer-editor {
  flex: 1;
  min-width: 0;
  width: 100%;
  /* lucide globe，描边几何提供遮罩透明度 */
  --chat-link-icon: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cpath d='M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20'/%3E%3Cpath d='M2 12h20'/%3E%3C/svg%3E");
}
.chat-composer-editor :deep(.cm-editor) {
  min-height: 56px;
  max-height: 200px;
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: inherit;
  line-height: 22px;
}
.chat-composer-editor.is-manual :deep(.cm-editor) {
  height: 100%;
  max-height: none;
}
/* 只读展示：内边距交给外层气泡，不出内部滚动 */
.chat-composer-editor.is-readonly :deep(.cm-editor) {
  min-height: 0;
  max-height: none;
}
.chat-composer-editor.is-readonly :deep(.cm-scroller) {
  overflow: visible;
}
.chat-composer-editor.is-readonly :deep(.cm-content) {
  min-height: 0;
  padding: 0;
}
.chat-composer-editor :deep(.cm-editor.cm-focused) {
  outline: none;
}
.chat-composer-editor :deep(.cm-scroller) {
  overflow: auto;
  font-family: inherit;
  scrollbar-width: thin;
}
.chat-composer-editor :deep(.cm-content) {
  box-sizing: border-box;
  min-height: 56px;
  padding: 12px 14px 4px;
  caret-color: #303133;
}
.chat-composer-editor.has-command :deep(.cm-content) {
  padding-left: 8px;
}
.chat-composer-editor :deep(.cm-line) {
  padding: 0;
}
/* 空行提示文字，脱离行内流，不占光标位置 */
.chat-composer-editor :deep(.cm-chat-empty) {
  position: relative;
}
.chat-composer-editor :deep(.cm-chat-empty)::before {
  content: var(--chat-placeholder, '');
  position: absolute;
  top: 0;
  left: 0;
  color: #9ca3af;
  pointer-events: none;
}
.chat-composer-editor :deep(.cm-chat-url) {
  color: #2858a4;
}
/* 链接前的地球图标，取色跟随文字颜色 */
.chat-composer-editor :deep(.cm-chat-url)::before {
  content: '';
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 5px;
  vertical-align: -3px;
  background-color: currentColor;
  -webkit-mask: var(--chat-link-icon) no-repeat center / contain;
  mask: var(--chat-link-icon) no-repeat center / contain;
}
.chat-composer-editor :deep(.cm-chat-command) {
  color: #2858a4;
}
.chat-composer-editor :deep(.cm-chat-heading-1) {
  font-size: 18px;
  font-weight: 600;
  line-height: 28px;
}
.chat-composer-editor :deep(.cm-chat-heading-2) {
  font-size: 16px;
  font-weight: 600;
  line-height: 26px;
}
.chat-composer-editor :deep(.cm-chat-heading-3),
.chat-composer-editor :deep(.cm-chat-heading-4),
.chat-composer-editor :deep(.cm-chat-heading-5),
.chat-composer-editor :deep(.cm-chat-heading-6) {
  font-weight: 600;
}
.chat-composer-editor :deep(.cm-chat-code-line) {
  padding: 0 6px;
  background: #f4f6f9;
  color: #374151;
  font-family: ui-monospace, Consolas, monospace;
}
.chat-composer-editor :deep(.cm-chat-quote-line) {
  padding-left: 8px;
  border-left: 2px solid #cbd5e1;
  color: #64748b;
}
.chat-composer-editor :deep(.cm-chat-inline-code) {
  border-radius: 3px;
  background: #f1f3f5;
  color: #a3405f;
  font-family: ui-monospace, Consolas, monospace;
}
.chat-composer-editor :deep(.cm-chat-strong) {
  font-weight: 600;
}
.chat-composer-editor :deep(.cm-chat-emphasis) {
  font-style: italic;
}
@media (hover: none) {
  .chat-composer-editor :deep(.cm-editor) {
    font-size: 16px;
  }
}
</style>
