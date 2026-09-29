<template>
  <div class="message-event-handler">
    <div ref="scrollContainer" class="message-scroll">
      <div class="message-list">
        <section
          v-for="turn in displayTurns"
          :key="turn.id"
          class="chat-turn"
          :data-locator-id="turn.locatorId"
        >
          <UserMessage
            v-if="turn.question || turn.attachments?.length"
            :content="turn.question"
            :attachments="turn.attachments"
            :created-at="turn.createdAt"
            @edit="emit('edit-message', $event)"
          />
          <div class="turn-reply">
            <div v-for="item in turn.displayItems" :key="item.id" class="message-item">
              <MessageChunk v-if="item.type === 'message_chunk'" :content="item.content" />
              <ToolCallMessage v-else :tools="item.tools" />
            </div>
            <TurnActions
              v-if="turn.status === 'completed' && turn.items.length"
              :items="turn.items"
              :usage="turn.usage"
              :feedback="turn.feedback"
              @feedback="setFeedback(turn.id, $event)"
              @fork="forkTurn(turn.id)"
            />
            <div
              v-if="turn.status === 'completed' && turn.visibleFollowUps.length"
              class="follow-up-questions"
              aria-label="推荐继续提问"
            >
              <button
                v-for="(question, index) in turn.visibleFollowUps"
                :key="`${turn.id}-${index}`"
                class="follow-up-question"
                type="button"
                :disabled="isResponding"
                @click="emit('ask-follow-up', question)"
              >
                <span class="follow-up-arrow" aria-hidden="true">
                  <CornerDownRight :size="14" :stroke-width="1.8" />
                </span>
                <span class="follow-up-label">{{ question }}</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
    <MessageLocator :container="scrollContainer" :items="locatorItems" />
  </div>
</template>

<script setup lang="ts">
import { CornerDownRight } from 'lucide-vue-next'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useChatSessionsStore } from '@/stores/chatSessions'
import MessageChunk from './MessageChunk.vue'
import MessageLocator from './MessageLocator.vue'
import ToolCallMessage from './ToolCallMessage.vue'
import TurnActions from './TurnActions.vue'
import UserMessage from './UserMessage.vue'
import type {
  ChatTurn,
  MessageChunkItem,
  StreamPhase,
  ToolItem,
  TurnFeedback,
  TurnItem,
  TurnUsage,
} from './messageTurn'

const props = defineProps<{ threadId: string }>()
const emit = defineEmits<{
  'responding-change': [active: boolean]
  'phase-change': [phase: StreamPhase]
  'edit-message': [content: string]
  'fork-created': [threadId: string]
  'ask-follow-up': [question: string]
}>()
const chatSessions = useChatSessionsStore()

interface MessageEvent {
  type: string
  [key: string]: unknown
}

interface ToolGroupItem {
  id: number
  type: 'tool_group'
  tools: ToolItem[]
}

interface TurnState extends ChatTurn {
  locatorId: number
}

interface TurnRuntime {
  nextItemId: number
  activeTextItemId: number | null
  toolItemsByCallId: Map<string, number>
  toolItemsByIndex: Map<number, number>
}

const turns = ref<TurnState[]>([])
const runtimes = new Map<string, TurnRuntime>()
const demoStreams = new Map<string, number>()
const scrollContainer = ref<HTMLElement | null>(null)
let nextLocatorId = 0
const isResponding = computed(() => turns.value.some((turn) => turn.status === 'streaming'))

