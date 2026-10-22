import { cancelChatTurn, createChatTurn, subscribeChatTurn } from '@/api/chat'
import type { ChatSendRequest, ChatStreamRequest } from '@/api/chat'
import type { UploadedFileInfo } from '@/api/uploads'
import type { ChatTurn, TurnRuntime } from '@/stores/chat/turnTypes'
import { createTurnRuntime } from '@/stores/chat/turnTypes'
import {
  readSessionStorage,
  removeSessionStorage,
  writeSessionStorage,
} from '@/utils/sessionStorageUtil'
import { RequestError } from '@/utils/requestUtil'
import type { Ref } from 'vue'

interface StreamTransportContext {
  activeStreams: Map<string, AbortController>
  cancelRequested: Set<string>
  turnThreads: Map<string, string>
  runtimes: Map<string, TurnRuntime>
  pendingNotice: Ref<{ threadId: string; message: string } | null>
  getTurns: (threadId: string) => ChatTurn[]
  findTurn: (turnId: string) => ChatTurn | undefined
  startTurn: (
    threadId: string,
    question: string,
    options?: { id?: string; attachments?: UploadedFileInfo[] },
  ) => string
  syncResponding: (threadId: string) => void
  bumpTick: (threadId: string) => void
  handleEvent: (event: unknown, turnId: string) => boolean
}

// 开始和重连的退避间隔
const STREAM_RETRY_INITIAL_MS = 500
const STREAM_RETRY_MAX_MS = 5000
const STREAM_RECONNECT_POLL_MS = 100

// 待服务端确认的轮次请求
const PENDING_STARTS_KEY = 'harness:pending-chat-turns'

interface PendingStart {
  turnId: string
  request: ChatStreamRequest
  cancelRequested?: boolean
}

// 读取待确认请求
export function pendingStarts(): PendingStart[] {
  const value = readSessionStorage<PendingStart[]>(PENDING_STARTS_KEY)
  return Array.isArray(value) ? value : []
}

// 保存待确认请求
function savePendingStart(turnId: string, request: ChatStreamRequest): void {
  writeSessionStorage(PENDING_STARTS_KEY, [
    ...pendingStarts().filter((entry) => entry.turnId !== turnId),
    { turnId, request },
  ])
}

// 清除已确认请求
export function clearPendingStart(turnId: string): void {
  const remaining = pendingStarts().filter((entry) => entry.turnId !== turnId)
  if (remaining.length) writeSessionStorage(PENDING_STARTS_KEY, remaining)
  else removeSessionStorage(PENDING_STARTS_KEY)
}

// 记录停止意图供刷新后恢复
function markPendingCancel(turnId: string): void {
  const entries = pendingStarts()
  const pending = entries.find((entry) => entry.turnId === turnId)
  if (pending) {
    pending.cancelRequested = true
    writeSessionStorage(PENDING_STARTS_KEY, entries)
  }
}

// 等待重试或主动中断
function waitForRetry(signal: AbortSignal, delay: number): Promise<void> {
  if (signal.aborted) return Promise.resolve()
  return new Promise((resolve) => {
    const finish = () => {
      window.clearTimeout(timer)
      signal.removeEventListener('abort', finish)
      resolve()
    }
    const timer = window.setTimeout(finish, delay)
    signal.addEventListener('abort', finish, { once: true })
  })
}

/** 管理发送、断线重连和停止请求 */
export function createChatStreamTransport(context: StreamTransportContext) {
  const {
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
  } = context

  // 订阅轮次进度
  async function runChatTurn(turnId: string, request?: ChatStreamRequest): Promise<void> {
    if (activeStreams.has(turnId)) return
    const controller = new AbortController()
    activeStreams.set(turnId, controller)
    try {
      if (request) {
        let delay = STREAM_RETRY_INITIAL_MS
        while (!controller.signal.aborted || cancelRequested.has(turnId)) {
          try {
            await createChatTurn(request)
            break
          } catch (error) {
            if (error instanceof RequestError && error.status && error.status < 500) throw error
            if (controller.signal.aborted && cancelRequested.has(turnId)) {
              await new Promise<void>((resolve) => window.setTimeout(resolve, delay))
            } else {
              await waitForRetry(controller.signal, delay)
            }
            delay = Math.min(delay * 2, STREAM_RETRY_MAX_MS)
            if (controller.signal.aborted && !cancelRequested.has(turnId)) return
          }
        }
        clearPendingStart(turnId)
      }
      if (cancelRequested.has(turnId)) {
        await cancelChatTurn(turnId)
        return
      }
      let delay = STREAM_RETRY_INITIAL_MS
      while (!controller.signal.aborted) {
        let completed = false
        try {
          await subscribeChatTurn(turnId, {
            signal: controller.signal,
            onEvent: (event) => handleEvent(event, turnId),
            onClose: (done) => {
              completed = done
            },
          })
        } catch {
          // 网络暂断后重订阅
        }
        if (completed || controller.signal.aborted) break
        await waitForRetry(controller.signal, delay)
        delay = Math.min(delay * 2, STREAM_RETRY_MAX_MS)
      }
    } catch {
      clearPendingStart(turnId)
      if (!controller.signal.aborted)
        handleEvent({ type: 'error', message: '开始对话失败' }, turnId)
    } finally {
      activeStreams.delete(turnId)
      cancelRequested.delete(turnId)
      const threadId = turnThreads.get(turnId) ?? request?.thread_id
      if (threadId) bumpTick(threadId)
    }
  }

  // 发送提问并接住回复流
  function startChatTurn(
    threadId: string,
    question: string,
    options: { attachments?: UploadedFileInfo[]; request?: ChatSendRequest } = {},
  ): string {
    const turnId = startTurn(threadId, question, options)
    const request: ChatStreamRequest = {
      ...options.request,
      message: question,
      thread_id: threadId,
      turn_id: turnId,
      attachments: options.attachments ?? [],
    }
    savePendingStart(turnId, request)
    void runChatTurn(turnId, request)
    return turnId
  }

  // 中断该会话未完成的回复
  function stopThreadTurns(threadId: string): void {
    for (const turn of getTurns(threadId)) {
      if (turn.status !== 'streaming') continue
      cancelRequested.add(turn.id)
      markPendingCancel(turn.id)
      void cancelChatTurn(turn.id).catch(() => {
        if (pendingStarts().some((entry) => entry.turnId === turn.id)) return
        const current = findTurn(turn.id)
        if (!current || current.status !== 'interrupted') return
        current.status = 'streaming'
        cancelRequested.delete(turn.id)
        syncResponding(threadId)
        pendingNotice.value = { threadId, message: '停止失败，回复仍在后台进行' }
        const reconnect = () => {
          if (!findTurn(turn.id)) return
          if (activeStreams.has(turn.id)) {
            window.setTimeout(reconnect, STREAM_RECONNECT_POLL_MS)
          } else {
            void runChatTurn(turn.id)
          }
        }
        reconnect()
      })
      activeStreams.get(turn.id)?.abort()
      if (!runtimes.has(turn.id)) runtimes.set(turn.id, createTurnRuntime(turn.items))
      handleEvent({ type: 'interrupted' }, turn.id)
    }
  }

  return { runChatTurn, startChatTurn, stopThreadTurns }
}
