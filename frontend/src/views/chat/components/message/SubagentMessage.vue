<!--子代理委派卡片-->
<template>
  <details class="delegation" :open="open" @toggle="onToggle">
    <summary class="delegation-header">
      <span
        class="delegation-avatar"
        :class="{ 'is-generating': isRunning }"
        :style="avatarStyle"
        aria-hidden="true"
      />
      <ShimmerText :active="isRunning">{{ titleText }}{{ failureTip }}</ShimmerText>
      <span v-if="timerVisible" class="delegation-timer" :class="{ 'is-live': isRunning }">
        {{ timerText }}
      </span>
    </summary>

    <div v-if="open" ref="body" class="delegation-body">
      <div v-for="item in parts" :key="item.id" class="delegation-item">
        <MessageChunk v-if="item.type === 'message_chunk'" :content="item.content" />
        <MessageReasoning
          v-else-if="item.type === 'reasoning'"
          :content="item.content"
          :started-at="item.startedAt"
          :duration-ms="item.durationMs"
          :streaming="isRunning && item.id === lastPartId"
          :expanded="isRunning"
          hide-chevron
        />
        <ToolCallItem v-else-if="item.type === 'tool'" :tool="item" />
        <MessageError v-else-if="item.type === 'error'" :content="item.content" />
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { formatDuration, useLiveTimer } from '@/utils/turnTimerUtil'
import MessageChunk from './MessageChunk.vue'
import MessageError from './MessageError.vue'
import MessageReasoning from './MessageReasoning.vue'
import ToolCallItem from './ToolCallItem.vue'
import { subagentAvatar } from './subagentAvatar'
import { isRunningTool } from './messageTurn'
import type { ToolItem, TurnItem } from './messageTurn'

const props = defineProps<{ host: ToolItem; parts: TurnItem[] }>()

// 徽标只认子代理名字，同名永远同一张
const avatar = computed(() => subagentAvatar(props.host.subagent ?? ''))
const avatarStyle = computed(() => ({ backgroundImage: `url("${avatar.value}")` }))

const lastPartId = computed(() => props.parts[props.parts.length - 1]?.id ?? -1)

// 卡片默认收起，只有点击才开
const open = ref(false)

// 浏览器开合 details 时同步状态，收起时不给子项建 DOM
function onToggle(event: Event): void {
  open.value = (event.target as HTMLDetailsElement).open
}

// 宿主那次 task 调用没收尾就算委派还在进行
const isRunning = computed(() => isRunningTool(props.host))

// 展开区是定高滚动区
const body = ref<HTMLElement | null>(null)

async function scrollBody(toBottom: boolean): Promise<void> {
  await nextTick()
  const element = body.value
  if (!element) return
  element.scrollTop = toBottom ? element.scrollHeight : 0
}

// 子项文本一直在长，用它察觉流式期间有没有新内容上屏
const bodySignature = computed(() =>
  props.parts.map((part) => `${part.id}:${part.type}:${textLength(part)}`).join('|'),
)

function textLength(part: TurnItem): number {
  if (part.type === 'tool') return typeof part.arguments === 'string' ? part.arguments.length : 0
  return part.content.length
}

// 刚打开时：执行中的贴到最新一行，历史还原停在开头
watch(open, (expanded) => {
  if (expanded) void scrollBody(isRunning.value)
})

// 执行中一直把视图推到底，历史那侧不再动它
watch(bodySignature, () => {
  if (open.value && isRunning.value) void scrollBody(true)
})

const failedCount = computed(
  () => props.parts.filter((part) => part.type === 'tool' && part.status === 'error').length,
)
const failureTip = computed(() =>
  failedCount.value === 0 ? '' : `，其中 ${failedCount.value} 次失败`,
)

// 标题按宿主的三种终态出文案，失败数另缀一句
const titleText = computed(() => {
  const name = props.host.subagent ?? ''
  if (isRunning.value) return `子 agent ${name} 正在执行`
  return props.host.status === 'error' ? `子 agent ${name} 执行失败` : `子 agent ${name} 执行完成`
})

// 执行中用本地时钟刷新整张卡片的计时
const nowTick = useLiveTimer(() => isRunning.value)

// 各段落库的耗时之和，没有起点时间戳时用它
const recordedMs = computed(() =>
  props.parts.reduce(
    (total, part) =>
      part.type === 'tool' || part.type === 'reasoning' ? total + (part.durationMs ?? 0) : total,
    0,
  ),
)

