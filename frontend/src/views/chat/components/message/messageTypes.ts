/** 消息区块的公共字段 */
interface MessageBlockBase {
  id: string
}

/** 助手正文 */
export interface TextMessageBlock extends MessageBlockBase {
  type: 'text'
  content: string
}

/** 推理内容 */
export interface ReasoningMessageBlock extends MessageBlockBase {
  type: 'reasoning'
  content: string
}

/** 工具调用 */
export interface ToolCallMessageBlock extends MessageBlockBase {
  type: 'tool_call'
  toolCallId?: string
  tool?: string
  arguments?: unknown
}

/** 其他自定义事件 */
export interface CustomMessageBlock extends MessageBlockBase {
  type: 'custom'
  eventType: string
  data: unknown
}

export type MessageBlock =
  TextMessageBlock | ReasoningMessageBlock | ToolCallMessageBlock | CustomMessageBlock

export type MessageStatus = 'streaming' | 'completed' | 'error'

/** 一轮对话的展示状态，由后端事件逐步更新 */
export interface ChatTurn {
  id: string
  prompt: string
  blocks: MessageBlock[]
  status: MessageStatus
  duration?: number
  error?: string
}
