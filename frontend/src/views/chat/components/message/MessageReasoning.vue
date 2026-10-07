<!--思考过程消息-->
<template>
  <details class="reasoning" :open="open" @toggle="onToggle">
    <summary class="reasoning-header">
      <span v-if="!hideChevron" class="reasoning-chevron"><ChevronDown :size="12" /></span>
      <ShimmerText :active="streaming">思考过程</ShimmerText>
      <span v-if="timerVisible" class="reasoning-timer" :class="{ 'is-live': streaming }">
        {{ timerText }}
      </span>
    </summary>

    <div ref="body" class="reasoning-body">{{ content }}</div>
  </details>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { useLiveTimer } from '@/utils/turnTimerUtil'

const props = defineProps<{
  content: string
  startedAt?: number
  durationMs?: number
  streaming: boolean
  expanded: boolean
  /** 子代理卡片内不再画折叠三角 */
  hideChevron?: boolean
}>()

// 本轮回复流式期间保持展开，结束后收起
const open = ref(props.expanded)
let toggledByUser = false

// 正文元素，流式追加时要滚动到最新一行
const body = ref<HTMLElement | null>(null)
// 距底部多少像素内算停在最新一行
const BOTTOM_EDGE_PX = 24

// 流式期间用本地时钟刷新已思考时长
const nowTick = useLiveTimer(() => props.streaming)

watch(
  () => props.expanded,
  (active) => {
    if (!toggledByUser) open.value = active
  },
)

// 追加时跟到最新一行，用户自己往上翻了就不打扰
watch(
  () => props.content,
  () => {
    const element = body.value
    if (!element || !props.streaming) return
    // 这里读到的是新增内容上屏之前的高度
    if (element.scrollHeight - element.scrollTop - element.clientHeight > BOTTOM_EDGE_PX) return
    void nextTick(() => {
      element.scrollTop = element.scrollHeight
    })
  },
)

// 这段推理结束，正文回到开头
watch(
  () => props.streaming,
  (active) => {
    if (!active && body.value) body.value.scrollTop = 0
  },
)

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
