<template>
  <div class="user-message">
    <div v-if="attachments.length" class="attachment-list" role="list" aria-label="消息附件">
      <div
        v-for="attachment in attachments"
        :key="attachment.id"
        class="attachment-card"
        role="listitem"
        :title="attachment.name"
      >
        <img
          v-if="attachment.type.startsWith('image/') && attachment.previewUrl"
          class="attachment-preview"
          :src="attachment.previewUrl"
          alt=""
        />
        <div v-else class="attachment-icon">
          <component :is="fileIcon(attachment)" :size="28" :stroke-width="1.5" />
        </div>
        <div class="attachment-details">
          <span class="attachment-name">{{ attachment.name }}</span>
          <span class="attachment-size">{{ formatSize(attachment.size) }}</span>
        </div>
      </div>
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
import { Check, Copy, File, FileImage, FileSpreadsheet, FileText, Pencil } from 'lucide-vue-next'
import type { ChatAttachment } from './messageTurn'

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
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    window.clearTimeout(copiedTimer)
    copiedTimer = window.setTimeout(() => (copied.value = false), 1500)
  } catch {
    copied.value = false
  }
}

onUnmounted(() => window.clearTimeout(copiedTimer))

function fileIcon(attachment: ChatAttachment) {
  const extension = attachment.name.split('.').pop()?.toLowerCase()
  if (attachment.type.startsWith('image/')) return FileImage
  if (extension && ['xls', 'xlsx', 'csv', 'ods'].includes(extension)) return FileSpreadsheet
  if (extension && ['pdf', 'doc', 'docx', 'txt', 'md', 'rtf'].includes(extension)) return FileText
  return File
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
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
  padding-bottom: 2px;
}
.attachment-card {
  flex: 0 0 150px;
  overflow: hidden;
  border: 1px solid #e1e3e6;
  border-radius: 9px;
  background: #fff;
}
.attachment-preview,
.attachment-icon {
  display: block;
  width: 100%;
  height: 88px;
}
.attachment-preview {
  object-fit: cover;
}
.attachment-icon {
  display: grid;
  place-items: center;
  background: #f8f9fa;
  color: #757d86;
}
.attachment-details {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  font-size: 11px;
}
.attachment-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-size {
  flex: none;
  margin-left: auto;
  color: #9299a1;
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
