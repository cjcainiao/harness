<template>
  <div class="usage-bar">
    <div
      ref="contextControl"
      class="context-control"
      @mouseenter="scheduleOpen"
      @mouseleave="scheduleClose"
      @focusin="openDetails"
      @focusout="scheduleClose"
      @keydown.esc.stop.prevent="closeDetails"
    >
      <button
        class="context-trigger"
        type="button"
        :aria-label="`上下文窗口占用 ${usagePercent}%，会话累计 ${compactTotalTokens} tokens`"
        :aria-expanded="detailsOpen"
        :aria-controls="detailsOpen ? 'context-details' : undefined"
        @click="toggleDetails"
      >
        <span class="mini-progress" aria-hidden="true">
          <span class="mini-progress-fill" :style="{ width: `${fillPercent}%` }" />
        </span>
        <span class="mini-percent">{{ usagePercent }}%</span>
        <span class="usage-divider" aria-hidden="true" />
        <span class="token-total">{{ compactTotalTokens }} tokens</span>
      </button>

      <div
        v-if="detailsOpen"
        id="context-details"
        class="context-details"
        role="dialog"
        aria-label="上下文窗口与会话 Token 用量"
      >
        <div class="details-heading">
          <span class="details-title">上下文窗口</span>
          <span class="details-summary">{{ formatTokens(totalTokens) }} tokens</span>
        </div>
        <p class="details-description">
          展示当前任务的上下文占用情况；压缩会摘要早期内容，需等待片刻并消耗提示积分。
        </p>
        <div
          class="details-progress"
          role="progressbar"
          aria-label="上下文占用"
          :aria-valuenow="fillPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuetext="`占用 ${usagePercent}%`"
        >
          <template v-if="segments.length > 0">
            <span
              v-for="item in segments"
              :key="item.name"
              class="progress-segment"
              :style="{ width: `${item.percent}%`, backgroundColor: item.color }"
            />
          </template>
          <span v-else class="progress-segment" :style="{ width: `${fillPercent}%` }" />
        </div>
        <ul v-if="segments.length > 0" class="details-breakdown" aria-label="上下文占用构成">
          <li v-for="item in segments" :key="item.name">
            <span class="breakdown-label">
              <i class="breakdown-dot" :style="{ backgroundColor: item.color }" />
              <span class="breakdown-name">{{ item.name }}</span>
            </span>
            <span class="breakdown-value">{{ formatPercent(item.percent) }}%</span>
          </li>
        </ul>
        <p class="token-summary">
          会话累计 输入 {{ formatTokens(inputTokens) }} / 输出 {{ formatTokens(outputTokens) }}
        </p>
        <button class="compact-button" type="button" @click="emit('compact')">
          <Minimize2 :size="14" :stroke-width="1.8" aria-hidden="true" />
          <span>压缩上下文</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Minimize2 } from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    percentage?: number
    systemPrompt?: number
    systemTools?: number
    skills?: number
    skillCount?: number
    messages?: number
    inputTokens?: number
    outputTokens?: number
    totalTokens?: number
  }>(),
  {
    percentage: 0,
    systemPrompt: 0,
    systemTools: 0,
    skills: 0,
    skillCount: 0,
    messages: 0,
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  },
)
const emit = defineEmits<{ compact: [] }>()
const detailsOpen = ref(false)
const contextControl = ref<HTMLElement | null>(null)
let closeTimer: number | null = null
let openTimer: number | null = null

// 各类占用的配色，按出现顺序取用
const CATEGORY_COLORS = ['#4b6f5a', '#3a5747', '#436651', '#d5dbd8', '#f2f4f2']

interface UsageSegment {
  name: string
  percent: number
  color: string
}

function clampPercent(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0
}

const fillPercent = computed(() => Math.round(clampPercent(props.percentage)))

function formatPercent(value: number): string {
  const bounded = clampPercent(value)
  if (bounded > 0 && bounded < 1) return '<1'
  return `${Math.round(bounded)}`
}

const usagePercent = computed(() => formatPercent(props.percentage))

// 只保留有占用的分类，颜色顺位补齐
const segments = computed<UsageSegment[]>(() => {
  const source = [
    { name: '系统提示词', percent: props.systemPrompt },
    { name: '系统工具', percent: props.systemTools },
    {
      name: props.skillCount > 0 ? `Skill（${props.skillCount}个）` : 'Skill',
      percent: props.skills,
    },
    { name: '消息', percent: props.messages },
  ]
  return source
    .filter((item) => clampPercent(item.percent) > 0)
    .map((item, index) => ({
      name: item.name,
      percent: clampPercent(item.percent),
      color: CATEGORY_COLORS[index % CATEGORY_COLORS.length] ?? CATEGORY_COLORS[0]!,
    }))
})