// 历史还原没有 startedAt，只能用落库的耗时，不能算成 0
const elapsedMs = computed(() => {
  if (isRunning.value && props.host.startedAt !== undefined) {
    return Math.max(0, nowTick.value - props.host.startedAt)
  }
  if (!isRunning.value && props.host.durationMs !== undefined) return props.host.durationMs
  return recordedMs.value
})

// 有起点时间戳或有耗时记录就显示，0 ms 也要显示
const timerVisible = computed(
  () =>
    props.host.startedAt !== undefined ||
    props.host.durationMs !== undefined ||
    props.parts.some(
      (part) =>
        (part.type === 'tool' || part.type === 'reasoning') && part.durationMs !== undefined,
    ),
)

const timerText = computed(() => {
  const value = formatDuration(elapsedMs.value)
  return isRunning.value ? value : `耗时 ${value}`
})
</script>

<style scoped>
.delegation {
  min-width: 0;
  color: #8b8b8b;
  --shimmer-base: #8b8b8b;
  font-size: 14px;
  line-height: 1.5;
}

.delegation-header {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 7px;
  min-height: 22px;
  cursor: pointer;
  list-style: none;
}

.delegation-header::-webkit-details-marker {
  display: none;
}

.delegation-avatar {
  position: relative;
  width: 24px;
  height: 24px;
  /* 拉伸最狠时超出表头约 2px，别裁掉 */
  z-index: 1;
  flex: none;
  overflow: hidden;
  border-radius: 50%;
  background-repeat: no-repeat;
  background-size: cover;
  /* 整颗水球跟着晃：上下浮 + 压扁拉长交替，圆圈轮廓自己在动 */
  animation: delegation-avatar-bob 2.8s ease-in-out infinite;
}

@keyframes delegation-avatar-bob {
  0%,
  100% {
    transform: translateY(0.9px) scale(1.1, 0.9);
  }
  35% {
    transform: translateY(-0.9px) scale(0.91, 1.1);
  }
  68% {
    transform: translateY(0.3px) scale(1.04, 0.96);
  }
}

/* 水波：两层同周期的正弦水面横向流动，
   深色水体垫底、亮色浪线走反方向，叠出起伏 */
.delegation-avatar::before,
.delegation-avatar::after {
  content: '';
  position: absolute;
  inset: 0;
  background-repeat: repeat-x;
  background-position: 0 -12px;
}

/* 水体：浪峰在画面中部，下方整片铺满 */
.delegation-avatar::before {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 60'><path d='M0 20 C3.3 17.5 6.7 17.5 10 20 C13.3 22.5 16.7 22.5 20 20 L20 60 L0 60 Z' fill='rgba(16,44,74,0.30)'/></svg>");
  background-size: 24px 72px;
  animation: delegation-avatar-swell 3.6s linear infinite;
}

/* 浪线：反向流动并轻微上下浮动，和水面叠出干涉 */
.delegation-avatar::after {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 60'><path d='M0 20 C3.3 17.5 6.7 17.5 10 20 C13.3 22.5 16.7 22.5 20 20' fill='none' stroke='rgba(255,255,255,0.62)' stroke-width='1.6'/></svg>");
  background-size: 24px 72px;
  animation: delegation-avatar-crest 5.2s linear infinite;
}

/* 执行中球和浪都走得更快 */
.delegation-avatar.is-generating {
  animation-duration: 1.8s;
}

.delegation-avatar.is-generating::before {
  animation-duration: 2.2s;
}

.delegation-avatar.is-generating::after {
  animation-duration: 3s;
}

@keyframes delegation-avatar-swell {
  to {
    background-position: -24px -12px;
  }
}

@keyframes delegation-avatar-crest {
  0% {
    background-position: 0 -12px;
  }
  50% {
    background-position: 24px -15px;
  }
  100% {
    background-position: 48px -12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .delegation-avatar,
  .delegation-avatar::before,
  .delegation-avatar::after {
    animation: none;
  }
}

.delegation-body {
  display: grid;
  gap: 12px;
  max-height: 260px;
  min-width: 0;
  margin: 4px 0 0 10px;
  padding: 2px 0 2px 16px;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-left: 1px solid #e1e4e5;
}

.delegation-item {
  min-width: 0;
}

.delegation-timer {
  flex: none;
  color: #628fbd;
  font-variant-numeric: tabular-nums;
  opacity: 0;
  transition: opacity 0.15s;
}

/* 结束后计时隐藏，鼠标移到标题上才显示 */
.delegation-header:hover .delegation-timer,
.delegation-timer.is-live {
  opacity: 1;
}

.delegation-timer.is-live {
  color: #a5abb1;
}

.delegation-header:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
  border-radius: 3px;
}
</style>
