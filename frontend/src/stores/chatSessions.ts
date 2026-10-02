import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchThreadTurns, fetchThreads } from '@/api/history'
import type { ThreadCursor, ThreadInfo, TurnInfo } from '@/api/history'
import { mapTurns, toTimestamp } from '@/views/chat/components/message/historyMapper'
import type { ChatTurn, TurnUsage } from '@/views/chat/components/message/messageTurn'

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
const TURN_PAGE_SIZE = 2

export const useChatSessionsStore = defineStore('chatSessions', () => {
  const sessions = ref<ChatSession[]>([])
  // 下一页游标，指向已加载最早的一条远端会话
  const threadsCursor = ref<ThreadCursor | null>(null)
  // 更早的会话是否已经取完
  const threadsEnded = ref(false)
  // 会话列表是否正在加载
  const threadsLoading = ref(false)
  const turnsByThread = ref<Record<string, ChatTurn[]>>({})
  // 每个会话已加载最早一轮的序号，向上翻页的游标
  const turnsCursor = ref<Record<string, number>>({})
  // 每个会话更早的轮次是否已经取完
  const turnsEnded = ref<Record<string, boolean>>({})
  // 每个会话是否正在拉更早的轮次
  const turnsLoading = ref<Record<string, boolean>>({})
  // 正在回复的会话，侧边栏动画用
  const respondingThreadId = ref<string | null>(null)
  // 已经读过服务端历史的会话，切回来不再重复拉
  const historyLoaded = new Set<string>()
  // 服务端返回过的会话标识，用来认出本地新建未落库的会话
  const loadedThreadIds = new Set<string>()

  function setResponding(id: string, active: boolean): void {
    if (active) respondingThreadId.value = id
    else if (respondingThreadId.value === id) respondingThreadId.value = null
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
    const id = crypto.randomUUID()
    ensureSession(id)
    markHistoryLoaded(id)
    return id
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
    if (!page) {
      turnsEnded.value[id] = true
      return []
    }
    rememberTurnPage(id, page)
    const history = mapTurns(id, page)
    saveTurns(id, history)
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
      if (older.length) saveTurns(id, [...older, ...cached])
      return older
    } finally {
      turnsLoading.value[id] = false
    }
  }

  // 保存 turn 快照，切换窗口后仍能读取用量
  function saveTurns(id: string, turns: ChatTurn[]): void {
    turnsByThread.value[id] = turns.map((turn) => ({
      ...turn,
      attachments: turn.attachments?.map((attachment) => ({ ...attachment })),
      items: turn.items.map((item) => ({ ...item })),
      usage: turn.usage && { ...turn.usage },
      followUpQuestions: turn.followUpQuestions?.slice(),
    }))
  }

  function getTurns(id: string): ChatTurn[] {
    return turnsByThread.value[id] ?? []
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

  return {
    sessions,
    threadsEnded,
    threadsLoading,
    respondingThreadId,
    createSession,
    ensureSession,
    setResponding,
    titleFromMessage,
    loadThreads,
    loadMoreThreads,
    isHistoryLoaded,
    markHistoryLoaded,
    loadHistory,
    loadMoreHistory,
    isTurnsEnded,
    isTurnsLoading,
    saveTurns,
    getTurns,
    getUsage,
    addSessionTokens,
  }
})