// 仅供前端预览的事件序列，覆盖当前所有渲染分支
const demoEvents: MessageEvent[] = [
  // 推理：当前无渲染器，验证不打断后续事件
  { type: 'reasoning_chunk', content: '先确认要演示哪些组件。' },

  // 正文块 A：连续分片合并为同一块
  {
    type: 'message_chunk',
    message_id: 'msg-a',
    content:
      '## 一、正文与 Markdown\n\n' +
      '这段文字由 **message_chunk** 事件累积，交给 `MessageChunk` 渲染，' +
      '同一块内的分片会合并成一个段落。\n\n' +
      '> 引用块：下面是自动识别的链接 https://github.com/bytedance/deer-flow\n\n',
  },
  {
    type: 'message_chunk',
    message_id: 'msg-a',
    content: '\n第二段分片继续写入同一正文块，不会新建显示项。\n',
  },

  // 用量：第一次计数，稍后与第二次累计
  {
    type: 'usage',
    usage: {
      input_tokens: 512,
      output_tokens: 96,
      total_tokens: 608,
      input_token_details: { cache_read: 256 },
    },
  },

  // 工具一：参数分片带调用 ID，正常完成
  {
    type: 'tool_call_chunk',
    tool: 'current_time',
    tool_call_id: 'call_time',
    index: 0,
    arguments: '{"time',
  },
  {
    type: 'tool_call_chunk',
    tool_call_id: 'call_time',
    index: 0,
    arguments: 'zone": "Asia/Shanghai"}',
  },
  {
    type: 'tool_start',
    tool: 'current_time',
    tool_call_id: 'call_time',
    arguments: { timezone: 'Asia/Shanghai' },
  },
  {
    type: 'tool_result',
    tool: 'current_time',
    tool_call_id: 'call_time',
    content: '{"timezone":"Asia/Shanghai","datetime":"2026-09-29T10:00:00+08:00","weekday":2}',
    duration_ms: 12,
  },

  // 工具二：首个分片只有 index 没有 ID，验证按 index 回捞；结果为失败态
  { type: 'tool_call_chunk', tool: 'read_file', index: 1, arguments: '{"path"' },
  {
    type: 'tool_call_chunk',
    tool: 'read_file',
    tool_call_id: 'call_read',
    index: 1,
    arguments: ': "/etc/hosts"}',
  },
  {
    type: 'tool_start',
    tool: 'read_file',
    tool_call_id: 'call_read',
    arguments: { path: '/etc/hosts' },
  },
  {
    type: 'tool_error',
    tool: 'read_file',
    tool_call_id: 'call_read',
    content: '文件不存在：/etc/hosts',
    duration_ms: 3,
  },

  // 工具三：无参数分片，结果无内容（Command 型返回值）
  {
    type: 'tool_start',
    tool: 'dispatch_task',
    tool_call_id: 'call_task',
    arguments: { target: 'subagent' },
  },
  { type: 'tool_result', tool: 'dispatch_task', tool_call_id: 'call_task', duration_ms: 480 },

  // 正文块 B：工具之后的正文，独立成块
  {
    type: 'message_chunk',
    message_id: 'msg-b',
    content:
      '### 二、列表 / 代码 / 表格\n\n' +
      '- 呼吸点加载动画\n- 推荐提问\n  - 嵌套列表项\n\n' +
      '1. 有序列表\n2. 带 ~~删除线~~ 的项\n\n' +
      '```python\n' +
      'async def stream():\n' +
      '    yield {"type": "message_chunk", "content": "..."}\n' +
      '```\n\n',
  },
  {
    type: 'message_chunk',
    message_id: 'msg-b',
    content:
      '\n| 组件 | 触发事件 |\n| --- | --- |\n' +
      '| MessageChunk | message_chunk |\n| ToolCallMessage | tool_start / tool_result / tool_error |\n' +
      '| TurnActions | usage |\n| 推荐提问 | done 前写入 |\n\n---\n\n' +
      '以上是本轮最后一段正文，用量为两次 usage 的累计值。\n',
  },

  // 用量：与第一次累加
  { type: 'usage', usage: { input_tokens: 320, output_tokens: 148, total_tokens: 468 } },

  // 自定义事件：当前仅占位
  { type: 'custom', event: 'demo', message: '自定义事件不改变渲染' },
]
const demoFollowUpQuestions = [
  '能再详细解释一下吗？',
  '可以给我一个具体示例吗？',
  '接下来该怎么做？',
]
// 单个分片的推送间隔
const demoTickMs = 40
// 正文分片长度，接近真实 token 节奏
const demoSliceSize = 8

