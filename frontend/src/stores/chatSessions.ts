import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { streamChat } from '@/api/chat'
import type { ChatSendRequest, ChatStreamRequest } from '@/api/chat'
import { fetchThreadTurns, fetchThreads } from '@/api/history'
import type { ThreadCursor, ThreadInfo, TurnInfo } from '@/api/history'
import { mapTurns, toTimestamp } from '@/views/chat/components/message/historyMapper'
import { createTurnRuntime, isRunningTool } from '@/views/chat/components/message/messageTurn'
import type {
  ChatTurn,
  DelegationBucket,
  ToolItem,
  TurnFeedback,
  TurnItem,
  TurnRuntime,
  TurnUsage,
} from '@/views/chat/components/message/messageTurn'
import { createUuid } from '@/utils/uuidUtil'

export interface ChatSession {
  id: string
  title: string
  createdAt: number
  // 会话累计输入 Token
  inputTokens: number
  // 会话累计输出 Token
  outputTokens: number
}

// 侧栏一次加载的会话条数
const THREAD_PAGE_SIZE = 20

// 消息区一次加载的轮次条数
const TURN_PAGE_SIZE = 20

// 同时接收流式回复的会话数上限
const MAX_CONCURRENT_STREAMS = 3

interface MessageEvent {
  type: string
  [key: string]: unknown
}

function isMessageEvent(value: unknown): value is MessageEvent {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    'type' in value &&
    typeof value.type === 'string'
  )
}

// 从时间戳算经过的毫秒数
function elapsedSince(startedAt?: number): number | undefined {
  return startedAt === undefined ? undefined : Date.now() - startedAt
}

// 空串按缺失处理
function readToolIdentity(value: unknown): string | undefined {
  return typeof value === 'string' && value ? value : undefined
}

// 复制一份轮次，避免和调用方共用对象
function copyTurn(turn: ChatTurn): ChatTurn {
  return {
    ...turn,
    attachments: turn.attachments?.map((attachment) => ({ ...attachment })),
    items: turn.items.map((item) => ({ ...item })),
    usage: turn.usage && { ...turn.usage },
    followUpQuestions: turn.followUpQuestions?.slice(),
  }
}

