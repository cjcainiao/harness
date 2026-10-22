import { reactive, type Ref } from 'vue'
import { mapTurnItems, toUsage } from '@/stores/chat/historyMapper'
import { createTurnRuntime, isRunningTool } from '@/stores/chat/turnTypes'
import type {
  ChatTurn,
  DelegationBucket,
  ImageAspectRatio,
  ReadyImageItem,
  ToolItem,
  TurnItem,
  TurnRuntime,
  TurnUsage,
} from '@/stores/chat/turnTypes'
import type { TurnItemInfo, TurnUsageInfo } from '@/api/history'

interface StreamEventContext {
  findTurn: (turnId: string) => ChatTurn | undefined
  runtimes: Map<string, TurnRuntime>
  addSessionTokens: (threadId: string, input: number, output: number) => void
  markUnreadWhenUnwatched: (turn: ChatTurn) => void
  syncResponding: (threadId: string) => void
  isWatched: (threadId: string) => boolean
  setFollowUpQuestions: (turnId: string, questions: string[]) => boolean
  bumpTick: (threadId: string) => void
  pendingNotice: Ref<{ threadId: string; message: string } | null>
}

interface MessageEvent {
  type: string
  [key: string]: unknown
}

function isMessageEvent(value: unknown): value is MessageEvent {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    'type' in value &&
    typeof value.type === 'string'
  )
}

// 从时间戳算经过的毫秒数
function elapsedSince(startedAt?: number): number | undefined {
  return startedAt === undefined ? undefined : Date.now() - startedAt
}

// 空串按缺失处理
function readToolIdentity(value: unknown): string | undefined {
  return typeof value === 'string' && value ? value : undefined
}