// 长正文拆成小分片，避免整块文字一次跳出
function sliceDemoEvent(event: MessageEvent): MessageEvent[] {
  const content = event.content
  const isTextEvent = event.type === 'message_chunk' || event.type === 'reasoning_chunk'
  if (!isTextEvent || typeof content !== 'string') return [event]

  const parts: MessageEvent[] = []
  for (let offset = 0; offset < content.length; offset += demoSliceSize) {
    parts.push({ ...event, content: content.slice(offset, offset + demoSliceSize) })
  }
  return parts
}
const demoScript = demoEvents.flatMap(sliceDemoEvent)

// 按当前 turn 状态同步输入框的回复提示
function notifyResponding(): void {
  emit('responding-change', isResponding.value)
  chatSessions.setResponding(props.threadId, isResponding.value)
}

// 输入区提示用的当前流式阶段
const streamPhase = computed<StreamPhase>(() => {
  const active = [...turns.value].reverse().find((turn) => turn.status === 'streaming')
  if (!active) return 'idle'

  const last = active.items[active.items.length - 1]
  if (last?.type === 'tool' && (last.status === 'preparing' || last.status === 'running'))
    return 'tool'
  return active.items.length ? 'streaming' : 'waiting'
})
watch(streamPhase, (phase) => emit('phase-change', phase), { immediate: true })

// 只合并相邻工具，正文块保持原有顺序
function groupItems(renderItems: TurnItem[]): Array<MessageChunkItem | ToolGroupItem> {
  const items: Array<MessageChunkItem | ToolGroupItem> = []

  for (const item of renderItems) {
    if (item.type === 'message_chunk') {
      items.push(item)
      continue
    }

    const lastItem = items[items.length - 1]
    if (lastItem?.type === 'tool_group') {
      lastItem.tools.push(item)
    } else {
      items.push({ id: item.id, type: 'tool_group', tools: [item] })
    }
  }

  return items
}

const displayTurns = computed(() =>
  turns.value.map((turn) => ({
    ...turn,
    displayItems: groupItems(turn.items),
    visibleFollowUps:
      turn.followUpQuestions?.map((question) => question.trim()).filter(Boolean) ?? [],
  })),
)
const locatorItems = computed(() =>
  turns.value.map((turn) => ({
    id: turn.locatorId,
    label:
      turn.question.replace(/\s+/g, ' ').slice(0, 32) ||
      turn.attachments
        ?.map((file) => file.name)
        .join('、')
        .slice(0, 32) ||
      '消息',
  })),
)

// 反馈仅记录在当前 turn，切换会话时仍可恢复
function setFeedback(turnId: string, feedback: TurnFeedback | undefined): void {
  const turn = turns.value.find((item) => item.id === turnId)
  if (!turn) return
  turn.feedback = feedback
  chatSessions.saveTurns(turn.threadId, turns.value)
}

// 将选中轮次及之前的对话复制到新窗口
function forkTurn(turnId: string): void {
  const index = turns.value.findIndex((turn) => turn.id === turnId)
  if (index < 0) return
  const newThreadId = chatSessions.createSession()
  const sourceTitle = chatSessions.sessions.find((session) => session.id === props.threadId)?.title
  chatSessions.ensureSession(newThreadId).title = `${sourceTitle || '新对话'}（分支）`.slice(0, 40)
  const history: ChatTurn[] = turns.value.slice(0, index + 1).map((turn) => ({
    id: crypto.randomUUID(),
    threadId: newThreadId,
    question: turn.question,
    createdAt: turn.createdAt,
    attachments: turn.attachments,
    status: turn.status,
    items: turn.items,
    usage: turn.usage,
    feedback: turn.feedback,
    followUpQuestions: turn.followUpQuestions,
  }))
  chatSessions.saveTurns(newThreadId, history)
  emit('fork-created', newThreadId)
}

// 重建工具调用索引，供后续事件按 ID 更新
function createRuntime(items: TurnItem[] = []): TurnRuntime {
  return {
    nextItemId: items.reduce((nextId, item) => Math.max(nextId, item.id + 1), 0),
    activeTextItemId: null,
    toolItemsByCallId: new Map(
      items.flatMap((item) =>
        item.type === 'tool' && item.toolCallId ? [[item.toolCallId, item.id] as const] : [],
      ),
    ),
    toolItemsByIndex: new Map(),
  }
}

