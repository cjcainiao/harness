<!--对话页效果预览-->
<template>
  <div class="chat-preview">
    <!-- 左侧导航栏 -->
    <aside class="preview-sidebar">
      <header class="sidebar-top">
        <div class="sidebar-top-row">
          <div class="sidebar-logo">Harness</div>
          <span class="sidebar-collapse">
            <PanelLeftClose :size="17" :stroke-width="1.8" aria-hidden="true" />
          </span>
        </div>
        <nav class="sidebar-menu">
          <span class="menu-item"
            ><SquarePen :size="16" aria-hidden="true" /><span>新对话</span></span
          >
          <span class="menu-item"><Search :size="16" aria-hidden="true" /><span>搜索</span></span>
        </nav>
      </header>
      <div class="sidebar-history">
        <div class="history-group">
          <div class="group-label">今天</div>
          <div
            v-for="item in historyItems"
            :key="item"
            class="history-item"
            :class="{ 'is-active': item === title }"
          >
            <MessageSquare :size="14" aria-hidden="true" />
            <span class="item-title">{{ item }}</span>
          </div>
        </div>
        <p class="list-tip">没有更早的历史消息了</p>
      </div>
      <footer class="sidebar-user">
        <div class="user-info">
          <span class="user-avatar">U</span>
          <span class="user-name">用户</span>
        </div>
        <span class="menu-item menu-icon"><Settings :size="16" aria-hidden="true" /></span>
      </footer>
    </aside>
    <!-- 右侧主区 -->
    <div class="preview-main">
      <header class="session-header">
        <div class="session-identity">
          <FolderClosed class="session-icon" :size="16" :stroke-width="1.6" aria-hidden="true" />
          <span class="session-title">{{ title }}</span>
        </div>
      </header>
      <!-- 消息区 -->
      <div ref="scrollRef" class="message-scroll" @scroll="onScroll">
        <div class="message-list">
          <section v-for="turn in turns" :key="turn.id" class="chat-turn">
            <div v-if="turn.question" class="user-message">
              <div class="message-text">{{ turn.question }}</div>
            </div>
            <div class="turn-reply">
              <template v-for="item in turn.items" :key="item.key">
                <!-- 思考过程 -->
                <details
                  v-if="item.kind === 'reasoning'"
                  class="message-item reasoning"
                  :open="item.expanded"
                  @toggle="onItemToggle(item, $event)"
                >
                  <summary class="reasoning-header">
                    <span class="item-chevron">
                      <ChevronDown :size="12" aria-hidden="true" />
                    </span>
                    <span :class="{ shimmer: item.streaming }">思考过程</span>
                    <span
                      v-if="item.durationMs !== undefined || item.streaming"
                      class="item-timer"
                      :class="{ 'is-live': item.streaming }"
                    >
                      {{ timerText(item) }}
                    </span>
                  </summary>
                  <div class="reasoning-body">{{ item.text }}</div>
                </details>
                <!-- 工具调用 -->
                <details
                  v-else-if="item.kind === 'tools'"
                  class="message-item tool-group"
                  :open="item.expanded"
                  @toggle="onItemToggle(item, $event)"
                >
                  <summary class="group-header">
                    <span class="item-chevron">
                      <ChevronDown :size="12" aria-hidden="true" />
                    </span>
                    <span :class="{ shimmer: item.streaming }">
                      执行工具 {{ item.tools.length }} 次
                    </span>
                    <span
                      v-if="item.durationMs !== undefined || item.streaming"
                      class="item-timer"
                      :class="{ 'is-live': item.streaming }"
                    >
                      {{ groupTimerText(item) }}
                    </span>
                  </summary>
                  <div class="tool-timeline">
                    <div v-for="tool in item.tools" :key="tool.id" class="tool-entry-summary">
                      <CircleCheck
                        v-if="tool.status === 'success'"
                        class="status-icon success"
                        :size="13"
                        aria-hidden="true"
                      />
                      <CircleX
                        v-else-if="tool.status === 'error'"
                        class="status-icon error"
                        :size="13"
                        aria-hidden="true"
                      />
                      <LoaderCircle
                        v-else-if="tool.status === 'running'"
                        class="status-icon running"
                        :size="13"
                        aria-hidden="true"
                      />
                      <Circle v-else class="status-icon preparing" :size="13" aria-hidden="true" />
                      <span class="tool-name">{{ tool.tool }}</span>
                      <span :class="{ shimmer: tool.status === 'running' }">
                        {{ statusLabels[tool.status] }}
                      </span>
                      <span v-if="tool.output" class="tool-preview">· {{ tool.output }}</span>
                    </div>
                  </div>
                </details>
                <!-- 回复正文 -->
                <div v-else class="message-item message-chunk" v-html="item.html" />
              </template>
            </div>
          </section>
        </div>
      </div>
      <!-- 底部固定区 -->
      <footer class="preview-bottom">
        <div class="input-box">
          <div class="input-card">
            <div class="input-textarea is-placeholder">规划与编程，@ 添加上下文，/ 使用命令</div>
            <div class="input-toolbar">
              <div class="toolbar-group">
                <span class="tool-btn tool-icon-btn">
                  <Plus :size="15" :stroke-width="2.5" aria-hidden="true" />
                </span>
                <span class="permission-trigger is-full">
                  <TriangleAlert :size="14" :stroke-width="1.8" aria-hidden="true" />
                  <span>完全访问</span>
                </span>
              </div>
              <div class="toolbar-group">
                <span class="tool-btn tool-model-btn">
                  <span class="model-name">DeepSeek-V4.1-Flash</span>
                  <span class="model-effort">Max</span>
                  <ChevronDown class="model-chevron" :size="14" aria-hidden="true" />
                </span>
                <span class="send-btn is-idle">
                  <ArrowUp :size="15" :stroke-width="2.25" aria-hidden="true" />
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="usage-bar">
          <span class="mini-progress" aria-hidden="true">
            <span class="mini-progress-fill" :style="{ width: `${usagePercent}%` }" />
          </span>
          <span class="mini-percent">{{ usagePercent }}%</span>
          <span class="usage-divider" aria-hidden="true" />
          <span class="token-total">{{ tokenTotal }} tokens</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ArrowUp,
  ChevronDown,
  Circle,
  CircleCheck,
  CircleX,
  FolderClosed,
  LoaderCircle,
  MessageSquare,
  PanelLeftClose,
  Plus,
  Search,
  Settings,
  SquarePen,
  TriangleAlert,
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { nextTick, onMounted, onUnmounted, reactive, ref, useTemplateRef, watch } from 'vue'

