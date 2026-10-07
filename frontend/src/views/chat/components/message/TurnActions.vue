<!--本轮回复操作条-->
<template>
  <div class="turn-actions" aria-label="本轮回复操作">
    <ElPopover
      placement="top-start"
      trigger="click"
      role="dialog"
      :width="220"
      :offset="8"
      :show-arrow="false"
      :persistent="false"
      :popper-style="{ padding: '12px', borderRadius: '10px' }"
    >
      <template #reference>
        <button
          class="usage-trigger"
          type="button"
          :aria-label="
            usage
              ? `本轮使用 ${formatTokens(usage.totalTokens)} Token，查看明细`
              : '查看本轮 Token 用量'
          "
        >
          <Database :size="14" :stroke-width="1.7" aria-hidden="true" />
          <span>本轮用量</span>
          <span class="usage-separator" aria-hidden="true">·</span>
          <span>{{ usage ? formatCompactTokens(usage.totalTokens) : '—' }} tok</span>
        </button>
      </template>
      <div class="token-details">
        <div class="token-heading">
          <strong>本轮 Token 用量</strong>
          <span v-if="usage">{{ formatTokens(usage.totalTokens) }}</span>
        </div>
        <template v-if="usage">
          <div class="token-row">
            <span>输入</span><span>{{ formatTokens(usage.inputTokens) }}</span>
          </div>
          <div class="token-row">
            <span>输出</span><span>{{ formatTokens(usage.outputTokens) }}</span>
          </div>
          <div v-if="usage.cacheReadTokens !== undefined" class="token-row">
            <span>缓存命中</span><span>{{ formatTokens(usage.cacheReadTokens) }}</span>
          </div>
          <div v-if="usage.reasoningTokens !== undefined" class="token-row">
            <span>推理</span><span>{{ formatTokens(usage.reasoningTokens) }}</span>
          </div>
        </template>
        <p v-else class="token-empty">暂无本轮用量数据</p>
      </div>
    </ElPopover>

    <div class="action-list" role="group" aria-label="回复操作">
      <ElTooltip
        :content="copied ? '已复制' : '复制回复'"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
        :disabled="!canHover"
      >
        <button
          class="action-button"
          :class="{ 'is-copied': copied }"
          type="button"
          :disabled="!replyText"
          :aria-label="copied ? '已复制回复' : '复制本轮回复'"
          @click="copyReply"
        >
          <Check v-if="copied" :size="17" :stroke-width="1.8" aria-hidden="true" />
          <Copy v-else :size="17" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
      <ElTooltip
        :content="feedback === 'up' ? '已赞同，点击取消' : '赞同'"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
        :disabled="!canHover"
      >
        <button
          class="action-button"
          :class="{ 'is-active': feedback === 'up' }"
          type="button"
          :aria-pressed="feedback === 'up'"
          aria-label="赞同回复"
          @click="toggleFeedback('up')"
        >
          <ThumbsUp :size="17" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
      <ElTooltip
        :content="feedback === 'down' ? '已反对，点击取消' : '反对'"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
        :disabled="!canHover"
      >
        <button
          class="action-button"
          :class="{ 'is-active': feedback === 'down' }"
          type="button"
          :aria-pressed="feedback === 'down'"
          aria-label="反对回复"
          @click="toggleFeedback('down')"
        >
          <ThumbsDown :size="17" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
      <ElTooltip
        content="从此处创建分支"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
        :disabled="!canHover"
      >
        <button
          class="action-button"
          type="button"
          aria-label="从本轮创建分支对话"
          @click="emit('fork')"
        >
          <GitFork :size="17" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Check, Copy, Database, GitFork, ThumbsDown, ThumbsUp } from 'lucide-vue-next'
import { ElPopover, ElTooltip } from 'element-plus'
import 'element-plus/es/components/popover/style/css'
import 'element-plus/es/components/tooltip/style/css'
import { computed, onUnmounted, ref } from 'vue'
import { copyToClipboard } from '@/utils/clipboardUtil'
import type { TurnFeedback, TurnItem, TurnUsage } from './messageTurn'

const props = defineProps<{ items: TurnItem[]; usage?: TurnUsage; feedback?: TurnFeedback }>()
const emit = defineEmits<{ feedback: [value: TurnFeedback | undefined]; fork: [] }>()
const copied = ref(false)
// 触屏没有悬停，气泡只会在误触时冒出来
const canHover = window.matchMedia('(hover: hover)').matches
let copiedTimer: number | undefined
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

// 工具前后的正文保持为独立段落，不复制工具参数和输出
const replyText = computed(() =>
  props.items
    .filter((item) => item.type === 'message_chunk')
    .map((item) => item.content.trim())
    .filter(Boolean)
    .join('\n\n'),
)

function formatTokens(value: number): string {
  return value.toLocaleString('en-US')
}

function formatCompactTokens(value: number): string {
  return compactFormatter.format(value)
}

function toggleFeedback(value: TurnFeedback): void {
  emit('feedback', props.feedback === value ? undefined : value)
}

async function copyReply(): Promise<void> {
  // 没复制成功就不翻成对勾，图标状态本身就是反馈
  copied.value = await copyToClipboard(replyText.value)
  if (!copied.value) return
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = false), 1500)
}

onUnmounted(() => window.clearTimeout(copiedTimer))
</script>

<style scoped>
.turn-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 7px;
  align-self: flex-start;
  color: #7d858d;
}
.usage-trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 18px;
  padding: 0 0 0 5px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.usage-separator {
  margin: 0 1px;
  color: #a5abb1;
}
.action-list {
  display: grid;
  grid-template-columns: repeat(4, 24px);
  align-items: center;
  column-gap: 14px;
}
.action-button {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  line-height: 0;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.action-button svg {
  display: block;
  width: 17px;
  height: 17px;
}
.action-button.is-copied,
.action-button.is-active {
  color: #30343a;
}
.action-button:disabled {
  opacity: 0.45;
  cursor: default;
}
.usage-trigger:focus-visible,
.action-button:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 1px;
}
.token-details {
  color: #5d646c;
  font-size: 12px;
}
.token-heading,
.token-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.token-heading {
  padding-bottom: 8px;
  border-bottom: 1px solid #eceef0;
}
.token-heading strong {
  color: #25292d;
  font-size: 12px;
  font-weight: 600;
}
.token-heading > span,
.token-row > span:last-child {
  font-variant-numeric: tabular-nums;
}
.token-row {
  margin-top: 8px;
}
.token-empty {
  margin: 10px 0 0;
  color: #8a9097;
}
@media (hover: hover) {
  .usage-trigger:hover {
    color: #454c53;
  }
  .action-button:hover {
    background: #f4f4f5;
    color: #454c53;
  }
  .action-button.is-copied:hover,
  .action-button.is-active:hover {
    background: transparent;
  }
}
/* 手指比指针粗，命中区放大到 40×40，并去掉点击时的灰色蒙版 */
@media (any-pointer: coarse) {
  .action-list {
    grid-template-columns: repeat(4, 40px);
    column-gap: 2px;
  }
  .action-button {
    width: 40px;
    height: 40px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
  .usage-trigger {
    min-height: 36px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
}
@media (prefers-reduced-motion: reduce) {
  .action-button {
    transition: none;
  }
}
</style>
