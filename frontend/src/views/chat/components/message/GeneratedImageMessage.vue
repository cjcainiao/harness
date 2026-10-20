<!--生成图片消息-->
<template>
  <div
    class="generated-image-message"
    :style="imageMaxWidth ? { maxWidth: imageMaxWidth } : undefined"
  >
    <button
      class="image-button"
      :class="{ 'is-placeholder': !imageLoaded }"
      type="button"
      :style="imageLoaded ? { aspectRatio: frameRatio } : undefined"
      :disabled="item.status !== 'ready' || !imageLoaded || loadError"
      :aria-label="
        loadError
          ? '图片无法加载'
          : imageLoaded && item.status === 'ready'
            ? `放大预览生成图片，${item.width}×${item.height}`
            : loadingLabel
      "
      @click="previewOpen = true"
    >
      <img
        v-if="item.status === 'ready' && !loadError"
        class="generated-image"
        :class="{ 'is-loaded': imageLoaded }"
        :src="previewUrl ?? undefined"
        :alt="`生成图片，${item.width}×${item.height}`"
        @load="imageLoaded = true"
        @error="onImageError"
      />
      <span v-if="!imageLoaded && !loadError" class="image-part__skeleton" aria-hidden="true">
        <i class="image-part__blob b1" />
        <i class="image-part__blob b2" />
        <i class="image-part__blob b3" />
      </span>
      <span v-if="!imageLoaded && !loadError" class="visually-hidden" role="status">{{
        loadingLabel
      }}</span>
      <span v-if="loadError" class="image-error">图片无法加载</span>
    </button>
    <div v-if="item.status === 'ready'" class="image-actions">
      <span>{{ item.width }} × {{ item.height }}</span>
      <a v-if="downloadUrl" :href="downloadUrl">下载图片</a>
    </div>
    <ImagePreview
      :src="previewOpen && imageLoaded && !loadError ? previewUrl : null"
      alt="生成图片"
      @close="previewOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { generatedImageDownloadUrl, generatedImagePreviewUrl } from '@/api/generatedImages'
import ImagePreview from '@/components/ImagePreview.vue'
import type { ImageItem } from './messageTurn'

const props = defineProps<{
  threadId: string
  item: ImageItem
}>()

const previewOpen = ref(false)
const loadError = ref(false)
const imageLoaded = ref(false)
const frameRatio = computed(() =>
  props.item.status === 'ready'
    ? `${props.item.width} / ${props.item.height}`
    : props.item.aspectRatio.replace(':', ' / '),
)
const imageMaxWidth = computed(() => {
  const item = props.item
  if (item.status !== 'ready' || !imageLoaded.value) return null
  return `${Math.min(420, (520 * item.width) / item.height)}px`
})
const loadingLabel = computed(() =>
  props.item.status === 'generating' ? '图片生成中…' : '图片加载中…',
)
const previewUrl = computed(() =>
  props.item.status === 'ready'
    ? generatedImagePreviewUrl(props.threadId, props.item.imageId)
    : null,
)
const downloadUrl = computed(() =>
  props.item.status === 'ready'
    ? generatedImageDownloadUrl(props.threadId, props.item.imageId)
    : null,
)

// 新图片到达时重置预览状态
watch(
  () => (props.item.status === 'ready' ? props.item.imageId : null),
  () => {
    imageLoaded.value = false
    loadError.value = false
    previewOpen.value = false
  },
)

// 预览请求失败
function onImageError(): void {
  imageLoaded.value = false
  loadError.value = true
}
</script>

<style scoped>
.generated-image-message {
  width: min(100%, 420px);
  min-width: 0;
}

.image-button {
  box-sizing: border-box;
  position: relative;
  display: block;
  width: 100%;
  max-height: 520px;
  padding: 0;
  overflow: hidden;
  border: 1px solid #d6d9de;
  border-radius: 10px;
  background: #eef0f4;
  cursor: zoom-in;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.image-button.is-placeholder {
  width: min(100%, 180px);
  height: 240px;
}

.image-button:disabled {
  cursor: default;
}

.image-button:focus-visible {
  outline: 2px solid #295fbe;
  outline-offset: 2px;
}

.generated-image {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.generated-image:not(.is-loaded) {
  visibility: hidden;
}

.image-part__skeleton {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 10px;
  background-image: linear-gradient(
    120deg,
    color-mix(in srgb, var(--el-color-primary) 8%, var(--el-bg-color)),
    color-mix(in srgb, var(--el-color-danger) 10%, var(--el-bg-color)),
    color-mix(in srgb, var(--el-color-primary) 10%, var(--el-bg-color)),
    color-mix(in srgb, var(--el-color-success) 10%, var(--el-bg-color)),
    color-mix(in srgb, var(--el-color-warning) 12%, var(--el-bg-color)),
    color-mix(in srgb, var(--el-color-primary) 8%, var(--el-bg-color))
  );
  background-size: 300% 300%;
  background-position: 0% 50%;
  animation: image-shimmer 3s ease-in-out infinite alternate;
}

.image-part__blob {
  position: absolute;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  filter: blur(40px);
  mix-blend-mode: multiply;
  opacity: 0.62;
  animation: image-blob 3s ease-in-out infinite alternate;
}

.image-part__blob.b1 {
  top: 12%;
  left: 8%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-danger) 30%, transparent) 0%,
    transparent 70%
  );
}

.image-part__blob.b2 {
  right: 0;
  bottom: 0;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-danger) 26%, transparent) 0%,
    transparent 70%
  );
  animation-delay: 1.2s;
}

.image-part__blob.b3 {
  top: 30%;
  right: 10%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-danger) 20%, transparent) 0%,
    transparent 70%
  );
  animation-delay: 2.4s;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.image-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}

.image-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-top: 7px;
  color: #666;
  font-size: 12px;
}

.image-actions a {
  color: #295fbe;
  text-decoration: none;
  touch-action: manipulation;
}

@media (hover: hover) {
  .image-actions {
    opacity: 0;
    visibility: hidden;
    transition:
      opacity 0.18s ease,
      visibility 0.18s;
  }

  .generated-image-message:hover .image-actions,
  .generated-image-message:focus-within .image-actions {
    opacity: 1;
    visibility: visible;
  }

  .image-actions a:hover {
    text-decoration: underline;
  }
}

@media (any-pointer: coarse) {
  .image-actions a {
    display: inline-flex;
    min-height: 36px;
    align-items: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .image-part__skeleton,
  .image-part__blob {
    animation: none;
  }
}

@keyframes image-shimmer {
  0% {
    background-position: 0% 50%;
  }

  100% {
    background-position: 100% 50%;
  }
}

@keyframes image-blob {
  0% {
    transform: translate(0, 0) scale(1);
  }

  50% {
    transform: translate(45px, -35px) scale(1.18);
  }

  100% {
    transform: translate(-35px, 45px) scale(0.92);
  }
}
</style>