/* 测试数据 */
interface PreviewStep {
  kind: 'reasoning' | 'content' | 'tool'
  text?: string
  tool?: string
  output?: string
}

interface PreviewTurn {
  question: string
  steps: PreviewStep[]
}

interface PreviewTool {
  id: number
  tool: string
  status: 'preparing' | 'running' | 'success' | 'error'
  output?: string
  durationMs?: number
}

interface PreviewItem {
  key: number
  kind: 'reasoning' | 'content' | 'tools'
  expanded: boolean
  streaming: boolean
  startedAt: number
  durationMs?: number
  text: string
  html: string
  tools: PreviewTool[]
}

interface PreviewSession {
  id: number
  question: string
  items: PreviewItem[]
}

const props = withDefaults(
  defineProps<{ title?: string; turns?: PreviewTurn[]; usagePercent?: number }>(),
  {
    title: '新对话',
    usagePercent: 41,
    turns: () => [
      {
        question: '用 LangChain 怎么给 Agent 加工具？',
        steps: [
          {
            kind: 'reasoning',
            text: '先看工具怎么声明：项目里用 `@tool` 装饰器，函数签名和 docstring 直接就是模型看到的说明书，不用另写一份 schema。\n再看绑定方式：`bind_tools` 把工具清单塞进请求，模型返回 `tool_calls` 才真的执行，没返回就当普通回答处理。\n最后确认执行位置：`ToolNode` 拿到参数后在本进程调函数，结果作为 `ToolMessage` 喂回去。',
          },
          { kind: 'tool', tool: 'search_docs', output: 'langchain.tools' },
          { kind: 'tool', tool: 'read_file', output: 'agents/tool_node.py' },
          { kind: 'tool', tool: 'list_dir', output: 'backend/harness/tools' },
          {
            kind: 'content',
            text: '三步就能跑起来：\n\n1. 用 `@tool` 把普通函数变成工具，docstring 是写给模型看的说明书\n2. `llm.bind_tools([...])` 绑上去，模型自己决定要不要调用\n3. 收到 `tool_calls` 就执行，结果用 `ToolMessage` 回灌，模型接着说下去\n\n```python\nfrom langchain_core.tools import tool\n\n\n@tool\ndef get_weather(city: str) -> str:\n    """查询指定城市当前天气。"""\n    return f"{city}：晴，24℃"\n\n\nllm_with_tools = llm.bind_tools([get_weather])\nmessage = llm_with_tools.invoke("北京现在天气怎么样？")\n\nfor call in message.tool_calls:\n    output = tool_map[call["name"]].invoke(call["args"])\n    print(output)\n```\n\n> 坑在 docstring：写含糊了，模型就会把参数名猜歪，工具调用失败多半出在这里。\n\n工具一多，紧接着就要面对上下文占用的问题。',
          },
        ],
      },
      {
        question: '工具一多，上下文被占满怎么办？',
        steps: [
          {
            kind: 'reasoning',
            text: '这块本项目踩过：全量注册，再做可见性减法。\n先量一下工具描述占多少 token，再决定是懒加载还是分组，别凭感觉砍。',
          },
          { kind: 'tool', tool: 'grep', output: 'tools/exposure.py' },
          { kind: 'tool', tool: 'read_file', output: 'middlewares/tool_filter.py' },
          {
            kind: 'content',
            text: '按**先测量、再裁剪**的顺序处理：\n\n- 描述控制在两三行，写清“什么时候该用它”，而不是罗列参数\n- 检索类工具先做一次包含匹配，只把命中的放进本轮可见列表\n- 超长结果落盘留路径，正文只回摘要和字段数\n\n```python\nvisible = [t for t in ALL_TOOLS if hits(query, t.description)]\n```\n\n> 减法要留痕：被摘掉的工具名和原因记进日志，否则排查“模型为什么不调它”会没线索。',
          },
        ],
      },
    ],
  },
)