// 切换窗口或加载历史时，替换当前窗口的所有 turn
function loadTurns(history: ChatTurn[]): void {
  turns.value = history
    .filter((turn) => turn.threadId === props.threadId)
    .map((turn) => ({
      ...turn,
      attachments: turn.attachments?.map((file) => ({ ...file })),
      items: turn.items.map((item) => ({ ...item })),
      usage: turn.usage && { ...turn.usage },
      followUpQuestions: turn.followUpQuestions?.slice(),
      locatorId: nextLocatorId++,
    }))
  runtimes.clear()
  for (const turn of turns.value) runtimes.set(turn.id, createRuntime(turn.items))
  notifyResponding()
}

// 每次发送问题先创建一个 turn，后续事件只写入这个 turn
function startTurn(question: string, options: { id?: string; files?: File[] } = {}): string {
  const turnId = options.id ?? crypto.randomUUID()
  if (turns.value.some((turn) => turn.id === turnId)) throw new Error('turn_id 已存在')
  const attachments = options.files?.map((file) => {
    const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    return {
      id: crypto.randomUUID(),
      name: file.name,
      type: file.type,
      size: file.size,
      previewUrl,
    }
  })
  turns.value.push({
    id: turnId,
    threadId: props.threadId,
    question,
    createdAt: Date.now(),
    attachments,
    status: 'streaming',
    items: [],
    locatorId: nextLocatorId++,
  })
  runtimes.set(turnId, createRuntime())
  notifyResponding()
  void nextTick(() => {
    const container = scrollContainer.value
    if (container) container.scrollTop = container.scrollHeight
  })
  return turnId
}

// 本轮有推荐问题时才写入，完成后展示在回复操作区下方
function setFollowUpQuestions(turnId: string, questions: string[]): boolean {
  const turn = turns.value.find((item) => item.id === turnId)
  if (!turn) return false
  turn.followUpQuestions = questions
    .map((question) => question.trim())
    .filter(Boolean)
    .slice(0, 3)
  if (turn.status !== 'streaming') chatSessions.saveTurns(turn.threadId, turns.value)
  return true
}

// 切换 thread 前保存当前 turn，再加载目标历史
watch(
  () => props.threadId,
  (nextId, previousId) => {
    if (previousId) {
      // 先清掉上一个会话的回复状态
      chatSessions.setResponding(previousId, false)
      stopDemoStreams()
      chatSessions.saveTurns(previousId, turns.value)
    }
    loadTurns(chatSessions.getTurns(nextId))
  },
  { immediate: true },
)

function isMessageEvent(value: unknown): value is MessageEvent {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    'type' in value &&
    typeof value.type === 'string'
  )
}

// 结束当前正文块，下一段文字会新建显示项
function closeMessageChunk(runtime: TurnRuntime): void {
  runtime.activeTextItemId = null
}

// 只合并同一正文块内的连续文字片段
function handleMessageChunk(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  if (typeof event.content !== 'string' || event.content.length === 0) return

  const messageId = typeof event.message_id === 'string' ? event.message_id : undefined
  const activeItem = turn.items.find((item) => item.id === runtime.activeTextItemId)
  if (activeItem?.type === 'message_chunk' && (!messageId || activeItem.messageId === messageId)) {
    activeItem.content += event.content
    return
  }

  const id = runtime.nextItemId++
  turn.items.push({
    id,
    type: 'message_chunk',
    content: event.content,
    messageId,
  })
  runtime.activeTextItemId = id
}

