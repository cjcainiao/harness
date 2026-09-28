<template>
  <div class="usage-bar">
    <div
      ref="contextControl"
      class="context-control"
      @mouseenter="openDetails"
      @mouseleave="scheduleClose"
      @focusin="openDetails"
      @focusout="scheduleClose"
      @keydown.esc.stop.prevent="closeDetails"
    >
      <button
        class="context-trigger"
        type="button"
        aria-label="查看上下文占用和会话 Token 用量"
        :aria-expanded="detailsOpen"
        aria-controls="context-details"
        @click="openDetails"
      >
        <span class="mini-progress" aria-hidden="true">
          <span class="mini-progress-fill" :style="{ width: `${percent}%` }" />
        </span>
        <span class="mini-percent">{{ percent }}%</span>
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
          <strong>上下文窗口</strong>
          <span>{{ percent }}%</span>
        </div>
        <p class="details-description">
          展示当前任务的上下文占用情况；压缩会摘要早期内容，需等待片刻并消耗提示积分。
        </p>
        <div
          class="details-progress"
          role="progressbar"
          :aria-valuenow="percent"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="上下文占用"
        >
          <span class="progress-system" :style="{ width: `${systemPercent}%` }" />
          <span class="progress-messages" :style="{ width: `${messagePercent}%` }" />
        </div>
        <ul class="details-breakdown">
          <li>
            <span class="breakdown-label"><i class="breakdown-dot" />系统提示词</span
            ><span>{{ formatPercent(systemPrompt) }}</span>
          </li>
          <li>
            <span class="breakdown-label"><i class="breakdown-dot" />系统工具</span
            ><span>{{ formatPercent(systemTools) }}</span>
          </li>
          <li>
            <span class="breakdown-label"
              ><i class="breakdown-dot" />Skill<span v-if="skillCount"
                >（{{ skillCount }}个）</span
              ></span
            ><span>{{ formatPercent(skills) }}</span>
          </li>
          <li>
            <span class="breakdown-label"><i class="breakdown-dot is-message" />消息</span
            ><span>{{ formatPercent(messages) }}</span>
          </li>
        </ul>
        <div class="token-summary">
          <div class="token-heading">
            <span>会话累计</span>
            <strong>{{ formatTokens(totalTokens) }} tokens</strong>
          </div>
          <div class="token-breakdown">
            <span>输入 {{ formatTokens(inputTokens) }}</span>
            <span>输出 {{ formatTokens(outputTokens) }}</span>
          </div>
        </div>
        <button class="compact-button" type="button" @click="emit('compact')">
          <NotebookText :size="13" :stroke-width="1.8" aria-hidden="true" />
          <span>压缩上下文</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NotebookText } from 'lucide-vue-next'
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

function clampPercent(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0
}

const percent = computed(() => Math.round(clampPercent(props.percentage)))
const systemPercent = computed(() =>
  Math.min(percent.value, clampPercent(props.systemPrompt + props.systemTools + props.skills)),
)
const messagePercent = computed(() =>
  Math.min(percent.value - systemPercent.value, clampPercent(props.messages)),
)
// 底部简写总量，弹层保留精确数字
const compactTotalTokens = computed(() =>
  new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
    .format(normalizeTokens(props.totalTokens))
    .toLowerCase(),
)

function formatPercent(value: number): string {
  const bounded = clampPercent(value)
  if (bounded > 0 && bounded < 1) return '<1%'
  return `${Math.round(bounded)}%`
}

function normalizeTokens(value: number): number {
  return Number.isSafeInteger(value) && value >= 0 ? value : 0
}

function formatTokens(value: number): string {
  return normalizeTokens(value).toLocaleString('en-US')
}

function openDetails(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = null
  detailsOpen.value = true
}

function closeDetails(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = null
  detailsOpen.value = false
}

// 延迟关闭，避免指针移入弹层时闪烁
function scheduleClose(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = window.setTimeout(closeDetails, 120)
}

function closeOnOutsideClick(event: PointerEvent): void {
  if (!contextControl.value?.contains(event.target as Node)) closeDetails()
}

onMounted(() => document.addEventListener('pointerdown', closeOnOutsideClick))
onUnmounted(() => {
  document.removeEventListener('pointerdown', closeOnOutsideClick)
  if (closeTimer !== null) window.clearTimeout(closeTimer)
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
  gap: 7px;
  min-height: 24px;
  padding: 3px 7px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #465049;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  line-height: 18px;
}
.context-trigger:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 3px;
}
.mini-progress {
  position: relative;
  display: block;
  width: 50px;
  height: 6px;
  overflow: hidden;
  border-radius: 2px;
  background: repeating-linear-gradient(135deg, #d7ddd8 0 2px, #f7f8f7 2px 4px);
}
.mini-progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: #466b57;
}
.mini-percent {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.usage-divider {
  width: 1px;
  height: 12px;
  margin: 0 2px;
  background: #d9dedb;
}
.token-total {
  color: #676f69;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.context-details {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 20;
  width: 296px;
  padding: 14px;
  border: 1px solid #e5e6e5;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 20px #00000017;
}
.details-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  line-height: 17px;
}
.details-heading strong {
  color: #202327;
  font-size: 14px;
  font-weight: 600;
}
.details-heading span {
  color: #59615c;
  font-size: 12px;
  font-weight: 500;
}
.details-description {
  margin: 5px 0 0;
  color: #747c76;
  font-size: 12px;
  line-height: 17px;
}
.details-progress {
  display: flex;
  height: 6px;
  margin-top: 12px;
  overflow: hidden;
  border-radius: 3px;
  background: #f1f2f1;
}
.progress-system {
  background: #466b57;
}
.progress-messages {
  background: #d5dcd8;
}
.details-breakdown {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  color: #505a53;
  font-size: 12px;
  line-height: 18px;
}
.details-breakdown li,
.breakdown-label {
  display: flex;
  align-items: center;
}
.details-breakdown li {
  justify-content: space-between;
  gap: 8px;
}
.breakdown-label {
  gap: 6px;
}
.breakdown-dot {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #466b57;
}
.breakdown-dot.is-message {
  background: #d5dcd8;
}
.token-summary {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e9ece9;
}
.token-heading,
.token-breakdown {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.token-heading {
  color: #505a53;
  font-size: 12px;
}
.token-heading strong {
  color: #202327;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.token-breakdown {
  margin-top: 5px;
  color: #747c76;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.compact-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 32px;
  margin-top: 14px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: #eeeeee;
  color: #202327;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.compact-button:hover,
.compact-button:focus-visible {
  background: #e7e7e7;
}
.compact-button:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
@media (max-width: 380px) {
  .context-details {
    width: min(296px, calc(100vw - 32px));
  }
}
</style>
