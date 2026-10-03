// 服务端历史还原成界面渲染用的 turn
import type { TurnInfo, TurnItemInfo, TurnUsageInfo } from '@/api/history'
import type { ChatTurn, ToolItem, TurnItem, TurnStatus, TurnUsage } from './messageTurn'

// ISO-8601 时间转时间戳
export function toTimestamp(value: string): number {
  const time = Date.parse(value)
  return Number.isNaN(time) ? Date.now() : time
}

// 恢复后只认终态，未收尾的轮次按已完成显示
function toTurnStatus(status: string): TurnStatus {
  return status === 'failed' ? 'failed' : 'completed'
}

// 未收尾的工具按失败显示，避免恢复后一直转圈
function toToolStatus(status: ToolItem['status'] | null): ToolItem['status'] {
  return status === 'success' || status === 'error' ? status : 'error'
}

// 用量字段转成界面字段名
function toUsage(usage: TurnUsageInfo | null): TurnUsage | undefined {
  if (!usage) return undefined
  return {
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    totalTokens: usage.total_tokens,
    cacheReadTokens: usage.cache_read_tokens ?? undefined,
  }
}

// 渲染段转显示项，序号即数组下标
function toTurnItem(item: TurnItemInfo, index: number): TurnItem {
  if (item.kind === 'reasoning') {
    return {
      id: index,
      type: 'reasoning',
      content: item.content ?? '',
      durationMs: item.duration_ms ?? undefined,
    }
  }
  if (item.kind === 'tool') {
    return {
      id: index,
      type: 'tool',
      tool: item.tool ?? '',
      status: toToolStatus(item.status),
      arguments: item.arguments ?? undefined,
      output: item.output ?? undefined,
      durationMs: item.duration_ms ?? undefined,
      toolCallId: item.tool_call_id ?? undefined,
    }
  }
  if (item.kind === 'error') {
    return {
      id: index,
      type: 'error',
      content: item.content ?? '',
    }
  }
  return {
    id: index,
    type: 'message_chunk',
    content: item.content ?? '',
  }
}

/** 会话内历史轮次列表转成 turn 列表 */
export function mapTurns(threadId: string, turns: TurnInfo[]): ChatTurn[] {
  return turns.map((turn) => ({
    id: turn.turn_id,
    threadId,
    question: turn.question,
    createdAt: toTimestamp(turn.created_at),
    status: toTurnStatus(turn.status),
    items: turn.items.map(toTurnItem),
    usage: toUsage(turn.usage),
  }))
}
