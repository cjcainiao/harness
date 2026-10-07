<!--工具调用消息-->
<template>
  <details class="tool-group" :open="open" @toggle="onToggle">
    <summary class="group-header">
      <span v-if="!hideChevron" class="group-chevron"><ChevronDown :size="12" /></span>
      <ShimmerText :active="isRunning">执行工具 {{ tools.length }} 次</ShimmerText>
      <span v-if="timerVisible" class="group-timer" :class="{ 'is-live': isRunning }">
        {{ timerText }}
      </span>
    </summary>

    <div class="tool-timeline">
      <ToolCallItem v-for="tool in tools" :key="tool.id" :tool="tool" />
    </div>
  </details>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { formatDuration, useLiveTimer } from '@/utils/turnTimerUtil'
import ToolCallItem from './ToolCallItem.vue'
import { isRunningTool } from './messageTurn'
import type { ToolItem } from './messageTurn'

const props = defineProps<{
  tools: ToolItem[]
  expanded: boolean
  /** 子代理卡片内不再画折叠三角 */
  hideChevron?: boolean
}>()

// 本轮回复流式期间保持展开，结束后收起
const open = ref(props.expanded)
let toggledByUser = false

watch(
  () => props.expanded,
  (active) => {
    if (!toggledByUser) open.value = active
  },
)

// 浏览器开合 details 时同步状态，用户手动开合后不再自动改
function onToggle(event: Event): void {
  const expanded = (event.target as HTMLDetailsElement).open
  if (expanded === open.value) return
  toggledByUser = true
  open.value = expanded
}

const isRunning = computed(() => props.tools.some(isRunningTool))
// 执行中用本地时钟刷新整组计时
const nowTick = useLiveTimer(() => isRunning.value)

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

// 历史还原没有起点时间戳，只能累加单次工具耗时
const restoredMs = computed(() =>
  props.tools.reduce((total, tool) => total + (tool.durationMs ?? 0), 0),
)

const elapsedMs = computed(() => {
  const start = groupStartedAt.value
  if (start === undefined) return restoredMs.value
  if (isRunning.value) return Math.max(0, nowTick.value - start)
  return groupEndedAt.value === undefined ? 0 : Math.max(0, groupEndedAt.value - start)
})

// 有起点时间戳或有耗时记录就显示，0 ms 也要显示
const timerVisible = computed(
  () =>
    groupStartedAt.value !== undefined || props.tools.some((tool) => tool.durationMs !== undefined),
)

const timerText = computed(() => {
  const value = formatDuration(elapsedMs.value)
  return isRunning.value ? value : `耗时 ${value}`
})
</script>

<style scoped>
.tool-group {
  min-width: 0;
  color: #8b8b8b;
  --shimmer-base: #8b8b8b;
  font-size: 14px;
  line-height: 1.5;
}

.group-header {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 7px;
  min-height: 22px;
  cursor: pointer;
  list-style: none;
}

.group-header::-webkit-details-marker {
  display: none;
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
  color: #a5abb1;
}

.group-header:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
  border-radius: 3px;
}
</style>
