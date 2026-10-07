<!--单条工具调用-->
<template>
  <details class="tool-entry">
    <summary class="tool-entry-summary">
      <CircleCheck v-if="tool.status === 'success'" class="status-icon success" :size="13" />
      <CircleX v-else-if="tool.status === 'error'" class="status-icon error" :size="13" />
      <LoaderCircle v-else-if="tool.status === 'running'" class="status-icon running" :size="13" />
      <Circle v-else class="status-icon preparing" :size="13" />
      <span class="tool-name">{{ tool.tool || '工具调用' }}</span>
      <ShimmerText class="tool-state" :active="isRunning">{{
        statusLabels[tool.status]
      }}</ShimmerText>
      <span v-if="preview" class="tool-preview">· {{ preview }}</span>
    </summary>

    <div v-if="hasDetails" class="tool-details">
      <div v-if="argText" class="tool-detail">
        <div class="detail-label">参数</div>
        <pre ref="argBody">{{ argText }}</pre>
      </div>
      <div v-if="outputText" class="tool-detail">
        <div class="detail-label">{{ tool.status === 'error' ? '错误' : '结果' }}</div>
        <pre>{{ outputText }}</pre>
      </div>
      <div v-if="tool.durationMs !== undefined" class="tool-duration">
        耗时 {{ tool.durationMs }} ms
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { Circle, CircleCheck, CircleX, LoaderCircle } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { isRunningTool } from './messageTurn'
import type { ToolItem } from './messageTurn'

const props = defineProps<{ tool: ToolItem }>()

const statusLabels = {
  preparing: '准备中',
  running: '执行中',
  success: '已完成',
  error: '失败',
} as const

// 参数区元素，流式追加时要滚动到最新一行
const argBody = ref<HTMLPreElement | null>(null)
// 是否还贴着最新一行，每条工具各自记着
let following = false
// 距底部多少像素内算停在最新一行
const BOTTOM_EDGE_PX = 24

const isRunning = computed(() => isRunningTool(props.tool))

const argText = computed(() => formatValue(props.tool.arguments))
const outputText = computed(() => formatValue(props.tool.output))

// 运行时预览参数，结束后预览结果
const preview = computed(() => {
  const value =
    props.tool.status === 'success' || props.tool.status === 'error'
      ? props.tool.output
      : props.tool.arguments
  return formatValue(value).replace(/\s+/g, ' ').trim()
})

const hasDetails = computed(() =>
  Boolean(argText.value || outputText.value || props.tool.durationMs !== undefined),
)

function formatValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2) ?? String(value)
}

// 参数流式追加时跟到最新一行，用户自己往上翻了就不打扰
watch(
  () => `${props.tool.status}:${argText.value.length}`,
  () => {
    const element = argBody.value
    if (!element) return
    if (!isRunning.value) {
      // 不再追加参数了，之前跟着走的拉回开头
      if (following) element.scrollTop = 0
      following = false
      return
    }
    following = true
    // 这里读到的是新增内容上屏之前的高度
    if (element.scrollHeight - element.scrollTop - element.clientHeight > BOTTOM_EDGE_PX) return
    void nextTick(() => {
      element.scrollTop = element.scrollHeight
    })
  },
)
</script>

<style scoped>
.tool-entry {
  min-width: 0;
}

.tool-entry-summary {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
  height: 20px;
  white-space: nowrap;
  cursor: pointer;
  list-style: none;
}

.tool-entry-summary::-webkit-details-marker {
  display: none;
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

.tool-entry-summary:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
  border-radius: 3px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
