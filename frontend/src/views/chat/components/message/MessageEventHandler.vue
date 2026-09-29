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
import { streamChat, type ChatSendRequest, type ChatStreamRequest } from '@/api/chat'
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
const activeStreams = new Map<string, AbortController>()
const scrollContainer = ref<HTMLElement | null>(null)
let nextLocatorId = 0
const isResponding = computed(() => turns.value.some((turn) => turn.status === 'streaming'))

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
      stopChatTurns()
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

// 请求后端，事件只写入本次 turn
async function runChatTurn(turnId: string, request: ChatStreamRequest): Promise<void> {
  const controller = new AbortController()
  activeStreams.set(turnId, controller)
  try {
    await streamChat(request, {
      signal: controller.signal,
      onEvent: (event) => handleEvent(event, turnId),
      onClose: (completed) => {
        // 没收到结束事件说明连接被截断
        if (!completed) handleEvent({ type: 'error', message: '连接中断' }, turnId)
      },
    })
  } catch {
    if (!controller.signal.aborted) handleEvent({ type: 'error', message: '请求失败' }, turnId)
  } finally {
    activeStreams.delete(turnId)
  }
}

// 发送提问，附件仅在本地展示
function startChatTurn(
  question: string,
  options: { files?: File[]; request?: ChatSendRequest } = {},
): string {
  const turnId = startTurn(question, { files: options.files })
  void runChatTurn(turnId, {
    ...options.request,
    message: question,
    thread_id: props.threadId,
  })
  return turnId
}

// 中断未完成的回复
function stopChatTurns(): void {
  for (const [turnId, controller] of activeStreams) {
    controller.abort()
    handleEvent({ type: 'done', thread_id: props.threadId }, turnId)
  }
  activeStreams.clear()
}

defineExpose({
  startTurn,
  startChatTurn,
  stopChatTurns,
  handleEvent,
  loadTurns,
  setFollowUpQuestions,
})

onUnmounted(() => {
  stopChatTurns()
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
