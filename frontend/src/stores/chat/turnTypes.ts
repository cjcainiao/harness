export type TurnStatus = 'streaming' | 'completed' | 'failed' | 'interrupted'
export type TurnFeedback = 'up' | 'down'
/** 输入区提示用的流式阶段 */
export type StreamPhase = 'idle' | 'waiting' | 'tool' | 'streaming' | 'compacting'

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

export type ImageAspectRatio = '1:1' | '16:9' | '9:16'

/** 生成中的图片占位 */
export interface GeneratingImageItem extends DelegationMarks {
  id: number
  type: 'image'
  status: 'generating'
  toolCallId: string
  aspectRatio: ImageAspectRatio
}

/** 已生成的图片 */
export interface ReadyImageItem extends DelegationMarks {
  id: number
  type: 'image'
  status: 'ready'
  toolCallId?: string
  imageId: string
  mimeType: string
  width: number
  height: number
}

export type ImageItem = GeneratingImageItem | ReadyImageItem

/** 本轮失败时的提示内容 */
export interface ErrorItem extends DelegationMarks {
  id: number
  type: 'error'
  content: string
}

export interface KnowledgeSourcesItem extends DelegationMarks {
  id: number
  type: 'knowledge_sources'
  sources: import('@/api/knowledge').KnowledgeSource[]
}

/** 上下文压缩段 */
export interface CompactionItem extends DelegationMarks {
  id: number
  type: 'compaction'
  status: 'running' | 'success' | 'skipped' | 'error'
  startedAt?: number
  durationMs?: number
}

export type TurnItem =
  | MessageChunkItem
  | ReasoningItem
  | ToolItem
  | ImageItem
  | KnowledgeSourcesItem
  | CompactionItem
  | ErrorItem

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
  // 当前是否正在压缩上下文
  compacting: boolean
  // 当前压缩段序号
  activeCompactionItemId: number | null
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
    compacting: false,
    activeCompactionItemId: null,
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
  downloadUrl?: string
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