// 只接受生图工具的完整结果
function readGeneratedImage(value: unknown): Omit<ReadyImageItem, 'id'> | undefined {
  if (typeof value !== 'string') return undefined
  let parsed: unknown
  try {
    parsed = JSON.parse(value)
  } catch {
    return undefined
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return undefined
  const result = parsed as Record<string, unknown>
  if (
    typeof result.image_id !== 'string' ||
    !/^[0-9a-f]{32}$/.test(result.image_id) ||
    !['image/png', 'image/jpeg', 'image/webp'].includes(String(result.mime_type)) ||
    !Number.isSafeInteger(result.width) ||
    !Number.isSafeInteger(result.height) ||
    (result.width as number) < 1 ||
    (result.height as number) < 1
  ) {
    return undefined
  }
  return {
    type: 'image',
    status: 'ready',
    imageId: result.image_id,
    mimeType: result.mime_type as string,
    width: result.width as number,
    height: result.height as number,
  }
}

// 读取图片工具请求的画幅
function readImageAspectRatio(value: unknown): ImageAspectRatio {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return '1:1'
  const ratio = (value as Record<string, unknown>).aspect_ratio
  return ratio === '16:9' || ratio === '9:16' ? ratio : '1:1'
}

// 清理未完成的图片占位
function removeGeneratingImages(items: TurnItem[], toolCallId?: string): void {
  for (let index = items.length - 1; index >= 0; index--) {
    const item = items[index]
    if (
      item?.type === 'image' &&
      item.status === 'generating' &&
      (!toolCallId || item.toolCallId === toolCallId)
    ) {
      items.splice(index, 1)
    }
  }
}

/** 将服务端事件写入当前轮次的显示状态 */
export function createStreamEventHandler(context: StreamEventContext) {
  const {
    findTurn,
    runtimes,
    addSessionTokens,
    markUnreadWhenUnwatched,
    syncResponding,
    isWatched,
    setFollowUpQuestions,
    bumpTick,
    pendingNotice,
  } = context

  // 只合并同一正文块内的连续文字片段
  function handleMessageChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    if (typeof event.content !== 'string' || event.content.length === 0) return

    const messageId = typeof event.message_id === 'string' ? event.message_id : undefined
    const activeItem = turn.items.find((item) => item.id === runtime.activeTextItemId)
    if (
      activeItem?.type === 'message_chunk' &&
      (!messageId || activeItem.messageId === messageId)
    ) {
      activeItem.content += event.content
      return
    }

    const id = runtime.nextItemId++
    turn.items.push({
      id,
      type: 'message_chunk',
      content: event.content,
      messageId,
    })
    runtime.activeTextItemId = id
  }

  // 同一工具用调用 ID 定位；参数分片没有 ID 时用 index 定位
  function getToolItem(
    turn: ChatTurn,
    runtime: TurnRuntime,
    event: MessageEvent,
  ): ToolItem | undefined {
    const callId = readToolIdentity(event.tool_call_id)
    const toolName = readToolIdentity(event.tool)
    const index = typeof event.index === 'number' ? event.index : undefined
    if (callId === undefined && index === undefined) return undefined

    let itemId = callId === undefined ? undefined : runtime.toolItemsByCallId.get(callId)
    if (itemId === undefined && index !== undefined) {
      const indexedId = runtime.toolItemsByIndex.get(index)
      const indexedItem = turn.items.find((item) => item.id === indexedId)
      if (
        indexedItem?.type === 'tool' &&
        (callId === undefined ||
          indexedItem.toolCallId === undefined ||
          indexedItem.toolCallId === callId)
      ) {
        itemId = indexedId
      }
    }

    let item = turn.items.find((entry) => entry.id === itemId)
    if (item?.type !== 'tool') {
      // 拿到真实标识才建项
      if (callId === undefined && toolName === undefined) return undefined
      item = {
        id: runtime.nextItemId++,
        type: 'tool',
        tool: '',
        status: 'preparing',
        startedAt: Date.now(),
      }
      turn.items.push(item)
    }

    if (callId !== undefined) {
      item.toolCallId = callId
      runtime.toolItemsByCallId.set(callId, item.id)
    }
    if (index !== undefined) runtime.toolItemsByIndex.set(index, item.id)
    if (toolName !== undefined) item.tool = toolName
    return item
  }

  function handleToolCallChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item || typeof event.arguments !== 'string') return
    item.arguments = `${typeof item.arguments === 'string' ? item.arguments : ''}${event.arguments}`
  }

  function handleToolStart(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'running'
    if (event.arguments !== undefined) item.arguments = event.arguments
    const callId = item.toolCallId
    if (
      item.tool === 'generate_image' &&
      callId &&
      !turn.items.some((entry) => entry.type === 'image' && entry.toolCallId === callId)
    ) {
      turn.items.push({
        id: runtime.nextItemId++,
        type: 'image',
        status: 'generating',
        toolCallId: callId,
        aspectRatio: readImageAspectRatio(item.arguments),
      })
    }
  }

  function handleToolResult(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'success'
    if (event.content !== undefined) item.output = event.content
    if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
    else item.durationMs ??= elapsedSince(item.startedAt)
    if (item.tool === 'generate_image') {
      const image = readGeneratedImage(event.content)
      if (!image) {
        item.status = 'error'
        item.output = '图片服务返回的结果无效'
        removeGeneratingImages(turn.items, item.toolCallId)
        return
      }
      if (
        turn.items.some(
          (entry) =>
            entry.type === 'image' && entry.status === 'ready' && entry.imageId === image.imageId,
        )
      ) {
        removeGeneratingImages(turn.items, item.toolCallId)
        return
      }
      const pendingIndex = turn.items.findIndex(
        (entry) =>
          entry.type === 'image' &&
          entry.status === 'generating' &&
          entry.toolCallId === item.toolCallId,
      )
      const id = pendingIndex < 0 ? runtime.nextItemId++ : turn.items[pendingIndex]!.id
      const ready: ReadyImageItem = { id, ...image, toolCallId: item.toolCallId }
      if (pendingIndex < 0) turn.items.push(ready)
      else turn.items.splice(pendingIndex, 1, ready)
    }
  }

  function handleToolError(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const item = getToolItem(turn, runtime, event)
    if (!item) return
    item.status = 'error'
    item.output = event.content ?? event.message
    if (typeof event.duration_ms === 'number') item.durationMs = event.duration_ms
    else item.durationMs ??= elapsedSince(item.startedAt)
    if (item.tool === 'generate_image') removeGeneratingImages(turn.items, item.toolCallId)
  }

  // 一次委派一个桶，边界事件先到就先建
  function ensureBucket(
    runtime: TurnRuntime,
    delegationId: string,
    subagent: string,
  ): DelegationBucket {
    const existing = runtime.delegations.get(delegationId)
    if (existing) return existing
    // 桶要包成响应式：子项状态是原地改的，不包不会触发更新
    const bucket: DelegationBucket = {
      subagent,
      items: reactive<TurnItem[]>([]),
      runtime: createTurnRuntime(),
    }
    runtime.delegations.set(delegationId, bucket)
    return bucket
  }

  // 子代理事件收进委派桶，子项形状与主代理同款，处理函数直接复用
  function handleSubagent(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    const delegationId = readToolIdentity(event.delegation_id)
    const subagent = readToolIdentity(event.subagent)
    if (delegationId === undefined || subagent === undefined) return

    // 主代理正文不在委派期间续写
    closeMessageChunk(runtime)

    // 边界事件也标宿主，子代理名挂在宿主那条上
    const hostId = runtime.toolItemsByCallId.get(delegationId)
    const hostItem =
      hostId === undefined ? undefined : turn.items.find((item) => item.id === hostId)
    if (hostItem?.type === 'tool') hostItem.subagent = subagent

    const subType = readToolIdentity(event.sub_type)
    if (subType === 'start' || subType === 'finish' || subType === 'error') return

    const bucket = ensureBucket(runtime, delegationId, subagent)
    const scope = bucket.runtime
    // 序号仍用本轮计数器，桶内桶外的显示项不撞号
    scope.nextItemId = runtime.nextItemId
    // 子项列表当成一个轮，直接喂给同款处理函数
    const view = { items: bucket.items } as ChatTurn

    switch (subType) {
      case 'message_chunk':
        handleMessageChunk(view, scope, event)
        break
      case 'tool_start':
        closeMessageChunk(scope)
        handleToolStart(view, scope, event)
        break
      case 'tool_result':
        closeMessageChunk(scope)
        handleToolResult(view, scope, event)
        break
      case 'tool_error':
        closeMessageChunk(scope)
        handleToolError(view, scope, event)
        break
      default:
        break
    }
    runtime.nextItemId = scope.nextItemId
  }

  // 连续到达的推理片段合并进同一显示项，被正文或工具调用打断后另起一项
  function handleReasoningChunk(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    if (typeof event.content !== 'string' || event.content.length === 0) return

    const last = turn.items[turn.items.length - 1]
    if (last?.type === 'reasoning') {
      last.content += event.content
      last.durationMs = elapsedSince(last.startedAt)
      runtime.activeReasoningItemId = last.id
      return
    }

    const id = runtime.nextItemId++
    turn.items.push({
      id,
      type: 'reasoning',
      content: event.content,
      startedAt: Date.now(),
    })
    runtime.activeReasoningItemId = id
  }

  // 忽略无效 Token 计数，避免累计值出错
  function readTokenCount(value: unknown): number | null {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null
  }

  // 每次模型响应后清空工具索引，并累计本轮用量
  function handleUsage(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    runtime.toolItemsByIndex.clear()
    const usage = event.usage
    if (typeof usage !== 'object' || usage === null || Array.isArray(usage)) return

    const counts = usage as Record<string, unknown>
    const input = readTokenCount(counts.input_tokens)
    const output = readTokenCount(counts.output_tokens)
    const total = readTokenCount(counts.total_tokens)
    const inputDetails = counts.input_token_details
    const cacheRead =
      typeof inputDetails === 'object' && inputDetails !== null && !Array.isArray(inputDetails)
        ? readTokenCount((inputDetails as Record<string, unknown>).cache_read)
        : null
    const outputDetails = counts.output_token_details
    const reasoning =
      typeof outputDetails === 'object' && outputDetails !== null && !Array.isArray(outputDetails)
        ? readTokenCount((outputDetails as Record<string, unknown>).reasoning)
        : null
    if (
      input === null &&
      output === null &&
      total === null &&
      cacheRead === null &&
      reasoning === null
    ) {
      return
    }

    const previous: TurnUsage = turn.usage ?? { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
    const next: TurnUsage = {
      inputTokens: previous.inputTokens + (input ?? 0),
      outputTokens: previous.outputTokens + (output ?? 0),
      totalTokens: previous.totalTokens + (total ?? (input ?? 0) + (output ?? 0)),
      cacheReadTokens:
        cacheRead === null && previous.cacheReadTokens === undefined
          ? undefined
          : (previous.cacheReadTokens ?? 0) + (cacheRead ?? 0),
      reasoningTokens:
        reasoning === null && previous.reasoningTokens === undefined
          ? undefined
          : (previous.reasoningTokens ?? 0) + (reasoning ?? 0),
    }
    turn.usage = next
    // 会话总量只累加本次新增，翻页加载过的轮次不重复计
    addSessionTokens(
      turn.threadId,
      next.inputTokens - previous.inputTokens,
      next.outputTokens - previous.outputTokens,
    )
  }

  // 未收尾的工具按失败显示
  function closeUnfinishedTools(turn: ChatTurn, runtime: TurnRuntime): void {
    // 委派桶里的子工具也在跑，收尾要连着扫
    const itemLists = [
      turn.items,
      ...[...runtime.delegations.values()].map((bucket) => bucket.items),
    ]
    for (const items of itemLists) {
      for (const item of items) {
        if (item.type !== 'tool' || !isRunningTool(item)) continue
        item.status = 'error'
        item.durationMs ??= elapsedSince(item.startedAt)
      }
      removeGeneratingImages(items)
    }
  }

  // 结束当前正文块，下一段文字会新建显示项
  function closeMessageChunk(runtime: TurnRuntime): void {
    runtime.activeTextItemId = null
  }

  // 结束当前推理块并记录耗时，供标题悬停显示
  function closeReasoning(turn: ChatTurn, runtime: TurnRuntime): void {
    const activeId = runtime.activeReasoningItemId
    runtime.activeReasoningItemId = null
    if (activeId === null) return

    const item = turn.items.find((entry) => entry.id === activeId)
    if (item?.type === 'reasoning') item.durationMs = elapsedSince(item.startedAt)
  }

  // 完成当前上下文压缩段
  function finishCompaction(
    turn: ChatTurn,
    runtime: TurnRuntime,
    status: 'success' | 'skipped' | 'error',
    duration?: unknown,
  ): void {
    const id = runtime.activeCompactionItemId
    runtime.activeCompactionItemId = null
    runtime.compacting = false
    if (id === null) return
    const item = turn.items.find((entry) => entry.id === id)
    if (item?.type !== 'compaction') return
    item.status = status
    item.durationMs =
      typeof duration === 'number' && Number.isFinite(duration) && duration >= 0
        ? Math.round(duration)
        : elapsedSince(item.startedAt)
  }

  // 流式压缩进度落成一条可恢复的显示项
  function handleCompaction(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): boolean {
    if (event.sub_type === 'start') {
      finishCompaction(turn, runtime, 'skipped')
      const id = runtime.nextItemId++
      turn.items.push({ id, type: 'compaction', status: 'running', startedAt: Date.now() })
      runtime.activeCompactionItemId = id
      runtime.compacting = true
      return true
    }
    if (event.sub_type === 'finish') {
      finishCompaction(turn, runtime, 'success', event.duration_ms)
      return true
    }
    if (event.sub_type === 'skip' || event.sub_type === 'error') {
      finishCompaction(
        turn,
        runtime,
        event.sub_type === 'skip' ? 'skipped' : 'error',
        event.duration_ms,
      )
      return true
    }
    return false
  }

  // 结束状态写回历史，避免重开窗口后持续显示加载中
  function handleDone(turn: ChatTurn, runtime: TurnRuntime): void {
    finishCompaction(turn, runtime, 'skipped')
    turn.status = 'completed'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    syncResponding(turn.threadId)
  }

  // 主动停止或连接中断，保留已有回复但不算完成
  function handleInterrupted(turn: ChatTurn, runtime: TurnRuntime): void {
    finishCompaction(turn, runtime, 'skipped')
    turn.status = 'interrupted'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    syncResponding(turn.threadId)
  }

  function handleError(turn: ChatTurn, runtime: TurnRuntime, event: MessageEvent): void {
    finishCompaction(turn, runtime, 'error')
    const message = typeof event.message === 'string' && event.message ? event.message : '请求失败'
    turn.items.push({ id: runtime.nextItemId++, type: 'error', content: message })
    turn.status = 'failed'
    closeUnfinishedTools(turn, runtime)
    markUnreadWhenUnwatched(turn)
    // 正看着这条会话才弹提示，后台收尾只留错误段
    if (isWatched(turn.threadId)) pendingNotice.value = { threadId: turn.threadId, message }
    syncResponding(turn.threadId)
  }

  // 恢复轮次快照
  function restoreSnapshot(turn: ChatTurn, event: MessageEvent): void {
    if (!Array.isArray(event.items)) return
    const mapped = mapTurnItems(event.items as TurnItemInfo[], event.status === 'streaming')
    const mainItems: TurnItem[] = []
    const delegated = new Map<string, { subagent: string; items: TurnItem[] }>()
    for (const item of mapped) {
      if (!item.delegationId) {
        mainItems.push(item)
        continue
      }
      const bucket = delegated.get(item.delegationId) ?? {
        subagent: item.subagent ?? '',
        items: [],
      }
      bucket.items.push(item)
      delegated.set(item.delegationId, bucket)
    }
    turn.usage = toUsage((event.usage ?? null) as TurnUsageInfo | null)
    if (Array.isArray(event.questions)) {
      turn.followUpQuestions = event.questions.filter(
        (item): item is string => typeof item === 'string',
      )
    }
    if (
      event.status === 'completed' ||
      event.status === 'failed' ||
      event.status === 'interrupted'
    ) {
      turn.status = event.status
    } else {
      turn.status = 'streaming'
    }
    const runtime = createTurnRuntime(mainItems)
    runtime.nextItemId = mapped.reduce(
      (next, item) => Math.max(next, item.id + 1),
      runtime.nextItemId,
    )
    const visibleItems: TurnItem[] = []
    for (const item of mainItems) {
      visibleItems.push(item)
      if (event.status === 'streaming' && item.type === 'compaction' && item.status === 'running') {
        runtime.compacting = true
        runtime.activeCompactionItemId = item.id
      }
      if (
        event.status === 'streaming' &&
        item.type === 'tool' &&
        item.tool === 'generate_image' &&
        isRunningTool(item) &&
        item.toolCallId
      ) {
        visibleItems.push({
          id: runtime.nextItemId++,
          type: 'image',
          status: 'generating',
          toolCallId: item.toolCallId,
          aspectRatio: readImageAspectRatio(item.arguments),
        })
      }
    }
    turn.items = visibleItems
    for (const [id, bucket] of delegated) {
      runtime.delegations.set(id, {
        subagent: bucket.subagent,
        items: reactive(bucket.items),
        runtime: createTurnRuntime(bucket.items),
      })
    }
    runtimes.set(turn.id, runtime)
    syncResponding(turn.threadId)
    bumpTick(turn.threadId)
  }

  // SSE 事件按轮次标识找到所属会话再写入，后台会话照收
  function handleEvent(value: unknown, turnId: string): boolean {
    if (!isMessageEvent(value)) return false
    const turn = findTurn(turnId)
    if (turn && value.type === 'turn_snapshot') {
      restoreSnapshot(turn, value)
      return true
    }
    const runtime = turn && runtimes.get(turn.id)
    if (!turn || !runtime) return false
    // 回复完成后，仍接收同一轮的推荐和最终结束事件
    const afterAnswer = value.type === 'follow_up_questions' || value.type === 'done'
    if (turn.status !== 'streaming' && !(turn.status === 'completed' && afterAnswer)) return false

    // 除推理片段本身，其他事件都表示上一段推理已经结束
    if (value.type !== 'reasoning_chunk') closeReasoning(turn, runtime)

    switch (value.type) {
      case 'message_chunk':
        handleMessageChunk(turn, runtime, value)
        break
      case 'knowledge_sources':
        closeMessageChunk(runtime)
        if (Array.isArray(value.sources)) {
          turn.items.push({
            id: runtime.nextItemId++,
            type: 'knowledge_sources',
            sources: value.sources as import('@/api/knowledge').KnowledgeSource[],
          })
        }
        break
      case 'reasoning_chunk':
        closeMessageChunk(runtime)
        handleReasoningChunk(turn, runtime, value)
        break
      case 'tool_call_chunk':
        closeMessageChunk(runtime)
        handleToolCallChunk(turn, runtime, value)
        break
      case 'tool_start':
        closeMessageChunk(runtime)
        handleToolStart(turn, runtime, value)
        break
      case 'tool_result':
        closeMessageChunk(runtime)
        handleToolResult(turn, runtime, value)
        break
      case 'tool_error':
        closeMessageChunk(runtime)
        handleToolError(turn, runtime, value)
        break
      case 'subagent':
        closeMessageChunk(runtime)
        handleSubagent(turn, runtime, value)
        break
      case 'context_compaction':
        closeMessageChunk(runtime)
        if (!handleCompaction(turn, runtime, value)) return false
        break
      case 'usage':
        handleUsage(turn, runtime, value)
        break
      case 'follow_up_questions':
        if (
          !Array.isArray(value.questions) ||
          !value.questions.every((item) => typeof item === 'string')
        ) {
          return false
        }
        setFollowUpQuestions(turn.id, value.questions)
        break
      case 'answer_complete':
      case 'done':
        closeMessageChunk(runtime)
        if (turn.status === 'streaming') handleDone(turn, runtime)
        break
      case 'interrupted':
        closeMessageChunk(runtime)
        handleInterrupted(turn, runtime)
        break
      case 'error':
        closeMessageChunk(runtime)
        handleError(turn, runtime, value)
        break
      default:
        return false
    }

    bumpTick(turn.threadId)
    return true
  }

  return handleEvent
}
