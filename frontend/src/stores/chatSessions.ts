import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import type { UploadedFileInfo } from '@/api/uploads'
import { fetchThreads } from '@/api/history'
import type { ThreadCursor, ThreadInfo } from '@/api/history'
import { toChatAttachments, toTimestamp } from '@/stores/chat/historyMapper'
import { createTurnHistory } from '@/stores/chat/turnHistory'
import { useChatImagesStore } from '@/stores/chatImages'
import { createTurnRuntime } from '@/stores/chat/turnTypes'
import { createStreamEventHandler } from '@/stores/chat/streamEvents'
import {
  clearPendingStart,
  createChatStreamTransport,
  pendingStarts,
} from '@/stores/chat/streamTransport'
import type {
  ChatTurn,
  DelegationBucket,
  TurnFeedback,
  TurnRuntime,
  TurnUsage,
} from '@/stores/chat/turnTypes'
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

// 同时接收流式回复的会话数上限
const MAX_CONCURRENT_STREAMS = 3
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
  // 每个会话收到的事件条数
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
  // 主动停止的轮次
  const cancelRequested = new Set<string>()
  // 每轮属于哪个会话
  const turnThreads = new Map<string, string>()
  // 已经读过服务端历史的会话，切回来不再重复拉
  const historyLoaded = reactive(new Set<string>())
  // 服务端返回过的会话标识，用来认出本地新建未落库的会话
  const loadedThreadIds = new Set<string>()
  // 只复用本地创建且尚未提问的会话
  const localSessionIds = new Set<string>()
  // 防止删除前发出的列表请求把旧会话带回来
  const deletedThreadIds = new Set<string>()

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

  // 从本地移除已删除会话及其缓存
  function removeSession(id: string): void {
    deletedThreadIds.add(id)
    useChatImagesStore().forgetThread(id)
    sessions.value = sessions.value.filter((session) => session.id !== id)
    delete turnsByThread.value[id]
    delete turnsCursor.value[id]
    delete turnsEnded.value[id]
    delete turnsLoading.value[id]
    delete streamTicks.value[id]
    respondingThreadIds.value.delete(id)
    unreadThreadIds.value.delete(id)
    historyLoaded.delete(id)
    loadedThreadIds.delete(id)
    localSessionIds.delete(id)
    if (viewingThreadId.value === id) viewingThreadId.value = null
    if (pendingNotice.value?.threadId === id) pendingNotice.value = null
    for (const [turnId, threadId] of turnThreads) {
      if (threadId !== id) continue
      turnThreads.delete(turnId)
      runtimes.delete(turnId)
      activeStreams.get(turnId)?.abort()
      activeStreams.delete(turnId)
      clearPendingStart(turnId)
    }
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
      current &&
      !loadedThreadIds.has(current.id) &&
      (localSessionIds.has(current.id) || historyLoaded.has(current.id)) &&
      getTurns(current.id).length === 0
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
    markHistoryLoaded(kept.id)
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
      const visiblePage = page.filter((thread) => !deletedThreadIds.has(thread.thread_id))
      rememberThreads(visiblePage)
      const local = sessions.value.filter(
        (item) => !loadedThreadIds.has(item.id) && !deletedThreadIds.has(item.id),
      )
      sessions.value = [...local, ...visiblePage.map(toSession)]
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
      const visiblePage = page.filter((thread) => !deletedThreadIds.has(thread.thread_id))
      rememberThreads(visiblePage)
      const known = new Set(sessions.value.map((item) => item.id))
      const added = visiblePage.map(toSession).filter((item) => !known.has(item.id))
      sessions.value = [...sessions.value, ...added]
      threadsCursor.value = nextCursor(page)
      threadsEnded.value = threadsCursor.value === null
    } catch {
      // 拉取失败保持现状，下次滚动再试
    } finally {
      threadsLoading.value = false
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

  // 当前轮次是否在压缩上下文
  function isCompacting(turnId: string): boolean {
    return runtimes.get(turnId)?.compacting === true
  }

  // 该会话是否还有未收尾的轮次
  function isThreadResponding(id: string): boolean {
    return getTurns(id).some((turn) => turn.status === 'streaming')
  }

  // 回答正文结束后推荐问题仍在流内，连接关闭前都不允许删除
  function isThreadBusy(id: string): boolean {
    void streamTick(id)
    if (respondingThreadIds.value.has(id)) return true
    for (const turnId of activeStreams.keys()) {
      if (turnThreads.get(turnId) === id) return true
    }
    return false
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
    options: { id?: string; attachments?: UploadedFileInfo[] } = {},
  ): string {
    const turns = turnsRef(threadId)
    const turnId = options.id ?? createUuid()
    if (turns.some((turn) => turn.id === turnId)) throw new Error('turn_id 已存在')
    const attachments = options.attachments && toChatAttachments(options.attachments)
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

  // 本轮有推荐问题时才写入
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

  const handleEvent = createStreamEventHandler({
    findTurn,
    runtimes,
    addSessionTokens,
    markUnreadWhenUnwatched,
    syncResponding,
    isWatched,
    setFollowUpQuestions,
    bumpTick,
    pendingNotice,
  })

  const { runChatTurn, startChatTurn, stopThreadTurns } = createChatStreamTransport({
    activeStreams,
    cancelRequested,
    turnThreads,
    runtimes,
    pendingNotice,
    getTurns,
    findTurn,
    startTurn,
    syncResponding,
    bumpTick,
    handleEvent,
  })

  const {
    isHistoryLoaded,
    hasPendingStart,
    markHistoryLoaded,
    loadHistory,
    loadMoreHistory,
    isTurnsEnded,
    isTurnsLoading,
  } = createTurnHistory({
    historyLoaded,
    turnsCursor,
    turnsEnded,
    turnsLoading,
    deletedThreadIds,
    cancelRequested,
    activeStreams,
    getTurns,
    setTurns,
    findTurn,
    startTurn,
    runChatTurn,
  })

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
    removeSession,
    setViewing,
    markUnread,
    clearUnread,
    isUnread,
    isThreadBusy,
    titleFromMessage,
    loadThreads,
    loadMoreThreads,
    isHistoryLoaded,
    hasPendingStart,
    markHistoryLoaded,
    loadHistory,
    loadMoreHistory,
    isTurnsEnded,
    isTurnsLoading,
    setTurns,
    prependTurns,
    getTurns,
    getDelegation,
    isCompacting,
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