/* 侧栏历史条目 */
const historyItems = [props.title, '项目整体解析', '工具懒加载方案']

/* 流式节奏 */
const reasoningCharMs = 28
const contentCharMs = 32
const contentRenderStep = 3
const itemGapMs = 560
const turnGapMs = 1200
const toolRunMs = 900
const replayGapMs = 2800

const statusLabels: Record<PreviewTool['status'], string> = {
  preparing: '准备中',
  running: '执行中',
  success: '已完成',
  error: '失败',
}

// markdown 渲染器
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })

const turns = reactive<PreviewSession[]>([])
const scrollRef = useTemplateRef<HTMLElement>('scrollRef')
const tokenTotal = ref(0)
let itemId = 0
let timer: ReturnType<typeof setTimeout> | undefined
let runToken = 0
let pinned = true

// 贴底阈值
const BOTTOM_EDGE_PX = 96

function sleep(ms: number, token: number): Promise<boolean> {
  return new Promise((resolve) => {
    timer = setTimeout(() => resolve(runToken === token), ms)
  })
}

// 响应式条目
function createItem(kind: PreviewItem['kind']): PreviewItem {
  return reactive({
    key: itemId,
    kind,
    expanded: false,
    streaming: false,
    startedAt: 0,
    text: '',
    html: '',
    tools: [] as PreviewTool[],
  })
}

function onScroll(): void {
  const element = scrollRef.value
  if (!element) return
  pinned = element.scrollHeight - element.scrollTop - element.clientHeight <= BOTTOM_EDGE_PX
}

// 贴底跟随
async function followScroll(): Promise<void> {
  if (!pinned) return
  await nextTick()
  const element = scrollRef.value
  if (element && pinned) element.scrollTop = element.scrollHeight
}

function onItemToggle(item: PreviewItem, event: Event): void {
  item.expanded = (event.target as HTMLDetailsElement).open
}

function elapsed(item: PreviewItem): number {
  return item.streaming ? Date.now() - item.startedAt : (item.durationMs ?? 0)
}

function timerText(item: PreviewItem): string {
  const seconds = (elapsed(item) / 1000).toFixed(1)
  return item.streaming ? `${seconds}s` : `耗时 ${seconds}s`
}

function groupTimerText(item: PreviewItem): string {
  const ms = elapsed(item)
  if (item.streaming) return `${(ms / 1000).toFixed(1)}s`
  return ms < 1000 ? `耗时 ${Math.round(ms)} ms` : `耗时 ${(ms / 1000).toFixed(1)}s`
}

