<!--图片预览大图层-->
<template>
  <Teleport to="body">
    <Transition name="preview-fade">
      <div
        v-if="src"
        ref="dialogRef"
        class="image-preview"
        role="dialog"
        aria-modal="true"
        :aria-label="alt || '图片预览'"
        tabindex="-1"
        @click.self="emit('close')"
        @keydown.esc="emit('close')"
      >
        <img class="preview-image" :src="src" :alt="alt || '图片预览'" draggable="false" />
        <button class="preview-close" type="button" aria-label="关闭预览" @click="emit('close')">
          <X :size="18" aria-hidden="true" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { nextTick, ref, watch } from 'vue'

const props = defineProps<{ src?: string | null; alt?: string }>()
const emit = defineEmits<{ close: [] }>()

// 打开时抢焦点，否则 Esc 收不到
const dialogRef = ref<HTMLElement | null>(null)

watch(
  () => props.src,
  async (value) => {
    if (!value) return
    await nextTick()
    dialogRef.value?.focus()
  },
)
</script>

<style scoped>
.image-preview {
  box-sizing: border-box;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 50;
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  padding: 40px 56px;
  background: rgba(12, 14, 16, 0.72);
  cursor: zoom-out;
  outline: none;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.45);
  object-fit: contain;
  cursor: default;
}

.preview-close {
  box-sizing: border-box;
  position: absolute;
  top: 18px;
  right: 18px;
  display: inline-flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
}

/* 悬停才出现圆形描边 */
.preview-close:hover,
.preview-close:focus-visible {
  border-color: rgba(255, 255, 255, 0.32);
  background: rgba(255, 255, 255, 0.24);
}

.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.15s ease;
}
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .preview-fade-enter-active,
  .preview-fade-leave-active {
    transition: none;
  }
}
</style>
