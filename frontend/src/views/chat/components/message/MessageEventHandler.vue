<!--消息流容器-->
<template>
  <div class="message-event-handler">
    <div ref="scrollContainer" class="message-scroll" @scroll="onScroll">
      <div class="message-list">
        <p v-if="earlierLoading" class="list-tip">加载中…</p>
        <p v-else-if="earlierEnded && displayTurns.length" class="list-tip">没有更早的消息了</p>
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
              <MessageReasoning
                v-else-if="item.type === 'reasoning'"
                :content="item.content"
                :started-at="item.startedAt"
                :duration-ms="item.durationMs"
                :streaming="turn.status === 'streaming' && item.id === turn.lastItemId"
                :expanded="turn.status === 'streaming'"
              />
              <ToolCallMessage
                v-else-if="item.type === 'tool_group'"
                :tools="item.tools"
                :expanded="turn.status === 'streaming'"
              />
              <SubagentMessage
                v-else-if="item.type === 'delegation_group'"
                :host="item.host"
                :parts="item.parts"
              />
              <MessageError v-else :content="item.content" />
            </div>
            <TurnActions
              v-if="turn.status === 'completed' && turn.items.length"
              :items="turn.items"
              :usage="turn.usage"
              :feedback="turn.feedback"
              @feedback="chatSessions.setFeedback(turn.id, $event)"
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
                :disabled="isResponding || !chatSessions.hasStreamSlot()"
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
import { ElMessage } from 'element-plus'
import { CornerDownRight } from 'lucide-vue-next'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import type { ChatSendRequest } from '@/api/chat'
import { useChatSessionsStore } from '@/stores/chatSessions'
import { createUuid } from '@/utils/uuidUtil'
import MessageChunk from './MessageChunk.vue'
import MessageError from './MessageError.vue'
import MessageLocator from './MessageLocator.vue'
import MessageReasoning from './MessageReasoning.vue'
import SubagentMessage from './SubagentMessage.vue'
import ToolCallMessage from './ToolCallMessage.vue'
import TurnActions from './TurnActions.vue'
import UserMessage from './UserMessage.vue'
import { groupItems, isRunningTool } from './messageTurn'
import type { ChatTurn, StreamStatusInfo, ToolItem, TurnItem } from './messageTurn'

const props = defineProps<{ threadId: string }>()
const emit = defineEmits<{
  'responding-change': [active: boolean]
  'phase-change': [status: StreamStatusInfo]
  'edit-message': [content: string]
  'fork-created': [threadId: string]
  'ask-follow-up': [question: string]
}>()
const chatSessions = useChatSessionsStore()

const scrollContainer = ref<HTMLElement | null>(null)
// 定位号只在本视图内分配
const locatorIds = new Map<string, number>()
let nextLocatorId = 0

// 距顶部多少像素内算滑到了顶
const TOP_EDGE_PX = 60

// 距底部多少像素内算跟着最新内容
const BOTTOM_EDGE_PX = 96

// 用户是否停在最新一条
let pinned = true

// 只显示当前会话，后台会话的事件不经过这里
const turns = computed(() => chatSessions.getTurns(props.threadId))

function locatorIdOf(turnId: string): number {
  const known = locatorIds.get(turnId)
  if (known !== undefined) return known
  const assigned = nextLocatorId++
  locatorIds.set(turnId, assigned)
  return assigned
}

const isResponding = computed(() => turns.value.some((turn) => turn.status === 'streaming'))
watch(isResponding, (active) => emit('responding-change', active), { immediate: true })

// 输入区提示用的当前流式阶段
const streamStatus = computed<StreamStatusInfo>(() => {
  // 委派桶登记在普通 Map 里，靠事件计数保证能重算
  void chatSessions.streamTick(props.threadId)
  const active = [...turns.value].reverse().find((turn) => turn.status === 'streaming')
  if (!active) return { phase: 'idle' }

  const last = active.items[active.items.length - 1]
  if (last?.type === 'tool' && isRunningTool(last)) {
    // 委派进行中，提示跟着子代理最新那一步走
    return last.subagent === undefined ? { phase: 'tool' } : delegationStatus(active.id, last)
  }
  return { phase: active.items.length ? 'streaming' : 'waiting' }
})
watch(streamStatus, (status) => emit('phase-change', status), { immediate: true })

// 子代理最新那一步是工具就说工具名，否则当它在组织回复
function delegationStatus(turnId: string, host: ToolItem): StreamStatusInfo {
  const parts = delegationParts(turnId, host)
  const step = parts?.[parts.length - 1]
  const subagent = host.subagent
  if (!step) return { phase: 'tool', subagent }
  if (step.type === 'tool' && isRunningTool(step)) {
    return { phase: 'tool', subagent, tool: step.tool || undefined }
  }
  return { phase: 'streaming', subagent }
}

// 实时路径的子项在委派桶里，按宿主的调用标识取
function delegationParts(turnId: string, host: ToolItem): TurnItem[] | undefined {
  const delegationId = host.toolCallId
  if (delegationId === undefined) return undefined
  const bucket = chatSessions.getDelegation(turnId, delegationId)
  // 交一份新数组，不让调用方碰到桶内实体
  return bucket?.items.slice()
}

