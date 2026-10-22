import { fetchThreadTurns } from '@/api/history'
import type { TurnInfo } from '@/api/history'
import type { ChatStreamRequest } from '@/api/chat'
import type { UploadedFileInfo } from '@/api/uploads'
import { mapTurns } from '@/stores/chat/historyMapper'
import { clearPendingStart, pendingStarts } from '@/stores/chat/streamTransport'
import type { ChatTurn } from '@/stores/chat/turnTypes'
import type { Ref } from 'vue'

interface TurnHistoryContext {
  historyLoaded: Set<string>
  turnsCursor: Ref<Record<string, number>>
  turnsEnded: Ref<Record<string, boolean>>
  turnsLoading: Ref<Record<string, boolean>>
  deletedThreadIds: Set<string>
  cancelRequested: Set<string>
  activeStreams: Map<string, AbortController>
  getTurns: (threadId: string) => ChatTurn[]
  setTurns: (threadId: string, turns: ChatTurn[]) => void
  findTurn: (turnId: string) => ChatTurn | undefined
  startTurn: (
    threadId: string,
    question: string,
    options?: { id?: string; attachments?: UploadedFileInfo[] },
  ) => string
  runChatTurn: (turnId: string, request?: ChatStreamRequest) => Promise<void>
}

// 消息区一次加载的轮次条数
const TURN_PAGE_SIZE = 20

/** 加载与恢复会话轮次，并维护历史分页状态 */
export function createTurnHistory(context: TurnHistoryContext) {
  const {
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
  } = context

  // 该会话是否已经确定过历史来源
  function isHistoryLoaded(id: string): boolean {
    return historyLoaded.has(id)
  }

  // 会话内是否有待确认请求
  function hasPendingStart(id: string): boolean {
    return pendingStarts().some((entry) => entry.request.thread_id === id)
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
    if (deletedThreadIds.has(id)) return []
    markHistoryLoaded(id)
    // 本地已提问但服务端还没有的轮次接在历史后面，正在流式的不能丢
    const pending = getTurns(id).filter((turn) => !page?.some((item) => item.turn_id === turn.id))
    const pendingStartsForThread = pendingStarts().filter((entry) => entry.request.thread_id === id)
    if (!page) {
      turnsEnded.value[id] = true
      for (const entry of pendingStartsForThread) {
        if (entry.cancelRequested) cancelRequested.add(entry.turnId)
        if (!findTurn(entry.turnId))
          startTurn(id, entry.request.message, {
            id: entry.turnId,
            attachments: entry.request.attachments,
          })
        void runChatTurn(entry.turnId, entry.request)
      }
      return getTurns(id)
    }
    rememberTurnPage(id, page)
    const serverTurns = mapTurns(id, page).map((turn) => {
      const live = getTurns(id).find((item) => item.id === turn.id)
      return live?.status === 'streaming' && activeStreams.has(turn.id) ? live : turn
    })
    const history = [...serverTurns, ...pending]
    setTurns(id, history)
    for (const entry of pendingStartsForThread) {
      const stored = history.find((turn) => turn.id === entry.turnId)
      if (stored && (stored.status === 'failed' || stored.status === 'interrupted')) {
        clearPendingStart(entry.turnId)
      }
    }
    const lastTurn = history[history.length - 1]
    for (const turn of history) {
      if (turn.status !== 'streaming' && !(turn === lastTurn && turn.status === 'completed'))
        continue
      if (activeStreams.has(turn.id)) continue
      const pendingStart = pendingStartsForThread.find((entry) => entry.turnId === turn.id)
      if (pendingStart) {
        if (pendingStart.cancelRequested) cancelRequested.add(turn.id)
        void runChatTurn(turn.id, pendingStart.request)
      } else void runChatTurn(turn.id)
    }
    for (const entry of pendingStartsForThread) {
      if (history.some((turn) => turn.id === entry.turnId)) continue
      if (entry.cancelRequested) cancelRequested.add(entry.turnId)
      startTurn(id, entry.request.message, {
        id: entry.turnId,
        attachments: entry.request.attachments,
      })
      void runChatTurn(entry.turnId, entry.request)
    }
    return history
  }

  // 从游标往上翻一页更早的轮次，接在缓存列表前面
  async function loadMoreHistory(id: string): Promise<ChatTurn[]> {
    const cursor = turnsCursor.value[id]
    if (cursor === undefined || turnsLoading.value[id]) return []
    turnsLoading.value[id] = true
    try {
      const page = await fetchThreadTurns(id, TURN_PAGE_SIZE, cursor)
      if (deletedThreadIds.has(id)) return []
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
      if (!deletedThreadIds.has(id)) turnsLoading.value[id] = false
    }
  }

  // 该会话更早的轮次是否已经取完
  function isTurnsEnded(id: string): boolean {
    return turnsEnded.value[id] === true
  }

  // 该会话是否正在拉更早的轮次
  function isTurnsLoading(id: string): boolean {
    return turnsLoading.value[id] === true
  }

  return {
    isHistoryLoaded,
    hasPendingStart,
    markHistoryLoaded,
    loadHistory,
    loadMoreHistory,
    isTurnsEnded,
    isTurnsLoading,
  }
}