// 同一工具用调用 ID 定位；参数分片没有 ID 时用 index 定位
function getToolItem(
  turn: TurnState,
  runtime: TurnRuntime,
  event: MessageEvent,
): ToolItem | undefined {
  const callId = typeof event.tool_call_id === 'string' ? event.tool_call_id : undefined
  const index = typeof event.index === 'number' ? event.index : undefined
  if (callId === undefined && index === undefined) return undefined

  let itemId = callId === undefined ? undefined : runtime.toolItemsByCallId.get(callId)
  if (itemId === undefined && index !== undefined) {
    const indexedId = runtime.toolItemsByIndex.get(index)
    const indexedItem = turn.items.find((item) => item.id === indexedId)
    if (
      indexedItem?.type === 'tool' &&
      (callId === undefined ||
        indexedItem.toolCallId === undefined ||
        indexedItem.toolCallId === callId)
    ) {
      itemId = indexedId
    }
  }

  let item = turn.items.find((entry) => entry.id === itemId)
  if (item?.type !== 'tool') {
    item = {
      id: runtime.nextItemId++,
      type: 'tool',
      tool: '',
      status: 'preparing',
    }
    turn.items.push(item)
  }

  if (callId !== undefined) {
    item.toolCallId = callId
    runtime.toolItemsByCallId.set(callId, item.id)
  }
  if (index !== undefined) runtime.toolItemsByIndex.set(index, item.id)
  if (typeof event.tool === 'string') item.tool = event.tool
  return item
}

function handleToolCallChunk(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  const item = getToolItem(turn, runtime, event)
  if (!item || typeof event.arguments !== 'string') return
  item.arguments = `${typeof item.arguments === 'string' ? item.arguments : ''}${event.arguments}`
}

function handleToolStart(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  const item = getToolItem(turn, runtime, event)
  if (!item) return
  item.status = 'running'
  if (event.arguments !== undefined) item.arguments = event.arguments
}

function handleToolResult(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  const item = getToolItem(turn, runtime, event)
  if (!item) return
  item.status = 'success'
  if (event.content !== undefined) item.output = event.content
  if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
}

function handleToolError(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  const item = getToolItem(turn, runtime, event)
  if (!item) return
  item.status = 'error'
  item.output = event.content ?? event.message
  if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
}

// 推理与自定义事件暂留扩展入口
function handleReasoningChunk(_event: MessageEvent): void {}
// 忽略无效 Token 计数，避免累计值出错
function readTokenCount(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null
}

