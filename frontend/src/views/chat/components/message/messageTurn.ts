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

export interface ToolItem {
  id: number
  type: 'tool'
  tool: string
  status: 'preparing' | 'running' | 'success' | 'error'
  arguments?: unknown
  output?: unknown
  durationMs?: number
  toolCallId?: string
}

export type TurnItem = MessageChunkItem | ToolItem

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
