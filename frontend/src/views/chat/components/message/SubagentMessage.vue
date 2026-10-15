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
        <details
          v-if="item.type === 'message_chunk'"
          class="delegation-response"
          :open="expandedResponses.has(item.id)"
          @toggle.stop="onResponseToggle(item.id, $event)"
        >
          <summary class="delegation-response-header">
            <LoaderCircle
              v-if="isRunning && item.id === lastPartId"
              class="delegation-response-status is-running"
              :size="13"
              aria-hidden="true"
            />
            <CircleCheck
              v-else
              class="delegation-response-status is-complete"
              :size="13"
              aria-hidden="true"
            />
            <span class="delegation-response-title">子代理回复</span>
            <span class="delegation-response-state">{{
              isRunning && item.id === lastPartId ? '生成中' : '已完成'
            }}</span>
            <span v-if="responsePreview(item.content)" class="delegation-response-preview">
              · {{ responsePreview(item.content) }}
            </span>
            <ChevronDown class="delegation-response-chevron" :size="15" aria-hidden="true" />
          </summary>
          <div v-if="expandedResponses.has(item.id)" class="delegation-response-content">
            <MessageChunk
              :content="item.content"
              :streaming="isRunning && item.id === lastPartId"
            />
          </div>
        </details>
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
        <ContextCompactionMessage v-else-if="item.type === 'compaction'" :item="item" />
        <MessageError v-else-if="item.type === 'error'" :content="item.content" />
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { ChevronDown, CircleCheck, LoaderCircle } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { formatDuration, useLiveTimer } from '@/utils/turnTimerUtil'
import ContextCompactionMessage from './ContextCompactionMessage.vue'
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
const expandedResponses = ref(new Set<number>())

// 浏览器开合 details 时同步状态，收起时不给子项建 DOM
function onToggle(event: Event): void {
  open.value = (event.target as HTMLDetailsElement).open
}

// 只在展开时渲染正文
function onResponseToggle(id: number, event: Event): void {
  if ((event.target as HTMLDetailsElement).open) {
    expandedResponses.value.add(id)
    if (isRunning.value) void scrollBody(true)
  } else {
    expandedResponses.value.delete(id)
  }
}

// 正文首行预览
function responsePreview(content: string): string {
  const firstLine = content.match(/[^\r\n]+/)?.[0] ?? ''
  return firstLine.replace(/^\s*#{1,6}\s+/, '').trim()
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
  if (part.type === 'compaction') return 0
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

/* 水波：两层同周期的正弦水面横向流动，叠出起伏 */
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

.delegation-response {
  min-width: 0;
}

.delegation-response-header {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
  min-height: 20px;
  color: #8b8b8b;
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
  list-style: none;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.delegation-response-header::-webkit-details-marker {
  display: none;
}

.delegation-response-status,
.delegation-response-title,
.delegation-response-state {
  flex: none;
}

.delegation-response-status.is-complete {
  color: #43a66d;
}

.delegation-response-status.is-running {
  color: #628fbd;
  animation: delegation-response-spin 1.4s linear infinite;
}

.delegation-response-preview {
  min-width: 0;
  overflow: hidden;
  color: #aaa;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delegation-response-chevron {
  flex: none;
  margin-left: auto;
  color: #9299a0;
  transition: transform 0.18s ease;
}

.delegation-response[open] .delegation-response-chevron {
  transform: rotate(180deg);
}

.delegation-response-content {
  min-width: 0;
  margin: 5px 0 4px 19px;
  padding: 10px 12px;
  border-radius: 5px;
  background: #f5f6f7;
  color: #34393d;
}

.delegation-response-header:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
  border-radius: 3px;
}

@keyframes delegation-response-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (any-pointer: coarse) {
  .delegation-response-header {
    min-height: 36px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .delegation-response-chevron,
  .delegation-response-status.is-running {
    animation: none;
    transition: none;
  }
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
