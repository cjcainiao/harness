// 历史轮次映射
import type { TurnInfo, TurnItemInfo, TurnUsageInfo } from '@/api/history'
import { isInlineUploadImage, uploadPreviewUrl, type UploadedFileInfo } from '@/api/uploads'
import type { ChatAttachment, ChatTurn, ToolItem, TurnItem, TurnStatus, TurnUsage } from './messageTurn'

// ISO-8601 时间转时间戳
export function toTimestamp(value: string): number {
  const time = Date.parse(value)
  return Number.isNaN(time) ? Date.now() : time
}

// 附件卡片映射
export function toChatAttachments(files: UploadedFileInfo[]): ChatAttachment[] {
  return files.map((file) => {
    const url = uploadPreviewUrl(file.preview_url)
    return {
      id: file.file_id,
      name: file.name,
      type: file.mime_type,
      size: file.size,
      previewUrl: isInlineUploadImage(file.mime_type) ? url : undefined,
      downloadUrl: url,
    }
  })
}

// 历史轮次状态
function toTurnStatus(status: string): TurnStatus {
  if (status === 'completed' || status === 'failed') return status
  return 'interrupted'
}

// 历史工具状态
function toToolStatus(status: ToolItem['status'] | null): ToolItem['status'] {
  return status === 'success' || status === 'error' ? status : 'error'
}

// 用量字段映射
function toUsage(usage: TurnUsageInfo | null): TurnUsage | undefined {
  if (!usage) return undefined
  return {
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    totalTokens: usage.total_tokens,
    cacheReadTokens: usage.cache_read_tokens ?? undefined,
    reasoningTokens: usage.reasoning_tokens ?? undefined,
  }
}

// 历史渲染段映射
function toTurnItem(item: TurnItemInfo, index: number): TurnItem {
  // 委派标记
  const marks = {
    subagent: item.subagent ?? undefined,
    delegationId: item.delegation_id ?? undefined,
  }
  if (item.kind === 'reasoning') {
    return {
      id: index,
      type: 'reasoning',
      content: item.content ?? '',
      durationMs: item.duration_ms ?? undefined,
      ...marks,
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
      ...marks,
    }
  }
  if (item.kind === 'error') {
    return {
      id: index,
      type: 'error',
      content: item.content ?? '',
      ...marks,
    }
  }
  return {
    id: index,
    type: 'message_chunk',
    content: item.content ?? '',
    ...marks,
  }
}

/** 会话内历史轮次列表转成 turn 列表 */
export function mapTurns(threadId: string, turns: TurnInfo[]): ChatTurn[] {
  return turns.map((turn) => ({
    id: turn.turn_id,
    threadId,
    question: turn.question.content,
    attachments: toChatAttachments(turn.question.attachments),
    createdAt: toTimestamp(turn.created_at),
    status: toTurnStatus(turn.status),
    items: turn.items.map(toTurnItem),
    usage: toUsage(turn.usage),
  }))
}