// 逐字追加
async function streamText(item: PreviewItem, full: string, charMs: number, token: number) {
  item.streaming = true
  item.expanded = true
  item.startedAt = Date.now()
  for (let index = 1; index <= full.length; index += 1) {
    item.text = full.slice(0, index)
    if (index % contentRenderStep === 0 || index === full.length) {
      item.html = markdown.render(item.text)
      await followScroll()
    }
    if (!(await sleep(charMs, token))) return false
  }
  item.streaming = false
  item.durationMs = Date.now() - item.startedAt
  item.expanded = false
  return true
}

async function runReasoning(turn: PreviewSession, text: string, token: number) {
  const item = createItem('reasoning')
  turn.items.push(item)
  if (!(await streamText(item, text, reasoningCharMs, token))) return
  await sleep(itemGapMs, token)
}

async function runContent(turn: PreviewSession, text: string, token: number) {
  const item = createItem('content')
  turn.items.push(item)
  await streamText(item, text, contentCharMs, token)
}

async function runTools(turn: PreviewSession, steps: PreviewStep[], token: number) {
  const item = createItem('tools')
  item.tools = steps.map((step, index) => ({
    id: index,
    tool: step.tool ?? '工具调用',
    status: 'preparing',
    output: step.output,
  }))
  turn.items.push(item)
  item.streaming = true
  item.expanded = true
  item.startedAt = Date.now()
  await followScroll()

  for (const tool of item.tools) {
    tool.status = 'running'
    if (!(await sleep(toolRunMs, token))) return
    tool.status = 'success'
    tool.durationMs = toolRunMs + 13 * (tool.id + 1)
    tokenTotal.value += 128 * (tool.id + 1)
    await followScroll()
  }

  item.streaming = false
  item.durationMs = Date.now() - item.startedAt
  item.expanded = false
  await sleep(itemGapMs, token)
}

/* 一轮完整播放 */
async function playRound(token: number): Promise<void> {
  turns.splice(
    0,
    turns.length,
    ...props.turns.map(() => ({ id: ++itemId, question: '', items: [] as PreviewItem[] })),
  )
  pinned = true
  tokenTotal.value = 0
  await followScroll()

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  for (const [turnIndex, source] of props.turns.entries()) {
    const turn = turns[turnIndex]!
    // 本轮用户消息上屏
    turn.question = source.question
    for (let index = 0; index < source.steps.length; index += 1) {
      const step = source.steps[index]!
      if (step.kind === 'tool') {
        const group = [step]
        while (source.steps[index + 1]?.kind === 'tool') group.push(source.steps[++index]!)
        if (reduced) {
          const tools = group.map((item, id) => ({
            id,
            tool: item.tool ?? '工具调用',
            status: 'success' as const,
            output: item.output,
            durationMs: toolRunMs,
          }))
          turn.items.push({
            ...createItem('tools'),
            tools,
            durationMs: toolRunMs * group.length,
          })
          tools.forEach((tool) => {
            tokenTotal.value += 128 * (tool.id + 1)
          })
          continue
        }
        await runTools(turn, group, token)
        continue
      }
      if (reduced) {
        const text = step.text ?? ''
        const charMs = step.kind === 'reasoning' ? reasoningCharMs : contentCharMs
        turn.items.push({
          ...createItem(step.kind === 'reasoning' ? 'reasoning' : 'content'),
          text,
          html: markdown.render(text),
          durationMs: text.length * charMs,
        })
        continue
      }
      if (step.kind === 'reasoning') await runReasoning(turn, step.text ?? '', token)
      else await runContent(turn, step.text ?? '', token)
      if (runToken !== token) return
    }
    if (!(await sleep(turnGapMs, token))) return
  }
}

/* 循环播放 */
async function runPreview(): Promise<void> {
  const token = ++runToken
  while (runToken === token) {
    await playRound(token)
    // 降低动效时只播一次
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    if (!(await sleep(replayGapMs, token))) return
  }
}

onMounted(() => {
  void runPreview()
})

watch(
  () => props.turns,
  () => {
    void runPreview()
  },
  { deep: true },
)

onUnmounted(() => {
  runToken += 1
  clearTimeout(timer)
})
</script>

