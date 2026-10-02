<template>
  <details class="reasoning" :open="open" @toggle="onToggle">
    <summary class="reasoning-header">
      <span class="reasoning-chevron"><ChevronDown :size="12" /></span>
      <ShimmerText :active="streaming">思考过程</ShimmerText>
      <span v-if="timerVisible" class="reasoning-timer" :class="{ 'is-live': streaming }">
        {{ timerText }}
      </span>
    </summary>

    <div class="reasoning-body">{{ content }}</div>
  </details>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import { computed, onUnmounted, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'

const props = defineProps<{
  content: string
  startedAt?: number
  durationMs?: number
  streaming: boolean
}>()

// 推理到达时自动展开，本轮回复结束后收起
const open = ref(props.streaming)
let toggledByUser = false

// 流式期间用本地时钟刷新已思考时长
const nowTick = ref(Date.now())
let timerId: number | null = null

// 清除计时器
function stopTimer(): void {
  if (timerId === null) return
  window.clearInterval(timerId)
  timerId = null
}

watch(
  () => props.streaming,
  (active) => {
    if (!toggledByUser) open.value = active

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

const elapsedMs = computed(() => {
  if (!props.streaming) return props.durationMs ?? 0
  return props.startedAt === undefined ? 0 : Math.max(0, nowTick.value - props.startedAt)
})
// 有耗时记录就显示，0 ms 也要显示
const timerVisible = computed(() => props.streaming || props.durationMs !== undefined)
const timerText = computed(() => {
  const seconds = (elapsedMs.value / 1000).toFixed(1)
  return props.streaming ? `${seconds}s` : `耗时 ${seconds}s`
})

// 浏览器开合 details 时同步状态，用户手动开合后不再自动改
function onToggle(event: Event): void {
  const expanded = (event.target as HTMLDetailsElement).open
  if (expanded === open.value) return
  toggledByUser = true
  open.value = expanded
}
</script>

<style scoped>
.reasoning {
  min-width: 0;
  color: #757b80;
  --shimmer-base: #757b80;
  font-size: 14px;
  line-height: 1.6;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 22px;
  cursor: pointer;
  list-style: none;
}

.reasoning-header::-webkit-details-marker {
  display: none;
}

.reasoning-chevron {
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

.reasoning:not([open]) .reasoning-chevron svg {
  transform: rotate(-90deg);
}

.reasoning-timer {
  flex: none;
  color: #628fbd;
  font-variant-numeric: tabular-nums;
  opacity: 0;
  transition: opacity 0.15s;
}

/* 结束后计时隐藏，鼠标移到标题上才显示 */
.reasoning-header:hover .reasoning-timer,
.reasoning-timer.is-live {
  opacity: 1;
}

.reasoning-timer.is-live {
  color: #9aa0a4;
}

.reasoning-body {
  max-height: 260px;
  min-width: 0;
  margin: 4px 0 0 10px;
  padding: 2px 0 2px 16px;
  overflow-y: auto;
  border-left: 1px solid #e1e4e5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
