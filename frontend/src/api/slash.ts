// 斜杠菜单接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

/** 斜杠命令菜单项 */
export interface SlashCommandItem {
  name: string
  label: string
  description: string
  icon_key: string
}

/** 查询当前层级的斜杠菜单 */
export async function fetchSlashMenu(
  command: string | null,
  query: string,
  signal?: AbortSignal,
): Promise<SlashCommandItem[]> {
  const result = await requestUtil.get<ApiResult<SlashCommandItem[]>>('/api/chat/slash', {
    params:
      command || query ? { command: command ?? undefined, query: query || undefined } : undefined,
    signal,
  })

  if (result.code !== 200) {
    throw new Error(result.message || '获取斜杠命令失败')
  }
  return result.data ?? []
}
