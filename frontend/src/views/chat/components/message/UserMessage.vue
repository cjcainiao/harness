<!--用户消息-->
<template>
  <div class="user-message">
    <div
      v-if="attachments.length"
      ref="attachmentListRef"
      class="attachment-list"
      :class="{ 'is-dragging': attachmentsDragging }"
      role="list"
      aria-label="消息附件"
      @pointerdown="onAttachmentsPointerDown"
      @pointermove="onAttachmentsPointerMove"
      @pointerup="onAttachmentsPointerUp"
      @pointercancel="onAttachmentsPointerUp"
    >
      <AttachmentCard
        v-for="attachment in attachments"
        :key="attachment.id"
        :name="attachment.name"
        :preview-url="attachment.previewUrl"
        :download-url="attachment.downloadUrl"
        :size="attachment.size"
      />
    </div>
    <div v-if="content" class="message-text">{{ content }}</div>
    <div class="message-actions">
      <time v-if="sentTime" :datetime="sentDateTime" class="message-time">{{ sentTime }}</time>
      <ElTooltip
        v-if="content"
        :content="copied ? '已复制' : '复制消息'"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
      >
        <button
          class="message-action"
          type="button"
          :aria-label="copied ? '已复制消息' : '复制消息'"
          @click="copyMessage"
        >
          <Check v-if="copied" :size="14" :stroke-width="1.7" aria-hidden="true" />
          <Copy v-else :size="14" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
      <ElTooltip
        v-if="content"
        content="在输入框中重新编辑"
        placement="bottom"
        effect="dark"
        :show-after="350"
        :show-arrow="true"
        :enterable="false"
        :trigger="['hover', 'focus']"
      >
        <button
          class="message-action"
          type="button"
          aria-label="在输入框中重新编辑"
          @click="emit('edit', content)"
        >
          <Pencil :size="14" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElTooltip } from 'element-plus'
import 'element-plus/es/components/tooltip/style/css'
import { computed, onUnmounted, ref } from 'vue'
import { Check, Copy, Pencil } from 'lucide-vue-next'
import type { ChatAttachment } from './messageTurn'
import { useDragScroll } from '@/utils/dragScrollUtil'
import { copyToClipboard } from '@/utils/clipboardUtil'
import AttachmentCard from '@/views/chat/components/attachment/AttachmentCard.vue'

// 附件条只占一排，超出用横向拖动滚动，触屏交给原生滑动
const {
  scrollRef: attachmentListRef,
  isDragging: attachmentsDragging,
  onPointerDown: onAttachmentsPointerDown,
  onPointerMove: onAttachmentsPointerMove,
  onPointerUp: onAttachmentsPointerUp,
} = useDragScroll()

// 显示当前 turn 的用户文字和附件
const props = withDefaults(
  defineProps<{ content: string; attachments?: ChatAttachment[]; createdAt?: number }>(),
  {
    attachments: () => [],
  },
)
const emit = defineEmits<{ edit: [content: string] }>()
const copied = ref(false)
let copiedTimer: number | undefined

const sentDate = computed(() => {
  if (props.createdAt === undefined || !Number.isFinite(props.createdAt)) return null
  const date = new Date(props.createdAt)
  return Number.isNaN(date.getTime()) ? null : date
})
const sentTime = computed(() => {
  const date = sentDate.value
  if (!date) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
})
const sentDateTime = computed(() => sentDate.value?.toISOString())

// 复制成功后短暂显示确认状态
async function copyMessage(): Promise<void> {
  copied.value = await copyToClipboard(props.content)
  if (!copied.value) return
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = false), 1500)
}

onUnmounted(() => window.clearTimeout(copiedTimer))
</script>

<style scoped>
.user-message {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  min-width: 0;
  color: #242629;
}
.message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 20px;
  margin-top: -6px;
  padding-right: 2px;
  color: #92979e;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}
.user-message:hover .message-actions,
.user-message:focus-within .message-actions {
  opacity: 1;
  pointer-events: auto;
}
.message-time {
  margin-right: 2px;
  font-size: 11px;
  line-height: 20px;
}
.message-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.message-action:hover {
  background: #f2f3f5;
  color: #454a50;
}
.message-action:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 1px;
}
.message-text {
  max-width: min(80%, 700px);
  padding: 10px 14px;
  border-radius: 10px;
  background: #f4f4f5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.attachment-list {
  display: flex;
  gap: 8px;
  width: max-content;
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  padding-bottom: 2px;
  scrollbar-width: none;
  cursor: grab;
}
.attachment-list::-webkit-scrollbar {
  display: none;
}
.attachment-list.is-dragging {
  cursor: grabbing;
  user-select: none;
}
@media (hover: none) {
  .message-actions {
    opacity: 1;
    pointer-events: auto;
  }
}
@media (prefers-reduced-motion: reduce) {
  .message-actions {
    transition: none;
  }
}
</style>
