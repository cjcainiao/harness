<template>
  <details class="tool-group" open>
    <summary class="group-header">
      <span class="group-chevron"><ChevronDown :size="12" /></span>
      <span>执行工具 {{ tools.length }} 次</span>
      <span v-if="timerVisible" class="group-timer" :class="{ 'is-live': isRunning }">
        {{ timerText }}
      </span>
    </summary>

    <div class="tool-timeline">
      <details v-for="tool in tools" :key="tool.id" class="tool-entry">
        <summary class="tool-entry-summary">
          <CircleCheck v-if="tool.status === 'success'" class="status-icon success" :size="13" />
          <CircleX v-else-if="tool.status === 'error'" class="status-icon error" :size="13" />
          <LoaderCircle
            v-else-if="tool.status === 'running'"
            class="status-icon running"
            :size="13"
          />
          <Circle v-else class="status-icon preparing" :size="13" />
          <span class="tool-name">{{ tool.tool || '工具调用' }}</span>
          <span class="tool-state">{{ statusLabels[tool.status] }}</span>
          <span v-if="preview(tool)" class="tool-preview">· {{ preview(tool) }}</span>
        </summary>

        <div v-if="hasDetails(tool)" class="tool-details">
          <div v-if="formatValue(tool.arguments)" class="tool-detail">
            <div class="detail-label">参数</div>
            <pre>{{ formatValue(tool.arguments) }}</pre>
          </div>
          <div v-if="formatValue(tool.output)" class="tool-detail">
            <div class="detail-label">{{ tool.status === 'error' ? '错误' : '结果' }}</div>
            <pre>{{ formatValue(tool.output) }}</pre>
          </div>
          <div v-if="tool.durationMs !== undefined" class="tool-duration">
            耗时 {{ tool.durationMs }} ms
          </div>
        </div>
      </details>
    </div>
  </details>
</template>

<script setup lang="ts">
import { ChevronDown, Circle, CircleCheck, CircleX, LoaderCircle } from 'lucide-vue-next'
import { computed, onUnmounted, ref, watch } from 'vue'

type ToolStatus = 'preparing' | 'running' | 'success' | 'error'

interface ToolMessageItem {
  id: number
  tool: string
  status: ToolStatus
  arguments?: unknown
  output?: unknown
  /** 工具开始执行的时间戳，用于前端自己计时 */
  startedAt?: number
  durationMs?: number
}

const props = defineProps<{ tools: ToolMessageItem[] }>()

const statusLabels: Record<ToolStatus, string> = {
  preparing: '准备中',
  running: '执行中',
  success: '已完成',
  error: '失败',
}

// 执行中用本地时钟刷新整组计时
const nowTick = ref(Date.now())
let timerId: number | null = null

function isRunningTool(tool: ToolMessageItem): boolean {
  return tool.status === 'preparing' || tool.status === 'running'
}

// 清除计时器
function stopTimer(): void {
  if (timerId === null) return
  window.clearInterval(timerId)
  timerId = null
}

const isRunning = computed(() => props.tools.some(isRunningTool))

// 整组起点：组内最早开始的工具
const groupStartedAt = computed(() => {
  const starts = props.tools
    .map((tool) => tool.startedAt)
    .filter((value): value is number => value !== undefined)
  return starts.length === 0 ? undefined : Math.min(...starts)
})

// 整组终点：组内最晚结束的工具
const groupEndedAt = computed(() => {
  const ends = props.tools
    .filter((tool) => tool.startedAt !== undefined)
    .map((tool) => (tool.startedAt as number) + (tool.durationMs ?? 0))
  return ends.length === 0 ? undefined : Math.max(...ends)
})

const elapsedMs = computed(() => {
  const start = groupStartedAt.value
  if (start === undefined) return 0
  if (isRunning.value) return Math.max(0, nowTick.value - start)
  return groupEndedAt.value === undefined ? 0 : Math.max(0, groupEndedAt.value - start)
})

const timerVisible = computed(
  () => groupStartedAt.value !== undefined && (isRunning.value || elapsedMs.value > 0),
)

watch(
  isRunning,
  (active) => {
    stopTimer()
    if (!active) return
    nowTick.value = Date.now()
    timerId = window.setInterval(() => {
      nowTick.value = Date.now()
    }, 200)
  },
  { immediate: true },
)

onUnmounted(stopTimer)

// 毫秒级显示，超过一秒换成秒
function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)}s`
}

const timerText = computed(() => {
  const value = formatDuration(elapsedMs.value)
  return isRunning.value ? value : `耗时 ${value}`
})

function formatValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2) ?? String(value)
}

// 运行时预览参数，结束后预览结果
function preview(tool: ToolMessageItem): string {
  const value = tool.status === 'success' || tool.status === 'error' ? tool.output : tool.arguments
  return formatValue(value).replace(/\s+/g, ' ').trim()
}

function hasDetails(tool: ToolMessageItem): boolean {
  return Boolean(
    formatValue(tool.arguments) || formatValue(tool.output) || tool.durationMs !== undefined,
  )
}
</script>

<style scoped>
.tool-group {
  min-width: 0;
  color: #8b8b8b;
  font-size: 13px;
  line-height: 1.5;
}

.group-header,
.tool-entry-summary {
  display: flex;
  align-items: center;
  min-width: 0;
  cursor: pointer;
  list-style: none;
}

.group-header::-webkit-details-marker,
.tool-entry-summary::-webkit-details-marker {
  display: none;
}

.group-header {
  gap: 7px;
  min-height: 22px;
}

.group-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex: none;
  border: 1px solid #e4e4e4;
  border-radius: 6px;
  background: #fff;
  color: #7f8588;
}

.tool-group:not([open]) .group-chevron svg {
  transform: rotate(-90deg);
}

.tool-timeline {
  display: grid;
  gap: 7px;
  min-width: 0;
  margin: 4px 0 0 10px;
  padding: 2px 0 2px 16px;
  border-left: 1px solid #e1e4e5;
}

.tool-entry {
  min-width: 0;
}

.tool-entry-summary {
  gap: 6px;
  height: 20px;
  white-space: nowrap;
}

.status-icon {
  flex: none;
}

.status-icon.success {
  color: #43a66d;
}

.status-icon.error {
  color: #d86464;
}

.status-icon.running {
  color: #628fbd;
  animation: spin 1.4s linear infinite;
}

.status-icon.preparing {
  color: #aeb7bd;
}

.tool-name,
.tool-state {
  flex: none;
}

.tool-name {
  max-width: 38%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-timer {
  flex: none;
  color: #628fbd;
  font-variant-numeric: tabular-nums;
  opacity: 0;
  transition: opacity 0.15s;
}

/* 结束后计时隐藏，鼠标移到标题上才显示 */
.group-header:hover .group-timer,
.group-timer.is-live {
  opacity: 1;
}

.group-timer.is-live {
  color: #9aa0a4;
}

.tool-preview {
  min-width: 0;
  overflow: hidden;
  color: #aaa;
  text-overflow: ellipsis;
}

.tool-details {
  display: grid;
  gap: 8px;
  min-width: 0;
  margin: 5px 0 4px 19px;
  color: #858585;
}

.detail-label,
.tool-duration {
  font-size: 12px;
}

.tool-detail pre {
  max-height: 220px;
  margin: 3px 0 0;
  padding: 8px 10px;
  overflow: auto;
  border-radius: 5px;
  background: #f5f6f7;
  color: #5e6368;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.group-header:focus-visible,
.tool-entry-summary:focus-visible {
  outline: 2px solid #8ab4e0;
  outline-offset: 2px;
  border-radius: 3px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