// 每次模型响应后清空工具索引，并累计本轮用量
function handleUsage(turn: TurnState, runtime: TurnRuntime, event: MessageEvent): void {
  runtime.toolItemsByIndex.clear()
  const usage = event.usage
  if (typeof usage !== 'object' || usage === null || Array.isArray(usage)) return

  const counts = usage as Record<string, unknown>
  const input = readTokenCount(counts.input_tokens)
  const output = readTokenCount(counts.output_tokens)
  const total = readTokenCount(counts.total_tokens)
  const inputDetails = counts.input_token_details
  const cacheRead =
    typeof inputDetails === 'object' && inputDetails !== null && !Array.isArray(inputDetails)
      ? readTokenCount((inputDetails as Record<string, unknown>).cache_read)
      : null
  if (input === null && output === null && total === null && cacheRead === null) return

  const previous: TurnUsage = turn.usage ?? { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  turn.usage = {
    inputTokens: previous.inputTokens + (input ?? 0),
    outputTokens: previous.outputTokens + (output ?? 0),
    totalTokens: previous.totalTokens + (total ?? (input ?? 0) + (output ?? 0)),
    cacheReadTokens:
      cacheRead === null && previous.cacheReadTokens === undefined
        ? undefined
        : (previous.cacheReadTokens ?? 0) + (cacheRead ?? 0),
  }
  chatSessions.saveTurns(turn.threadId, turns.value)
}
// 结束状态写回历史，避免重开窗口后持续显示加载中
function handleDone(turn: TurnState): void {
  turn.status = 'completed'
  chatSessions.saveTurns(turn.threadId, turns.value)
  notifyResponding()
}
function handleError(turn: TurnState, _event: MessageEvent): void {
  turn.status = 'failed'
  chatSessions.saveTurns(turn.threadId, turns.value)
  notifyResponding()
}
function handleCustom(_event: MessageEvent): void {}

// SSE 回调传入创建时拿到的 turnId，避免交错的请求串到别的对话
function handleEvent(value: unknown, turnId: string): boolean {
  if (!isMessageEvent(value)) return false
  const turn = turns.value.find((item) => item.id === turnId)
  const runtime = turn && runtimes.get(turn.id)
  if (!turn || !runtime || turn.status !== 'streaming') return false
  const container = scrollContainer.value
  const followLatest =
    container !== null &&
    container.scrollHeight - container.scrollTop - container.clientHeight <= 96

  switch (value.type) {
    case 'message_chunk':
      handleMessageChunk(turn, runtime, value)
      break
    case 'reasoning_chunk':
      closeMessageChunk(runtime)
      handleReasoningChunk(value)
      break
    case 'tool_call_chunk':
      closeMessageChunk(runtime)
      handleToolCallChunk(turn, runtime, value)
      break
    case 'tool_start':
      closeMessageChunk(runtime)
      handleToolStart(turn, runtime, value)
      break
    case 'tool_result':
      closeMessageChunk(runtime)
      handleToolResult(turn, runtime, value)
      break
    case 'tool_error':
      closeMessageChunk(runtime)
      handleToolError(turn, runtime, value)
      break
    case 'usage':
      handleUsage(turn, runtime, value)
      break
    case 'done':
      closeMessageChunk(runtime)
      handleDone(turn)
      break
    case 'error':
      closeMessageChunk(runtime)
      handleError(turn, value)
      break
    case 'custom':
      handleCustom(value)
      break
    default:
      return false
  }

  // 只在用户停留底部时跟随新增内容
  if (followLatest) {
    void nextTick(() => {
      if (scrollContainer.value === container) container.scrollTop = container.scrollHeight
    })
  }
  return true
}

// 前端预览：按事件序列走真实渲染入口
function startDemoTurn(question: string, options: { id?: string; files?: File[] } = {}): string {
  const turnId = startTurn(question, options)
  let eventIndex = 0
  const timer = window.setInterval(() => {
    if (eventIndex < demoScript.length) {
      handleEvent({ ...demoScript[eventIndex], source: 'model' }, turnId)
      eventIndex += 1
      return
    }
    setFollowUpQuestions(turnId, demoFollowUpQuestions)
    handleEvent({ type: 'done', thread_id: props.threadId }, turnId)
    window.clearInterval(timer)
    demoStreams.delete(turnId)
  }, demoTickMs)
  demoStreams.set(turnId, timer)
  return turnId
}

// 切换窗口时结束未完成的模拟回复
function stopDemoStreams(): void {
  for (const [turnId, timer] of demoStreams) {
    window.clearInterval(timer)
    handleEvent({ type: 'done' }, turnId)
  }
  demoStreams.clear()
}

defineExpose({
  startTurn,
  startDemoTurn,
  stopDemoStreams,
  handleEvent,
  loadTurns,
  setFollowUpQuestions,
})

onUnmounted(() => {
  stopDemoStreams()
  chatSessions.saveTurns(props.threadId, turns.value)
})
</script>

<style scoped>
.message-event-handler {
  position: relative;
  height: 100%;
}
.message-scroll {
  height: 100%;
  overflow-y: auto;
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
  margin: 0 auto;
  padding: 24px 16px 24px 36px;
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
.follow-up-questions {
  display: flex;
  flex-direction: column;
  /* 按内容收窄，空白处不响应点击 */
  align-items: flex-start;
  gap: 2px;
  max-width: 100%;
  margin-top: 2px;
}
.follow-up-question {
  display: flex;
  align-items: center;
  gap: 9px;
  max-width: 100%;
  padding: 5px 0;
  border: 0;
  background: none;
  color: #6d757e;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 400;
  line-height: 22px;
  text-align: left;
  transition: color 0.16s ease;
}
.follow-up-label {
  min-width: 0;
  overflow-wrap: anywhere;
}
.follow-up-arrow {
  display: grid;
  place-items: center;
  flex: none;
  width: 16px;
  height: 16px;
  color: #9ca3aa;
  transition: color 0.16s ease;
}
.follow-up-question:hover:not(:disabled) {
  color: #0d0d0d;
}
.follow-up-question:hover:not(:disabled) .follow-up-arrow {
  color: #57606a;
}
.follow-up-question:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
  border-radius: 6px;
}
.follow-up-question:disabled {
  opacity: 0.55;
  cursor: default;
}
@media (prefers-reduced-motion: reduce) {
  .follow-up-question,
  .follow-up-arrow {
    transition: none;
  }
  .message-item {
    animation: none;
  }
}
</style>