// 底部简写总量，弹层保留精确数字
const compactTotalTokens = computed(() =>
  new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
    .format(normalizeTokens(props.totalTokens))
    .toLowerCase(),
)

function normalizeTokens(value: number): number {
  return Number.isSafeInteger(value) && value >= 0 ? value : 0
}

function formatTokens(value: number): string {
  return normalizeTokens(value).toLocaleString('en-US')
}

function clearTimers(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  if (openTimer !== null) window.clearTimeout(openTimer)
  closeTimer = null
  openTimer = null
}

function openDetails(): void {
  clearTimers()
  detailsOpen.value = true
}

function closeDetails(): void {
  clearTimers()
  detailsOpen.value = false
}

// 悬停稍延迟再展开，避免扫过误触；重新进入要取消待关闭
function scheduleOpen(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = null
  if (detailsOpen.value || openTimer !== null) return
  openTimer = window.setTimeout(() => {
    openTimer = null
    detailsOpen.value = true
  }, 150)
}

// 延迟关闭，避免指针移入弹层时闪烁
function scheduleClose(): void {
  if (openTimer !== null) window.clearTimeout(openTimer)
  openTimer = null
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = window.setTimeout(closeDetails, 120)
}

function toggleDetails(): void {
  if (detailsOpen.value) closeDetails()
  else openDetails()
}

function closeOnOutsideClick(event: PointerEvent): void {
  if (!contextControl.value?.contains(event.target as Node)) closeDetails()
}

onMounted(() => document.addEventListener('pointerdown', closeOnOutsideClick))
onUnmounted(() => {
  document.removeEventListener('pointerdown', closeOnOutsideClick)
  clearTimers()
})
</script>

<style scoped>
.usage-bar {
  display: flex;
  justify-content: flex-end;
  max-width: 980px;
  margin: 0 auto;
  padding: 5px 16px 8px;
}
.context-control {
  position: relative;
}
.context-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #838280;
  cursor: pointer;
  font-size: 10px;
  font-weight: 400;
  line-height: 1;
}
.context-trigger:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 3px;
}
/* 斜纹底 + 纯色进度，方角无圆角 */
.mini-progress {
  position: relative;
  display: block;
  box-sizing: border-box;
  flex: 0 0 auto;
  width: var(--usage-bar-width, 48px);
  height: 6px;
  overflow: hidden;
  border: 1px solid #e6e6e6;
  background-image: repeating-linear-gradient(120deg, #ddd 0 1px, transparent 1px 4px);
}
.mini-progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: #4b6f5a;
  transition: width 0.3s;
}
.mini-percent {
  min-width: 22px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.usage-divider {
  width: 1px;
  height: 10px;
  background: #e6e6e6;
}
.token-total {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.context-details {
  position: absolute;
  right: 0;
  bottom: calc(100% + 8px);
  z-index: 20;
  width: 280px;
  padding: 12px;
  border: 1px solid #e6e6e6;
  border-radius: 8px;
  background: #fff;
  box-shadow:
    0 10px 15px -3px rgb(0 0 0 / 10%),
    0 4px 6px -4px rgb(0 0 0 / 10%);
  transform-origin: bottom right;
  animation: details-in 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes details-in {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.details-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.details-title {
  color: #141414;
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
}
.details-summary {
  flex-shrink: 0;
  color: #838280;
  font-size: 11px;
  line-height: 16px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.details-description {
  margin: 2px 0 0;
  color: #838280;
  font-size: 11px;
  line-height: 16px;
}
.details-progress {
  display: flex;
  height: 4px;
  margin-top: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #f6f6f6;
}
.progress-segment {
  height: 100%;
  background: #4b6f5a;
}
.details-breakdown {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}
.details-breakdown li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  line-height: 16px;
}
.breakdown-label {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  color: #636261;
}
.breakdown-name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.breakdown-dot {
  flex: 0 0 auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.breakdown-value {
  flex-shrink: 0;
  color: #838280;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.token-summary {
  margin: 6px 0 0;
  color: #838280;
  font-size: 11px;
  line-height: 16px;
  font-variant-numeric: tabular-nums;
}
.compact-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 32px;
  margin-top: 8px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: #efefef;
  color: #141414;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}
.compact-button:hover {
  background: #e6e6e6;
}
.compact-button:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
.compact-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
/* 窄屏收窄进度条，保留百分比 */
@media (max-width: 480px) {
  .usage-bar {
    --usage-bar-width: 32px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .context-details {
    animation: none;
  }
  .mini-progress-fill {
    transition: none;
  }
}
@media (max-width: 380px) {
  .context-details {
    width: min(280px, calc(100vw - 32px));
  }
}
</style>
