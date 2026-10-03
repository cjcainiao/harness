export type TurnStatus = 'streaming' | 'completed' | 'failed'
export type TurnFeedback = 'up' | 'down'
/** 输入区提示用的流式阶段 */
export type StreamPhase = 'idle' | 'waiting' | 'tool' | 'streaming'

export interface MessageChunkItem {
  id: number
  type: 'message_chunk'
  content: string
  messageId?: string
}

/** 模型一次响应里连续到达的推理内容 */
export interface ReasoningItem {
  id: number
  type: 'reasoning'
  content: string
  /** 本段推理开始到达的时间戳 */
  startedAt?: number
  /** 本段推理结束的时间差，结束后悬停才显示 */
  durationMs?: number
}

export interface ToolItem {
  id: number
  type: 'tool'
  tool: string
  status: 'preparing' | 'running' | 'success' | 'error'
  arguments?: unknown
  output?: unknown
  /** 工具开始执行的时间戳，用于前端自己计时 */
  startedAt?: number
  durationMs?: number
  toolCallId?: string
}

/** 本轮失败时的提示内容 */
export interface ErrorItem {
  id: number
  type: 'error'
  content: string
}

export type TurnItem = MessageChunkItem | ReasoningItem | ToolItem | ErrorItem | ErrorItem

/** 一轮流式回复定位用的临时状态 */
export interface TurnRuntime {
  // 下一个显示项序号
  nextItemId: number
  // 正在追加的正文项序号
  activeTextItemId: number | null
  // 正在追加的推理项序号
  activeReasoningItemId: number | null
  // 调用 ID 到显示项序号
  toolItemsByCallId: Map<string, number>
  // 并行分片序号到显示项序号
  toolItemsByIndex: Map<number, number>
}

// 从已有显示项恢复序号和调用 ID 索引
export function createTurnRuntime(items: TurnItem[] = []): TurnRuntime {
  return {
    nextItemId: items.reduce((nextId, item) => Math.max(nextId, item.id + 1), 0),
    activeTextItemId: null,
    activeReasoningItemId: null,
    toolItemsByCallId: new Map(
      items.flatMap((item) =>
        item.type === 'tool' && item.toolCallId ? [[item.toolCallId, item.id] as const] : [],
      ),
    ),
    toolItemsByIndex: new Map(),
  }
}

export interface ChatAttachment {
  id: string
  name: string
  type: string
  size: number
  previewUrl?: string
}

/** 单次对话中所有模型调用的累计用量 */
export interface TurnUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  cacheReadTokens?: number
}

/** 同一个聊天窗口中的一次提问及其完整回复 */
export interface ChatTurn {
  id: string
  threadId: string
  question: string
  createdAt?: number
  attachments?: ChatAttachment[]
  status: TurnStatus
  items: TurnItem[]
  usage?: TurnUsage
  feedback?: TurnFeedback
  followUpQuestions?: string[]
}
