export type TurnStatus = 'streaming' | 'completed' | 'failed' | 'interrupted'
export type TurnFeedback = 'up' | 'down'
/** 输入区提示用的流式阶段 */
export type StreamPhase = 'idle' | 'waiting' | 'tool' | 'streaming'

/** 输入区提示，委派进行中要带上是谁在干活、干到哪一步 */
export interface StreamStatusInfo {
  phase: StreamPhase
  // 正在跑的子代理名称，不在委派中就没有
  subagent?: string
  // 子代理当前在跑的工具名
  tool?: string
}

/** 子代理落下的段多挂的两个标记，宿主那条只有名字 */
export interface DelegationMarks {
  // 执行这段的子代理名称
  subagent?: string
  // 所属委派标识，即主代理那次工具调用的标识
  delegationId?: string
}

export interface MessageChunkItem extends DelegationMarks {
  id: number
  type: 'message_chunk'
  content: string
  messageId?: string
}

/** 模型一次响应里连续到达的推理内容 */
export interface ReasoningItem extends DelegationMarks {
  id: number
  type: 'reasoning'
  content: string
  /** 本段推理开始到达的时间戳 */
  startedAt?: number
  /** 本段推理结束的时间差，结束后悬停才显示 */
  durationMs?: number
}

export interface ToolItem extends DelegationMarks {
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
export interface ErrorItem extends DelegationMarks {
  id: number
  type: 'error'
  content: string
}

export type TurnItem = MessageChunkItem | ReasoningItem | ToolItem | ErrorItem

/** 工具项还在跑 */
export function isRunningTool(item: ToolItem): boolean {
  return item.status === 'preparing' || item.status === 'running'
}

/** 一次委派收到的子项，形状与主代理同款 */
export interface DelegationBucket {
  // 子代理名称
  subagent: string
  // 子项列表，渲染时挂在宿主那条工具项下面
  items: TurnItem[]
  // 子项自己的定位状态，序号仍借用本轮的统一计数器
  runtime: TurnRuntime
}

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
  // 委派标识到子项桶
  delegations: Map<string, DelegationBucket>
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
    delegations: new Map(),
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
  reasoningTokens?: number
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
  MessageChunkItem | ReasoningItem | ErrorItem | ToolGroupItem | DelegationGroupItem

// 宿主那条 task 的判据：带子代理名字、不带委派标识
function asDelegationHost(item: TurnItem): ToolItem | undefined {
  if (item.type !== 'tool') return undefined
  return item.subagent !== undefined && item.delegationId === undefined ? item : undefined
}

/**
 * 主流程显示项转渲染分组：只合并相邻工具，委派收进卡片。
 * partsOf 给实时路径按委派标识取桶；还原路径的子项混在同一份列表里，按标识归拢。
 */
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
