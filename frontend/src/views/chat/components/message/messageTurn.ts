import type {
  CompactionItem,
  ErrorItem,
  ImageItem,
  KnowledgeSourcesItem,
  MessageChunkItem,
  ReasoningItem,
  ToolItem,
  TurnItem,
} from '@/stores/chat/turnTypes'

export * from '@/stores/chat/turnTypes'

/** 相邻工具合并成的一组 */
export interface ToolGroupItem {
  id: number
  type: 'tool_group'
  tools: ToolItem[]
}

/** 一次委派，卡片内每条子项单独占一行 */
export interface DelegationGroupItem {
  id: number
  type: 'delegation_group'
  // 主代理那次 task 调用
  host: ToolItem
  // 子代理产生的显示项
  parts: TurnItem[]
}

export type DisplayItem =
  | MessageChunkItem
  | ReasoningItem
  | ImageItem
  | CompactionItem
  | ErrorItem
  | KnowledgeSourcesItem
  | ToolGroupItem
  | DelegationGroupItem

// 宿主那条 task 的判据：带子代理名字、不带委派标识
function asDelegationHost(item: TurnItem): ToolItem | undefined {
  if (item.type !== 'tool') return undefined
  return item.subagent !== undefined && item.delegationId === undefined ? item : undefined
}

/** 主流程显示项转渲染分组：只合并相邻工具，委派收进卡片 */
export function groupItems(
  renderItems: TurnItem[],
  partsOf?: (host: ToolItem) => TurnItem[] | undefined,
): DisplayItem[] {
  // 有宿主才归，找不到宿主的子项照原样显示
  const hostIds = new Set(
    renderItems.flatMap((item) => {
      const host = asDelegationHost(item)
      return host?.toolCallId === undefined ? [] : [host.toolCallId]
    }),
  )
  const inlined = new Map<string, TurnItem[]>()
  for (const item of renderItems) {
    const delegationId = item.delegationId
    if (delegationId === undefined || !hostIds.has(delegationId)) continue
    const children = inlined.get(delegationId)
    if (children) children.push(item)
    else inlined.set(delegationId, [item])
  }

  const items: DisplayItem[] = []
  for (const item of renderItems) {
    const host = asDelegationHost(item)
    if (host !== undefined) {
      const children = host.toolCallId === undefined ? undefined : inlined.get(host.toolCallId)
      items.push({
        id: host.id,
        type: 'delegation_group',
        host,
        parts: partsOf?.(host) ?? children ?? [],
      })
      continue
    }
    // 已归进卡片的子项不再在顶层出现
    if (item.delegationId !== undefined && inlined.has(item.delegationId)) continue

    if (item.type !== 'tool') {
      items.push(item)
      continue
    }

    const lastItem = items[items.length - 1]
    if (lastItem?.type === 'tool_group') {
      lastItem.tools.push(item)
    } else {
      items.push({ id: item.id, type: 'tool_group', tools: [item] })
    }
  }

  return items
}