const displayTurns = computed(() => {
  void chatSessions.streamTick(props.threadId)
  return turns.value.map((turn) => ({
    ...turn,
    locatorId: locatorIdOf(turn.id),
    displayItems: groupItems(turn.items, (host) => delegationParts(turn.id, host)),
    lastItemId: turn.items[turn.items.length - 1]?.id ?? -1,
    visibleFollowUps:
      turn.followUpQuestions?.map((question) => question.trim()).filter(Boolean) ?? [],
  }))
})
// 预览正文摘要，只取回复文字、不含代码块
function locatorExcerpt(turn: ChatTurn): string {
  const reply = turn.items
    .flatMap((item) => (item.type === 'message_chunk' ? [item.content] : []))
    .join('\n')
  return reply
    .replace(/```[\s\S]*?(```|$)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 120)
}

const locatorItems = computed(() =>
  turns.value.map((turn) => ({
    id: locatorIdOf(turn.id),
    label:
      turn.question.replace(/\s+/g, ' ').slice(0, 32) ||
      turn.attachments
        ?.map((file) => file.name)
        .join('、')
        .slice(0, 32) ||
      '消息',
    excerpt: locatorExcerpt(turn),
  })),
)

// 顶部翻页提示用当前会话的翻页状态
const earlierLoading = computed(() => chatSessions.isTurnsLoading(props.threadId))
const earlierEnded = computed(() => chatSessions.isTurnsEnded(props.threadId))

// 将选中轮次及之前的对话复制到新窗口
function forkTurn(turnId: string): void {
  const index = turns.value.findIndex((turn) => turn.id === turnId)
  if (index < 0) return
  const newThreadId = chatSessions.createSession()
  const sourceTitle = chatSessions.sessions.find((session) => session.id === props.threadId)?.title
  chatSessions.ensureSession(newThreadId).title = `${sourceTitle || '新对话'}（分支）`.slice(0, 40)
  const history: ChatTurn[] = turns.value.slice(0, index + 1).map((turn) => ({
    id: createUuid(),
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
  chatSessions.setTurns(newThreadId, history)
  emit('fork-created', newThreadId)
}

// 停在最新一条，往上滑再翻更早的轮次
function scrollToBottom(): void {
  pinned = true
  void nextTick(() => {
    const container = scrollContainer.value
    if (container) container.scrollTop = container.scrollHeight
  })
}

// 切换窗口只换显示的数据源，正在跑的流不受影响
async function switchThread(nextId: string): Promise<void> {
  chatSessions.setViewing(nextId)
  scrollToBottom()
  if (chatSessions.isHistoryLoaded(nextId)) return
  try {
    await chatSessions.loadHistory(nextId)
  } catch {
    // 拉取失败按空历史显示，切回来时重试
    return
  }
  if (props.threadId === nextId) scrollToBottom()
}

// 滑到接近顶部时往前翻一页更早的轮次
async function onScroll(): Promise<void> {
  const container = scrollContainer.value
  if (!container) return

  pinned = container.scrollHeight - container.scrollTop - container.clientHeight <= BOTTOM_EDGE_PX
  if (container.scrollTop > TOP_EDGE_PX) return

  const threadId = props.threadId
  if (chatSessions.isTurnsLoading(threadId) || chatSessions.isTurnsEnded(threadId)) return

  const previousHeight = container.scrollHeight
  const previousTop = container.scrollTop
  const older = await chatSessions.loadMoreHistory(threadId)
  // 已经切走或没有新内容，位置不用调整
  if (props.threadId !== threadId || !older.length) return

  // 补回新增高度，视线仍停在原来的那条
  await nextTick()
  container.scrollTop = previousTop + container.scrollHeight - previousHeight
}

watch(
  () => props.threadId,
  (nextId) => void switchThread(nextId),
  { immediate: true },
)

// 后台会话的事件不影响当前视图，只有当前会话才跟着走
watch(
  () => chatSessions.streamTick(props.threadId),
  () => {
    if (!pinned) return
    void nextTick(() => {
      const container = scrollContainer.value
      if (container) container.scrollTop = container.scrollHeight
    })
  },
)

// 错误提示只对当前会话弹出
watch(
  () => chatSessions.pendingNotice,
  (notice) => {
    if (!notice) return
    chatSessions.clearNotice()
    ElMessage.error({ message: notice.message, plain: true })
  },
)

// 发送提问，附件仅在本地展示
function startChatTurn(
  question: string,
  options: { files?: File[]; request?: ChatSendRequest } = {},
): string {
  pinned = true
  return chatSessions.startChatTurn(props.threadId, question, options)
}

// 只中断当前会话未完成的回复
function stopChatTurns(): void {
  chatSessions.stopThreadTurns(props.threadId)
}

defineExpose({ startChatTurn, stopChatTurns })

// 离开页面后不算在看，收尾会留未读点
onUnmounted(() => chatSessions.setViewing(null))
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
  /* 往上翻页时手动补滚动位置，别让浏览器锚定重复调整 */
  overflow-anchor: none;
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
.list-tip {
  margin: 0;
  color: #a8adb3;
  font-size: 12px;
  text-align: center;
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