<style scoped>
/* 缩略预览容器，无尺寸断点 */
.chat-preview {
  display: flex;
  width: 100%;
  height: calc(100vh - 180px);
  min-height: 420px;
  max-height: 640px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fff;
  color: #24292f;
  font-size: 14px;
  text-align: left;
}
@supports (height: 100dvh) {
  .chat-preview {
    height: calc(100dvh - 180px);
  }
}
/* 左侧导航栏 */
.preview-sidebar {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  width: 200px;
  border-right: 1px solid #e4e7ed;
}
.sidebar-top {
  flex-shrink: 0;
}
.sidebar-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 2px 12px;
}
.sidebar-logo {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.sidebar-collapse {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: #565d64;
}
.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 8px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
}
.menu-icon {
  width: auto;
  justify-content: center;
}
.sidebar-history {
  flex: 1;
  min-height: 0;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.history-group {
  padding: 4px 0;
}
.group-label {
  padding: 6px 20px;
  color: #909399;
  font-size: 12px;
  font-weight: 500;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
}
.history-item.is-active {
  background: #e9ebee;
}
.item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.list-tip {
  margin: 0;
  padding: 10px 20px 14px;
  color: #a8adb3;
  font-size: 12px;
  text-align: center;
}
.sidebar-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 8px;
  border-top: 1px solid #e4e7ed;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 4px 8px;
}
.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 13px;
}
.user-name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* 右侧主区 */
.preview-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}
.session-header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  height: 44px;
  min-width: 0;
  padding: 0 17px 0 20px;
  border-bottom: 1px solid #e8e9eb;
  background: #fff;
}
.session-identity {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.session-icon {
  flex-shrink: 0;
  color: #565d64;
}
.session-title {
  overflow: hidden;
  color: #202327;
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 消息区 */
.message-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
}
.message-scroll::-webkit-scrollbar {
  display: none;
}
.message-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
  max-width: 980px;
  padding: 24px 16px 24px 36px;
  margin: 0 auto;
}
.chat-turn {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}
.turn-reply {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.message-item {
  min-width: 0;
  animation: item-in 0.18s ease-out;
}
@keyframes item-in {
  from {
    opacity: 0;
    transform: translateY(3px);
  }
}
.user-message {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  min-width: 0;
  color: #242629;
}
.message-text {
  max-width: min(80%, 700px);
  padding: 10px 14px;
  border-radius: 10px;
  background: #f4f4f5;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
/* 条目头 */
.reasoning,
.tool-group {
  min-width: 0;
  color: #757b80;
  font-size: 14px;
  line-height: 1.6;
}
.tool-group {
  color: #8b8b8b;
  line-height: 1.5;
}
.reasoning-header,
.group-header {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 22px;
  cursor: pointer;
  list-style: none;
}
.reasoning-header::-webkit-details-marker,
.group-header::-webkit-details-marker {
  display: none;
}
.item-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 20px;
  height: 20px;
  border: 1px solid #e4e4e4;
  border-radius: 6px;
  background: #fff;
  color: #7f8588;
}
.reasoning:not([open]) .item-chevron svg,
.tool-group:not([open]) .item-chevron svg {
  transform: rotate(-90deg);
}
.item-timer {
  flex: none;
  color: #628fbd;
  font-variant-numeric: tabular-nums;
  opacity: 0;
  transition: opacity 0.15s;
}
.item-timer.is-live {
  color: #9aa0a4;
  opacity: 1;
}
/* 进行中文案扫光 */
.shimmer {
  background-image: linear-gradient(110deg, currentcolor 0 42%, #b6bec7 50%, currentcolor 58% 100%);
  background-repeat: no-repeat;
  background-size: 250% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: text-shimmer 4s linear infinite;
}
@keyframes text-shimmer {
  0% {
    background-position: 0% 0;
  }
  100% {
    background-position: 100% 0;
  }
}
/* 思考正文 */
.reasoning-body {
  max-height: 260px;
  min-width: 0;
  margin: 4px 0 0 10px;
  padding: 2px 0 2px 16px;
  overflow-y: auto;
  border-left: 1px solid #e1e4e5;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
/* 工具条目 */
.tool-timeline {
  display: grid;
  gap: 7px;
  min-width: 0;
  margin: 4px 0 0 10px;
  padding: 2px 0 2px 16px;
  border-left: 1px solid #e1e4e5;
}
.tool-entry-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 20px;
  min-width: 0;
  white-space: nowrap;
}
.status-icon {
  flex: none;
}
.status-icon.success {
  color: #43a66d;
}
.status-icon.error {
  color: #d86464;
}
.status-icon.running {
  color: #628fbd;
  animation: spin 1.4s linear infinite;
}
.status-icon.preparing {
  color: #aeb7bd;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.tool-name {
  flex: none;
  max-width: 38%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tool-preview {
  min-width: 0;
  overflow: hidden;
  color: #aaa;
  text-overflow: ellipsis;
}
/* 回复正文 */
.message-chunk {
  color: #292d32;
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.message-chunk :deep(p) {
  margin: 0 0 0.6em;
}
.message-chunk :deep(ul),
.message-chunk :deep(ol) {
  margin: 0 0 0.7em;
  padding-left: 1.4em;
}
.message-chunk :deep(ul) {
  list-style: disc;
}
.message-chunk :deep(ol) {
  list-style: decimal;
}
.message-chunk :deep(li) {
  margin: 0.15em 0;
}
.message-chunk :deep(h1),
.message-chunk :deep(h2),
.message-chunk :deep(h3) {
  margin: 1.25em 0 0.55em;
  color: #202327;
  font-size: 1.15em;
  font-weight: 600;
  line-height: 1.4;
}
.message-chunk :deep(code) {
  padding: 0.15em 0.35em;
  border-radius: 4px;
  background: #f1f3f5;
  color: #24292f;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 0.9em;
}
.message-chunk :deep(pre) {
  margin: 0 0 0.7em;
  padding: 12px 14px;
  overflow-x: auto;
  border: 1px solid #e9ebee;
  border-radius: 8px;
  background: #f7f8fa;
}
.message-chunk :deep(pre code) {
  display: block;
  padding: 0;
  border-radius: 0;
  background: none;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre;
}
.message-chunk :deep(a) {
  color: #3369aa;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.message-chunk :deep(blockquote) {
  margin: 0 0 0.7em;
  padding-left: 12px;
  border-left: 3px solid #d6dce4;
  color: #65707b;
}
/* 底部固定区 */
.preview-bottom {
  flex-shrink: 0;
}
.input-box {
  max-width: 980px;
  padding: 0 16px;
  margin: 0 auto;
}
.input-card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.input-textarea {
  min-height: 56px;
  padding: 12px 14px 4px;
  color: #24292f;
  line-height: 22px;
}
.input-textarea.is-placeholder {
  color: #9ca3af;
}
.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 8px;
}
.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tool-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #4b5563;
  font-size: 13px;
}
.tool-icon-btn {
  border-color: transparent;
}
.tool-model-btn {
  gap: 8px;
  max-width: 260px;
  padding: 0 6px;
  border-color: transparent;
  color: #1f2328;
  font-weight: 500;
}
.model-name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.model-effort {
  flex-shrink: 0;
  color: #8b9098;
  font-weight: 400;
}
.model-chevron {
  flex-shrink: 0;
  color: #8b9098;
}
.permission-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: #f7f7f8;
  color: #555b63;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}
.permission-trigger.is-full {
  color: #ef4444;
}
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #0d0d0d;
  color: #fff;
}
.send-btn.is-idle {
  background: #e8e8e8;
  color: #b0b0b0;
}
.usage-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  max-width: 980px;
  padding: 5px 16px 8px;
  margin: 0 auto;
  color: #838280;
  font-size: 10px;
  line-height: 1;
}
.mini-progress {
  position: relative;
  display: block;
  flex: 0 0 auto;
  box-sizing: border-box;
  width: 48px;
  height: 6px;
  overflow: hidden;
  border: 1px solid #e6e6e6;
  background-image: repeating-linear-gradient(120deg, #ddd 0 1px, transparent 1px 4px);
}
.mini-progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: #4b6f5a;
  transition: width 0.3s;
}
.mini-percent {
  min-width: 22px;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.usage-divider {
  width: 1px;
  height: 10px;
  background: #e6e6e6;
}
.token-total {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
@media (hover: hover) {
  .message-chunk :deep(a:hover) {
    color: #1e4d87;
  }
  /* 悬停显示耗时 */
  .reasoning-header:hover .item-timer,
  .group-header:hover .item-timer {
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .message-item,
  .shimmer,
  .status-icon.running {
    animation: none;
  }
  .item-timer {
    transition: none;
  }
}
/* 手机档：侧栏收起 */
@media (max-width: 560px) {
  .preview-sidebar {
    display: none;
  }
  .message-list {
    padding: 20px 12px;
  }
  .input-box {
    padding: 0 12px;
  }
  .input-toolbar {
    flex-wrap: wrap;
    gap: 6px;
  }
}
</style>
