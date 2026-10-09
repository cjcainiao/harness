// history 页面模块接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'
import type { UploadedFileInfo } from '@/api/uploads'

/** 渲染段类型 */
export type TurnItemKind = 'message' | 'reasoning' | 'tool' | 'error'

/** 工具执行状态 */
export type ToolStatus = 'preparing' | 'running' | 'success' | 'error'

/** 会话摘要 */
export interface ThreadInfo {
  // 会话标识
  thread_id: string
  // 会话标题
  title: string
  // 创建时间，ISO-8601 UTC
  created_at: string
  // 最后活动时间，ISO-8601 UTC
  updated_at: string
  // 会话累计输入令牌数
  input_tokens: number
  // 会话累计输出令牌数
  output_tokens: number
}

/** 会话列表翻页游标，指向已加载的最早一条 */
export interface ThreadCursor {
  // 游标会话的创建时间，用服务端返回的原始字符串
  createdAt: string
  // 游标会话标识，同一秒内区分先后
  threadId: string
}

/** 轮次渲染段 */
export interface TurnItemInfo {
  // 段类型
  kind: TurnItemKind
  // 正文、推理或失败提示文本
  content: string | null
  // 本段耗时，单位毫秒
  duration_ms: number | null
  // 工具名称
  tool: string | null
  // 工具调用标识
  tool_call_id: string | null
  // 工具状态
  status: ToolStatus | null
  // 工具入参
  arguments: Record<string, unknown> | string | null
  // 工具返回内容
  output: unknown
  // 执行这段的子代理名称，主代理的段没有
  subagent?: string | null
  // 所属委派标识，宿主那条 task 段没有
  delegation_id?: string | null
}

/** 一轮问答的令牌用量 */
export interface TurnUsageInfo {
  // 输入令牌数
  input_tokens: number
  // 输出令牌数
  output_tokens: number
  // 总令牌数
  total_tokens: number
  // 命中缓存的输入令牌数
  cache_read_tokens: number | null
  // 推理消耗的输出令牌数
  reasoning_tokens: number | null
}

/** 一轮问答 */
export interface TurnInfo {
  // 轮次标识
  turn_id: string
  // 所属会话
  thread_id: string
  // 会话内序号
  seq: number
  // 提问正文与附件
  question: { content: string; attachments: UploadedFileInfo[] }
  // 轮次状态
  status: 'streaming' | 'completed' | 'failed' | 'interrupted'
  // 提问时间，ISO-8601 UTC
  created_at: string
  // 渲染段，顺序即显示顺序
  items: TurnItemInfo[]
  // 本轮累计用量
  usage: TurnUsageInfo | null
}

/** 获取会话列表，按创建时间倒序，带游标则往前翻一页 */
export async function fetchThreads(limit = 50, cursor?: ThreadCursor): Promise<ThreadInfo[]> {
  const result = await requestUtil.get<ApiResult<ThreadInfo[]>>('/api/chat/threads', {
    params: {
      limit,
      before_created_at: cursor?.createdAt,
      before_thread_id: cursor?.threadId,
    },
  })

  if (result.code !== 200) {
    throw new Error(result.message || '获取会话列表失败')
  }
  return result.data ?? []
}

/** 获取会话内的历史轮次，取最新一页，带游标则往前翻更早的一页；会话不存在时返回 null */
export async function fetchThreadTurns(
  threadId: string,
  limit = 20,
  beforeSeq?: number,
): Promise<TurnInfo[] | null> {
  const result = await requestUtil.get<ApiResult<TurnInfo[]>>(
    `/api/chat/threads/${encodeURIComponent(threadId)}/turns`,
    { params: { limit, before_seq: beforeSeq } },
  )

  // 会话不存在按空历史处理
  if (result.code === 404) return null
  if (result.code !== 200) {
    throw new Error(result.message || '获取会话历史失败')
  }
  return result.data ?? []
}
