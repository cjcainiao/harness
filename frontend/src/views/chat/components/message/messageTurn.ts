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

export type TurnItem = MessageChunkItem | ReasoningItem | ToolItem

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