export const useChatSessionsStore = defineStore('chatSessions', () => {
  const sessions = ref<ChatSession[]>([])
  // 下一页游标，指向已加载最早的一条远端会话
  const threadsCursor = ref<ThreadCursor | null>(null)
  // 更早的会话是否已经取完
  const threadsEnded = ref(false)
  // 会话列表是否正在加载
  const threadsLoading = ref(false)
  // 每个会话的轮次列表，流式事件直接写这里
  const turnsByThread = ref<Record<string, ChatTurn[]>>({})
  // 每个会话已加载最早一轮的序号，向上翻页的游标
  const turnsCursor = ref<Record<string, number>>({})
  // 每个会话更早的轮次是否已经取完
  const turnsEnded = ref<Record<string, boolean>>({})
  // 每个会话是否正在拉更早的轮次
  const turnsLoading = ref<Record<string, boolean>>({})
  // 每个会话收到的事件条数，视图用它决定是否跟到最新
  const streamTicks = ref<Record<string, number>>({})
  // 正在回复的会话，侧边栏动画用
  const respondingThreadIds = ref<Set<string>>(new Set())
  // 回复结束时用户没在看的会话
  const unreadThreadIds = ref<Set<string>>(new Set())
  // 待提示的错误
  const pendingNotice = ref<{ threadId: string; message: string } | null>(null)
  // 正在显示的会话
  const viewingThreadId = ref<string | null>(null)
  // 每轮的事件定位状态
  const runtimes = new Map<string, TurnRuntime>()
  // 每轮未完成的请求
  const activeStreams = new Map<string, AbortController>()
  // 每轮属于哪个会话
  const turnThreads = new Map<string, string>()
  // 已经读过服务端历史的会话，切回来不再重复拉
  const historyLoaded = new Set<string>()
  // 服务端返回过的会话标识，用来认出本地新建未落库的会话
  const loadedThreadIds = new Set<string>()
  // 只复用本地创建且尚未提问的会话
  const localSessionIds = new Set<string>()

  function markUnread(id: string): void {
    unreadThreadIds.value.add(id)
  }

  function clearUnread(id: string): void {
    unreadThreadIds.value.delete(id)
  }

  function isUnread(id: string): boolean {
    return unreadThreadIds.value.has(id)
  }

  // 记下当前显示的是哪个会话
  function setViewing(id: string | null): void {
    viewingThreadId.value = id
  }

  // 该会话此刻是否被看着
  function isWatched(id: string): boolean {
    return id === viewingThreadId.value && !document.hidden && document.hasFocus()
  }

  // 收尾时会话没被看着就记未读
  function markUnreadWhenUnwatched(turn: ChatTurn): void {
    if (isWatched(turn.threadId)) return
    markUnread(turn.threadId)
  }

  function ensureSession(id: string): ChatSession {
    const existing = sessions.value.find((session) => session.id === id)
    if (existing) return existing
    const session = {
      id,
      title: '新对话',
      createdAt: Date.now(),
      inputTokens: 0,
      outputTokens: 0,
    }
    sessions.value.unshift(session)
    return session
  }

  function createSession(): string {
    const id = createUuid()
    ensureSession(id)
    localSessionIds.add(id)
    markHistoryLoaded(id)
    return id
  }

  // 当前页面也是空会话时优先复用，并清理此前遗留的重复空会话
  function getOrCreateEmptySession(currentThreadId?: string): string {
    const current = sessions.value.find((session) => session.id === currentThreadId)
    const currentEmpty =
      current && !loadedThreadIds.has(current.id) && getTurns(current.id).length === 0
        ? current
        : undefined
    const empty = sessions.value.filter(
      (session) =>
        !loadedThreadIds.has(session.id) &&
        (session.id === currentEmpty?.id ||
          localSessionIds.has(session.id) ||
          historyLoaded.has(session.id)) &&
        getTurns(session.id).length === 0,
    )
    const kept = currentEmpty || empty[0]
    if (!kept) return createSession()

    // 旧版已生成的空会话可能不在 localSessionIds 中，按已加载的本地空会话一起去重
    const redundant = new Set(
      empty.filter((session) => session.id !== kept.id).map((session) => session.id),
    )
    if (redundant.size) {
      sessions.value = sessions.value.filter((session) => !redundant.has(session.id))
      for (const id of redundant) {
        localSessionIds.delete(id)
        historyLoaded.delete(id)
        unreadThreadIds.value.delete(id)
        delete turnsByThread.value[id]
        delete turnsCursor.value[id]
        delete turnsEnded.value[id]
        delete turnsLoading.value[id]
        delete streamTicks.value[id]
      }
    }
    localSessionIds.add(kept.id)
    return kept.id
  }

  // 用首条消息生成会话标题
  function titleFromMessage(id: string, message: string): void {
    const session = ensureSession(id)
    if (session.title !== '新对话') return
    const title = message.replace(/\s+/g, ' ').trim()
    if (title) session.title = title.slice(0, 40)
  }

  // 服务端会话转侧栏条目
  function toSession(thread: ThreadInfo): ChatSession {
    return {
      id: thread.thread_id,
      title: thread.title,
      createdAt: toTimestamp(thread.created_at),
      inputTokens: thread.input_tokens,
      outputTokens: thread.output_tokens,
    }
  }

  // 满页才可能还有更早的，游标取这一页最后一条
  function nextCursor(page: ThreadInfo[]): ThreadCursor | null {
    const last = page.at(-1)
    if (page.length < THREAD_PAGE_SIZE || !last) return null
    return { createdAt: last.created_at, threadId: last.thread_id }
  }

  // 记下服务端给过的会话标识
  function rememberThreads(page: ThreadInfo[]): void {
    for (const thread of page) loadedThreadIds.add(thread.thread_id)
  }

  // 拉首页会话列表，本地新建未落库的会话排在前面
  async function loadThreads(): Promise<void> {
    if (threadsLoading.value) return
    threadsLoading.value = true
    try {
      const page = await fetchThreads(THREAD_PAGE_SIZE)
      rememberThreads(page)
      const local = sessions.value.filter((item) => !loadedThreadIds.has(item.id))
      sessions.value = [...local, ...page.map(toSession)]
      threadsCursor.value = nextCursor(page)
      threadsEnded.value = threadsCursor.value === null
    } catch {
      // 拉取失败保留本地列表
    } finally {
      threadsLoading.value = false
    }
  }

  // 从游标往前翻一页，追加在列表末尾
  async function loadMoreThreads(): Promise<void> {
    const cursor = threadsCursor.value
    if (!cursor || threadsLoading.value) return
    threadsLoading.value = true
    try {
      const page = await fetchThreads(THREAD_PAGE_SIZE, cursor)
      rememberThreads(page)
      const known = new Set(sessions.value.map((item) => item.id))
      const added = page.map(toSession).filter((item) => !known.has(item.id))
      sessions.value = [...sessions.value, ...added]
      threadsCursor.value = nextCursor(page)
      threadsEnded.value = threadsCursor.value === null
    } catch {
      // 拉取失败保持现状，下次滚动再试
    } finally {
      threadsLoading.value = false
    }
  }

  // 该会话是否已经确定过历史来源
  function isHistoryLoaded(id: string): boolean {
    return historyLoaded.has(id)
  }

  // 本地生成的会话不用拉历史
  function markHistoryLoaded(id: string): void {
    historyLoaded.add(id)
  }

  // 记下这一页最早一轮的序号，不足一页说明没有更早的了
  function rememberTurnPage(id: string, page: TurnInfo[]): void {
    const oldest = page[0]
    if (page.length < TURN_PAGE_SIZE || !oldest) {
      turnsEnded.value[id] = true
      return
    }
    turnsCursor.value[id] = oldest.seq
    turnsEnded.value[id] = false
  }

  // 拉取会话首页历史并写入本地缓存，会话不存在时按空历史处理
  async function loadHistory(id: string): Promise<ChatTurn[]> {
    const page = await fetchThreadTurns(id, TURN_PAGE_SIZE)
    markHistoryLoaded(id)
    // 本地已提问但服务端还没有的轮次接在历史后面，正在流式的不能丢
    const pending = getTurns(id).filter((turn) => !page?.some((item) => item.turn_id === turn.id))
    if (!page) {
      turnsEnded.value[id] = true
      return pending
    }
    rememberTurnPage(id, page)
    const history = [...mapTurns(id, page), ...pending]
    setTurns(id, history)
    return history
  }

  // 从游标往上翻一页更早的轮次，接在缓存列表前面
  async function loadMoreHistory(id: string): Promise<ChatTurn[]> {
    const cursor = turnsCursor.value[id]
    if (cursor === undefined || turnsLoading.value[id]) return []
    turnsLoading.value[id] = true
    try {
      const page = await fetchThreadTurns(id, TURN_PAGE_SIZE, cursor)
      if (!page) {
        turnsEnded.value[id] = true
        return []
      }
      rememberTurnPage(id, page)
      const cached = getTurns(id)
      const known = new Set(cached.map((turn) => turn.id))
      const older = mapTurns(id, page).filter((turn) => !known.has(turn.id))
      if (older.length) setTurns(id, [...older, ...cached])
      return older
    } finally {
      turnsLoading.value[id] = false
    }
  }

  // 覆盖写入某会话的轮次列表
  function setTurns(id: string, turns: ChatTurn[]): void {
    turnsByThread.value[id] = turns.map(copyTurn)
    for (const turn of turns) turnThreads.set(turn.id, id)
    syncResponding(id)
  }

  // 更早的轮次接在列表前面
  function prependTurns(id: string, older: ChatTurn[]): void {
    setTurns(id, [...older, ...getTurns(id)])
  }

  // 该会话的轮次列表
  function getTurns(id: string): ChatTurn[] {
    return turnsByThread.value[id] ?? []
  }

  // 该会话的轮次列表，没有就建一条空的
  function turnsRef(id: string): ChatTurn[] {
    const known = turnsByThread.value[id]
    if (known) return known
    const created: ChatTurn[] = []
    turnsByThread.value[id] = created
    return created
  }

  // 按轮次标识找这一轮
  function findTurn(turnId: string): ChatTurn | undefined {
    const threadId = turnThreads.get(turnId)
    return threadId === undefined
      ? undefined
      : getTurns(threadId).find((item) => item.id === turnId)
  }

  // 某次委派收到的子项
  function getDelegation(turnId: string, delegationId: string): DelegationBucket | undefined {
    return runtimes.get(turnId)?.delegations.get(delegationId)
  }

  // 该会话是否还有未收尾的轮次
  function isThreadResponding(id: string): boolean {
    return getTurns(id).some((turn) => turn.status === 'streaming')
  }

  function syncResponding(id: string): void {
    if (isThreadResponding(id)) respondingThreadIds.value.add(id)
    else respondingThreadIds.value.delete(id)
  }

  // 没到上限才能再起一条流
  function hasStreamSlot(): boolean {
    return respondingThreadIds.value.size < MAX_CONCURRENT_STREAMS
  }

  // 通知视图这个会话又多了一段内容
  function bumpTick(id: string): void {
    streamTicks.value[id] = (streamTicks.value[id] ?? 0) + 1
  }

  function streamTick(id: string): number {
    return streamTicks.value[id] ?? 0
  }

  // 该会话更早的轮次是否已经取完
  function isTurnsEnded(id: string): boolean {
    return turnsEnded.value[id] === true
  }

  // 该会话是否正在拉更早的轮次
  function isTurnsLoading(id: string): boolean {
    return turnsLoading.value[id] === true
  }

  // 汇总同一会话的 Token 用量，只认服务端给的会话累计值
  function getUsage(id: string): TurnUsage {
    const session = sessions.value.find((item) => item.id === id)
    const inputTokens = session?.inputTokens ?? 0
    const outputTokens = session?.outputTokens ?? 0
    return { inputTokens, outputTokens, totalTokens: inputTokens + outputTokens }
  }

  // 本次新增用量累加进会话，游标翻页不影响总数
  function addSessionTokens(id: string, inputTokens: number, outputTokens: number): void {
    const session = sessions.value.find((item) => item.id === id)
    if (!session) return
    session.inputTokens += inputTokens
    session.outputTokens += outputTokens
  }

  // 一次提问建一轮，后续事件只写入这一轮
  function startTurn(
    threadId: string,
    question: string,
    options: { id?: string; files?: File[] } = {},
  ): string {
    const turns = turnsRef(threadId)
    const turnId = options.id ?? createUuid()
    if (turns.some((turn) => turn.id === turnId)) throw new Error('turn_id 已存在')
    const attachments = options.files?.map((file) => {
      const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      return {
        id: createUuid(),
        name: file.name,
        type: file.type,
        size: file.size,
        previewUrl,
      }
    })
    turns.push({
      id: turnId,
      threadId,
      question,
      createdAt: Date.now(),
      attachments,
      status: 'streaming',
      items: [],
    })
    turnThreads.set(turnId, threadId)
    localSessionIds.delete(threadId)
    runtimes.set(turnId, createTurnRuntime())
    syncResponding(threadId)
    bumpTick(threadId)
    return turnId
  }

  // 反馈仅记录在当前轮次，切换会话时仍可恢复
  function setFeedback(turnId: string, feedback: TurnFeedback | undefined): void {
    const turn = findTurn(turnId)
    if (turn) turn.feedback = feedback
  }

  // 本轮有推荐问题时才写入，完成后展示在回复操作区下方
  function setFollowUpQuestions(turnId: string, questions: string[]): boolean {
    const turn = findTurn(turnId)
    if (!turn) return false
    turn.followUpQuestions = questions
      .map((question) => question.trim())
      .filter(Boolean)
      .slice(0, 3)
    return true
  }

  // 取走待提示的错误
  function clearNotice(): void {
    pendingNotice.value = null
  }

  // 只合并同一正文块内的连续文字片段
  function handleMessageChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    if (typeof event.content !== 'string' || event.content.length === 0) return

    const messageId = typeof event.message_id === 'string' ? event.message_id : undefined
    const activeItem = turn.items.find((item) => item.id === runtime.activeTextItemId)
    if (
      activeItem?.type === 'message_chunk' &&
      (!messageId || activeItem.messageId === messageId)
    ) {
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
    turn: ChatTurn,
    runtime: TurnRuntime,
    event: MessageEvent,
  ): ToolItem | undefined {
    const callId = readToolIdentity(event.tool_call_id)
    const toolName = readToolIdentity(event.tool)
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
      // 拿到真实标识才建项
      if (callId === undefined && toolName === undefined) return undefined
      item = {
        id: runtime.nextItemId++,
        type: 'tool',
        tool: '',
        status: 'preparing',
        startedAt: Date.now(),
      }
      turn.items.push(item)
    }

    if (callId !== undefined) {
      item.toolCallId = callId
      runtime.toolItemsByCallId.set(callId, item.id)
    }
    if (index !== undefined) runtime.toolItemsByIndex.set(index, item.id)
    if (toolName !== undefined) item.tool = toolName
    return item
  }

  function handleToolCallChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item || typeof event.arguments !== 'string') return
    item.arguments = `${typeof item.arguments === 'string' ? item.arguments : ''}${event.arguments}`
  }

  function handleToolStart(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'running'
    if (event.arguments !== undefined) item.arguments = event.arguments
  }

  function handleToolResult(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'success'
    if (event.content !== undefined) item.output = event.content
    if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
    else item.durationMs ??= elapsedSince(item.startedAt)
  }

  function handleToolError(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'error'
    item.output = event.content ?? event.message
    if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
    else item.durationMs ??= elapsedSince(item.startedAt)
  }

  // 一次委派一个桶，边界事件先到就先建
  function ensureBucket(
    runtime: TurnRuntime,
    delegationId: string,
    subagent: string,
  ): DelegationBucket {
    const existing = runtime.delegations.get(delegationId)
    if (existing) return existing
    // 桶要包成响应式：子项状态是原地改的，不包不会触发更新
    const bucket: DelegationBucket = {
      subagent,
      items: reactive<TurnItem[]>([]),
      runtime: createTurnRuntime(),
    }
    runtime.delegations.set(delegationId, bucket)
    return bucket
  }

  // 子代理事件收进委派桶，子项形状与主代理同款，处理函数直接复用
  function handleSubagent(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const delegationId = readToolIdentity(event.delegation_id)
    const subagent = readToolIdentity(event.subagent)
    if (delegationId === undefined || subagent === undefined) return

    // 主代理正文不在委派期间续写
    closeMessageChunk(runtime)

    // 边界事件也标宿主，子代理名挂在宿主那条上
    const hostId = runtime.toolItemsByCallId.get(delegationId)
    const hostItem =
      hostId === undefined ? undefined : turn.items.find((item) => item.id === hostId)
    if (hostItem?.type === 'tool') hostItem.subagent = subagent

    const subType = readToolIdentity(event.sub_type)
    if (subType === 'start' || subType === 'finish' || subType === 'error') return

    const bucket = ensureBucket(runtime, delegationId, subagent)
    const scope = bucket.runtime
    // 序号仍用本轮计数器，桶内桶外的显示项不撞号
    scope.nextItemId = runtime.nextItemId
    // 子项列表当成一个轮，直接喂给同款处理函数
    const view = { items: bucket.items } as ChatTurn

    switch (subType) {
      case 'message_chunk':
        handleMessageChunk(view, scope, event)
        break
      case 'tool_start':
        closeMessageChunk(scope)
        handleToolStart(view, scope, event)
        break
      case 'tool_result':
        closeMessageChunk(scope)
        handleToolResult(view, scope, event)
        break
      case 'tool_error':
        closeMessageChunk(scope)
        handleToolError(view, scope, event)
        break
      default:
        break
    }
    runtime.nextItemId = scope.nextItemId
  }

  // 连续到达的推理片段合并进同一显示项，被正文或工具调用打断后另起一项
  function handleReasoningChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    if (typeof event.content !== 'string' || event.content.length === 0) return

    const last = turn.items[turn.items.length - 1]
    if (last?.type === 'reasoning') {
      last.content += event.content
      last.durationMs = elapsedSince(last.startedAt)
      runtime.activeReasoningItemId = last.id
      return
    }

    const id = runtime.nextItemId++
    turn.items.push({
      id,
      type: 'reasoning',
      content: event.content,
      startedAt: Date.now(),
    })
    runtime.activeReasoningItemId = id
  }

  // 忽略无效 Token 计数，避免累计值出错
  function readTokenCount(value: unknown): number | null {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null
  }

  // 每次模型响应后清空工具索引，并累计本轮用量
  function handleUsage(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
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
    const outputDetails = counts.output_token_details
    const reasoning =
      typeof outputDetails === 'object' && outputDetails !== null && !Array.isArray(outputDetails)
        ? readTokenCount((outputDetails as Record<string, unknown>).reasoning)
        : null
    if (
      input === null &&
      output === null &&
      total === null &&
      cacheRead === null &&
      reasoning === null
    ) {
      return
    }

    const previous: TurnUsage = turn.usage ?? { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
    const next: TurnUsage = {
      inputTokens: previous.inputTokens + (input ?? 0),
      outputTokens: previous.outputTokens + (output ?? 0),
      totalTokens: previous.totalTokens + (total ?? (input ?? 0) + (output ?? 0)),
      cacheReadTokens:
        cacheRead === null && previous.cacheReadTokens === undefined
          ? undefined
          : (previous.cacheReadTokens ?? 0) + (cacheRead ?? 0),
      reasoningTokens:
        reasoning === null && previous.reasoningTokens === undefined
          ? undefined
          : (previous.reasoningTokens ?? 0) + (reasoning ?? 0),
    }
    turn.usage = next
    // 会话总量只累加本次新增，翻页加载过的轮次不重复计
    addSessionTokens(
      turn.threadId,
      next.inputTokens - previous.inputTokens,
      next.outputTokens - previous.outputTokens,
    )
  }

  // 未收尾的工具按失败显示
  function closeUnfinishedTools(turn: ChatTurn, runtime: TurnRuntime): void {
    // 委派桶里的子工具也在跑，收尾要连着扫
    const itemLists = [
      turn.items,
      ...[...runtime.delegations.values()].map((bucket) => bucket.items),
    ]
    for (const items of itemLists) {
      for (const item of items) {
        if (item.type !== 'tool' || !isRunningTool(item)) continue
        item.status = 'error'
        item.durationMs ??= elapsedSince(item.startedAt)
      }
    }
  }

  // 结束当前正文块，下一段文字会新建显示项
  function closeMessageChunk(runtime: TurnRuntime): void {
    runtime.activeTextItemId = null
  }

  // 结束当前推理块并记录耗时，供标题悬停显示
  function closeReasoning(turn: ChatTurn, runtime: TurnRuntime): void {
    const activeId = runtime.activeReasoningItemId
    runtime.activeReasoningItemId = null
    if (activeId === null) return

    const item = turn.items.find((entry) => entry.id === activeId)
    if (item?.type === 'reasoning') item.durationMs = elapsedSince(item.startedAt)
  }

  // 结束状态写回历史，避免重开窗口后持续显示加载中
  function handleDone(turn: ChatTurn, runtime: TurnRuntime): void {
    turn.status = 'completed'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    syncResponding(turn.threadId)
  }

  // 主动停止或连接中断，保留已有回复但不算完成
  function handleInterrupted(turn: ChatTurn, runtime: TurnRuntime): void {
    turn.status = 'interrupted'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    syncResponding(turn.threadId)
  }

  function handleError(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const message = typeof event.message === 'string' && event.message ? event.message : '请求失败'
    turn.items.push({ id: runtime.nextItemId++, type: 'error', content: message })
    turn.status = 'failed'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    // 正看着这条会话才弹提示，后台收尾只留错误段
    if (isWatched(turn.threadId)) pendingNotice.value = { threadId: turn.threadId, message }
    syncResponding(turn.threadId)
  }

  // SSE 事件按轮次标识找到所属会话再写入，后台会话照收
  function handleEvent(value: unknown, turnId: string): boolean {
    if (!isMessageEvent(value)) return false
    const turn = findTurn(turnId)
    const runtime = turn && runtimes.get(turn.id)
    if (!turn || !runtime || turn.status !== 'streaming') return false

    // 除推理片段本身，其他事件都表示上一段推理已经结束
    if (value.type !== 'reasoning_chunk') closeReasoning(turn, runtime)

    switch (value.type) {
      case 'message_chunk':
        handleMessageChunk(turn, runtime, value)
        break
      case 'reasoning_chunk':
        closeMessageChunk(runtime)
        handleReasoningChunk(turn, runtime, value)
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
      case 'subagent':
        closeMessageChunk(runtime)
        handleSubagent(turn, runtime, value)
        break
      case 'usage':
        handleUsage(turn, runtime, value)
        break
      case 'done':
        closeMessageChunk(runtime)
        handleDone(turn, runtime)
        break
      case 'interrupted':
        closeMessageChunk(runtime)
        handleInterrupted(turn, runtime)
        break
      case 'error':
        closeMessageChunk(runtime)
        handleError(turn, runtime, value)
        break
      default:
        return false
    }

    bumpTick(turn.threadId)
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
          if (!completed) handleEvent({ type: 'interrupted' }, turnId)
        },
      })
    } catch {
      if (!controller.signal.aborted) handleEvent({ type: 'error', message: '请求失败' }, turnId)
    } finally {
      activeStreams.delete(turnId)
    }
  }

  // 发送提问并接住回复流
  function startChatTurn(
    threadId: string,
    question: string,
    options: { files?: File[]; request?: ChatSendRequest } = {},
  ): string {
    const turnId = startTurn(threadId, question, options)
    void runChatTurn(turnId, {
      ...options.request,
      message: question,
      thread_id: threadId,
    })
    return turnId
  }

  // 中断该会话未完成的回复
  function stopThreadTurns(threadId: string): void {
    for (const turn of getTurns(threadId)) {
      if (turn.status !== 'streaming') continue
      activeStreams.get(turn.id)?.abort()
      handleEvent({ type: 'interrupted' }, turn.id)
    }
  }

  return {
    sessions,
    threadsEnded,
    threadsLoading,
    respondingThreadIds,
    unreadThreadIds,
    streamTicks,
    pendingNotice,
    createSession,
    getOrCreateEmptySession,
    ensureSession,
    setViewing,
    markUnread,
    clearUnread,
    isUnread,
    titleFromMessage,
    loadThreads,
    loadMoreThreads,
    isHistoryLoaded,
    markHistoryLoaded,
    loadHistory,
    loadMoreHistory,
    isTurnsEnded,
    isTurnsLoading,
    setTurns,
    prependTurns,
    getTurns,
    getDelegation,
    getUsage,
    addSessionTokens,
    startTurn,
    startChatTurn,
    stopThreadTurns,
    handleEvent,
    setFeedback,
    setFollowUpQuestions,
    clearNotice,
    hasStreamSlot,
    streamTick,
  }
})
