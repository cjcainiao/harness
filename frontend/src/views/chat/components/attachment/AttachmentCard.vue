<!--附件卡片-->
<template>
  <div class="attachment-card" role="listitem" :title="name" :aria-busy="uploading">
    <img
      v-if="previewUrl"
      class="attachment-thumb"
      :src="previewUrl"
      :alt="`${name} 的缩略图`"
      role="button"
      tabindex="0"
      draggable="false"
      :aria-label="`放大预览 ${name}`"
      @click="previewOpen = true"
      @keydown.enter.prevent="previewOpen = true"
      @keydown.space.prevent="previewOpen = true"
    />
    <!-- 非图片附件用按扩展名匹配的图标素材 -->
    <img
      v-else
      class="attachment-icon"
      :src="resolveFileIconUrl(name)"
      :alt="`${name} 的类型图标`"
    />
    <div class="attachment-info">
      <a
        v-if="downloadUrl && !previewUrl"
        class="attachment-name attachment-name-link"
        :href="downloadUrl"
        :aria-label="`下载 ${name}`"
      >{{ name }}</a>
      <span v-else class="attachment-name">{{ name }}</span>
      <span v-if="size !== undefined" class="attachment-size">{{ formatSize(size) }}</span>
    </div>
    <!-- 上传中遮罩：灰黑铺满卡片，顺时针擦除 -->
    <span v-if="sweep" class="attachment-sweep" aria-hidden="true" />
    <span v-if="uploading" class="attachment-uploading" aria-label="上传中">
      <LoaderCircle :size="16" aria-hidden="true" />
      上传中
    </span>
    <button
      v-if="removable"
      class="attachment-remove"
      type="button"
      :aria-label="`移除文件 ${name}`"
      @click="emit('remove')"
    >
      <X :size="14" aria-hidden="true" />
    </button>
    <ImagePreview
      :src="previewOpen ? (previewUrl ?? null) : null"
      :alt="name"
      @close="previewOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { LoaderCircle, X } from 'lucide-vue-next'
import { ref } from 'vue'
import ImagePreview from '@/components/ImagePreview.vue'
import { resolveFileIconUrl } from '@/utils/fileIconUtil'

withDefaults(
  defineProps<{
    /** 文件名 */
    name: string
    /** 图片缩略图地址，有才可点开放大 */
    previewUrl?: string | null
    /** 后端预览或下载地址 */
    downloadUrl?: string
    /** 文件字节数，传了才显示 */
    size?: number
    /** 显示移除按钮 */
    removable?: boolean
    /** 播放上传退场遮罩 */
    sweep?: boolean
    /** 上传进行中 */
    uploading?: boolean
  }>(),
  { removable: false, sweep: false },
)

const emit = defineEmits<{ remove: [] }>()

// 浮层状态留在卡片内，卡片卸载时浮层跟着消失
const previewOpen = ref(false)

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style scoped>
/* 可动画的擦除进度，配合 conic 遮罩做顺时针退场 */
@property --sweep-progress {
  syntax: '<percentage>';
  inherits: false;
  initial-value: 0%;
}
.attachment-card {
  box-sizing: border-box;
  position: relative;
  flex: 0 0 160px;
  width: 160px;
  height: 120px;
  max-width: 100%;
  border: 1px solid #d6d9de;
  border-radius: 9px;
  background: #f5f6f8;
  color: #454a50;
  font-size: 12px;
}
.attachment-card svg {
  flex-shrink: 0;
}
.attachment-thumb {
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  width: 100%;
  height: calc(100% - 26px);
  border-radius: 8px 8px 0 0;
  background: #e9ebef;
  object-fit: cover;
  cursor: zoom-in;
}
.attachment-thumb:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: -2px;
}
.attachment-icon {
  position: absolute;
  top: 21px;
  left: 50%;
  width: 52px;
  height: 52px;
  transform: translateX(-50%);
  object-fit: contain;
}
.attachment-info {
  position: absolute;
  right: 8px;
  bottom: 6px;
  left: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  line-height: 16px;
}
.attachment-name {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.attachment-size {
  flex: none;
  margin-left: auto;
  color: #9299a1;
}
.attachment-sweep {
  position: absolute;
  inset: 0;
  border-radius: 8px;
  background: rgba(32, 34, 37, 0.66);
  -webkit-mask-image: conic-gradient(
    from 0deg,
    transparent var(--sweep-progress),
    #000 var(--sweep-progress)
  );
  mask-image: conic-gradient(
    from 0deg,
    transparent var(--sweep-progress),
    #000 var(--sweep-progress)
  );
  pointer-events: none;
  animation: file-sweep-out 1.4s linear forwards;
}
.attachment-name-link {
  color: inherit;
  text-decoration: none;
}
.attachment-name-link:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
@media (hover: hover) {
  .attachment-name-link:hover {
    text-decoration: underline;
  }
}
.attachment-uploading {
  position: absolute;
  top: 6px;
  left: 6px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border-radius: 5px;
  background: rgba(32, 34, 37, 0.78);
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  pointer-events: none;
}
.attachment-uploading svg {
  animation: upload-spin 1s linear infinite;
}
@keyframes upload-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes file-sweep-out {
  from {
    --sweep-progress: 0%;
  }
  to {
    --sweep-progress: 100%;
  }
}
.attachment-remove {
  position: absolute;
  top: -9px;
  right: -8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #fff;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.attachment-remove::before {
  position: absolute;
  inset: 5px;
  border-radius: 50%;
  background: rgba(20, 24, 30, 0.78);
  content: '';
}
.attachment-remove svg {
  position: relative;
  width: 11px;
  height: 11px;
}
.attachment-remove:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 1px;
}
.attachment-remove:active::before {
  background: #111;
}
@media (hover: hover) {
  .attachment-card .attachment-remove {
    opacity: 0;
    pointer-events: none;
  }
  .attachment-card:hover .attachment-remove,
  .attachment-card .attachment-remove:focus-visible {
    opacity: 1;
    pointer-events: auto;
  }
  .attachment-remove:hover::before {
    background: #111;
  }
}
@media (any-pointer: coarse) {
  .attachment-card .attachment-remove {
    opacity: 1;
    pointer-events: auto;
  }
}
</style>
