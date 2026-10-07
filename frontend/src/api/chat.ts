// chat 页面模块接口
import sseUtil, { type SseError } from '@/utils/sseUtil'

/** 流式对话请求体 */
export interface ChatStreamRequest {
  // 用户消息
  message: string
  // 会话标识
  thread_id?: string
  // 实际模型名称
  model_name?: string
  // 是否启用推理
  thinking_enabled?: boolean
  // 推理强度，需同时启用推理
  reasoning_effort?: string
}

/** 除消息内容与会话标识外的对话参数 */
export type ChatSendRequest = Omit<ChatStreamRequest, 'message' | 'thread_id'>

/** 单次模型响应的令牌用量 */
export interface ChatUsage {
  // 输入令牌数
  input_tokens?: number
  // 输出令牌数
  output_tokens?: number
  // 总令牌数
  total_tokens?: number
  // 输入明细
  input_token_details?: {
    // 命中缓存的输入令牌数
    cache_read?: number
  }
  // 输出明细
  output_token_details?: {
    // 推理消耗的输出令牌数
    reasoning?: number
  }
}

/** 流式事件公共字段 */
export interface ChatStreamEventBase {
  // 产生事件的图节点
  source?: string
  // 子图路径
  namespace?: string[]
}

/** 正文增量 */
export interface MessageChunkEvent extends ChatStreamEventBase {
  type: 'message_chunk'
  // 文本片段
  content: string
  // 所属消息标识，用于合并同一段正文
  message_id?: string
}

/** 推理增量 */
export interface ReasoningChunkEvent extends ChatStreamEventBase {
  type: 'reasoning_chunk'
  // 推理文本片段
  content: string
}

/** 工具调用参数增量 */
export interface ToolCallChunkEvent extends ChatStreamEventBase {
  type: 'tool_call_chunk'
  // 工具名，首个分片可能缺失
  tool?: string | null
  // 调用标识，首个分片可能缺失
  tool_call_id?: string | null
  // 并行调用序号
  index?: number | null
  // 参数文本分片
  arguments?: string | null
}

/** 工具开始执行 */
export interface ToolStartEvent extends ChatStreamEventBase {
  type: 'tool_start'
  // 工具名
  tool: string
  // 调用标识
  tool_call_id: string
  // 完整调用参数
  arguments?: unknown
}

/** 工具执行成功 */
export interface ToolResultEvent extends ChatStreamEventBase {
  type: 'tool_result'
  // 工具名
  tool: string
  // 调用标识
  tool_call_id: string
  // 执行结果，部分返回值无内容
  content?: unknown
  // 执行耗时
  duration_ms?: number
}

/** 工具执行失败 */
export interface ToolErrorEvent extends ChatStreamEventBase {
  type: 'tool_error'
  // 工具名
  tool: string
  // 调用标识
  tool_call_id: string
  // 失败结果
  content?: unknown
  // 异常兜底提示，无结果内容时给出
  message?: string
  // 执行耗时
  duration_ms?: number
}

/** 子代理委派事件，子事件字段与主代理同款 */
export interface SubagentEvent extends ChatStreamEventBase {
  type: 'subagent'
  // 委派阶段
  sub_type:
    'start' | 'message_chunk' | 'tool_start' | 'tool_result' | 'tool_error' | 'finish' | 'error'
  // 子代理名称
  subagent: string
  // 所属委派标识，即主代理那次工具调用的标识
  delegation_id: string
  // 工具名，工具类子事件才有
  tool?: string
  // 子代理自己的调用标识，工具类子事件才有
  tool_call_id?: string
  // 正文片段或工具结果，随委派阶段取其一
  content?: unknown
  // 调用参数，按字符数截断
  arguments?: string
  // 失败提示
  message?: string
  // 执行耗时
  duration_ms?: number
}

/** 令牌用量 */
export interface UsageEvent extends ChatStreamEventBase {
  type: 'usage'
  // 用量明细
  usage: ChatUsage
}

/** 本轮结束 */
export interface DoneEvent extends ChatStreamEventBase {
  type: 'done'
  // 服务端回传的会话标识
  thread_id?: string
}

/** 流内错误 */
export interface ErrorEvent extends ChatStreamEventBase {
  type: 'error'
  // 业务错误码
  code: number
  // 错误提示
  message: string
}

/** 未识别的自定义事件 */
export interface CustomStreamEvent extends ChatStreamEventBase {
  type: 'custom'
  // 自定义事件负载
  data?: unknown
}

export type ChatStreamEvent =
  | MessageChunkEvent
  | ReasoningChunkEvent
  | ToolCallChunkEvent
  | ToolStartEvent
  | ToolResultEvent
  | ToolErrorEvent
  | SubagentEvent
  | UsageEvent
  | DoneEvent
  | ErrorEvent
  | CustomStreamEvent

/** 流式对话回调 */
export interface ChatStreamHandlers {
  // 收到任一事件
  onEvent: (event: ChatStreamEvent) => void
  // 连接关闭，completed 表示是否收到结束事件
  onClose?: (completed: boolean) => void
  // 连接、解析或服务端错误
  onError?: (error: SseError) => void
  // 用于中断输出
  signal?: AbortSignal
}

// 已知事件类型
const CHAT_STREAM_EVENT_TYPES = [
  'message_chunk',
  'reasoning_chunk',
  'tool_call_chunk',
  'tool_start',
  'tool_result',
  'tool_error',
  'subagent',
  'usage',
  'done',
  'error',
  'custom',
] as const

// 过滤非对象和无法识别的事件负载
function isChatStreamEvent(value: unknown): value is ChatStreamEvent {
  const type = (value as { type?: unknown } | null)?.type
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof type === 'string' &&
    (CHAT_STREAM_EVENT_TYPES as readonly string[]).includes(type)
  )
}

/**
 * 发起一次流式对话。
 * 页面隐藏时保持连接，失败不自动重连，避免重复触发同一轮执行。
 */
export function streamChat(
  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
): Promise<void> {
  return sseUtil.request<ChatStreamRequest, ChatStreamEvent>({
    url: '/api/chat/stream',
    method: 'POST',
    data: request,
    signal: handlers.signal,
    openWhenHidden: true,
    onMessage: (message) => {
      if (isChatStreamEvent(message.data)) handlers.onEvent(message.data)
    },
    onClose: handlers.onClose,
    onError: handlers.onError,
  })
}
