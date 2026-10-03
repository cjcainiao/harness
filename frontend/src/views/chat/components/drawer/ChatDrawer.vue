<!--移动端内容抽屉-->
<template>
  <Transition name="drawer-mask">
    <button
      v-if="page"
      class="drawer-mask"
      type="button"
      aria-label="关闭抽屉"
      @click="emit('close')"
    />
  </Transition>
  <Transition name="drawer">
    <section
      v-if="page"
      class="chat-drawer"
      :class="{ 'is-resizing': resizing }"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      :style="{ width: `${width}px` }"
    >
      <div
        class="drawer-resize"
        role="separator"
        aria-label="调整抽屉宽度"
        @pointerdown="startResize"
      />
      <header class="drawer-head">
        <h2 class="drawer-title">{{ title }}</h2>
        <button class="drawer-close" type="button" aria-label="关闭抽屉" @click="emit('close')">
          <X :size="16" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </header>
      <component :is="page" v-bind="pageProps" class="drawer-body" />
    </section>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Component } from 'vue'
import { X } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    page: Component | null
    title: string
    pageProps?: Record<string, unknown>
  }>(),
  { pageProps: () => ({}) },
)
const emit = defineEmits<{ close: [] }>()

// 抽屉宽度：拖左缘调整
const width = ref(520)
const resizing = ref(false)
const minWidth = 320
// 左侧消息区至少保留的宽度
const sideReserve = 260

function startResize(event: PointerEvent): void {
  const panel = (event.currentTarget as HTMLElement).parentElement
  if (!panel) return
  event.preventDefault()

  const containerWidth = panel.offsetParent?.getBoundingClientRect().width ?? window.innerWidth
  const maxWidth = Math.min(
    Math.max(minWidth, containerWidth - sideReserve),
    Math.max(minWidth, containerWidth),
  )
  const panelRight = panel.getBoundingClientRect().right
  resizing.value = true

  const move = (moveEvent: PointerEvent): void => {
    const next = panelRight - moveEvent.clientX
    width.value = Math.round(Math.min(maxWidth, Math.max(minWidth, next)))
  }
  const stop = (): void => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', stop)
    window.removeEventListener('pointercancel', stop)
    resizing.value = false
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', stop)
  window.addEventListener('pointercancel', stop)
}
</script>

<style scoped>
/* 右侧抽屉 */
.chat-drawer {
  position: absolute;
  z-index: 31;
  inset: 0 0 0 auto;
  display: flex;
  flex-direction: column;
  max-width: 100%;
  overflow: hidden;
  border-left: 1px solid #e6e8eb;
  background: #fff;
  box-shadow: -8px 0 24px rgba(20, 24, 29, 0.12);
}
.chat-drawer.is-resizing {
  user-select: none;
}
.drawer-resize {
  position: absolute;
  z-index: 1;
  inset: 0 auto 0 0;
  width: 7px;
  cursor: col-resize;
  touch-action: none;
}
.drawer-resize:hover,
.chat-drawer.is-resizing .drawer-resize {
  background: rgba(51, 105, 170, 0.16);
}
.drawer-mask {
  position: absolute;
  z-index: 30;
  inset: 0;
  padding: 0;
  border: 0;
  background: rgba(18, 22, 28, 0.3);
  cursor: pointer;
}
.drawer-head {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
  padding: 9px 10px 9px 16px;
  border-bottom: 1px solid #e6e8eb;
}
.drawer-title {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: #202327;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drawer-close {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: none;
  color: #6d757e;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}
@media (hover: hover) {
  .drawer-close:hover {
    background: #f1f3f5;
    color: #202327;
  }
}
.drawer-body {
  flex: 1;
  min-height: 0;
}
/* 抽屉从右侧滑入滑出 */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.2s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(105%);
}
.drawer-mask-enter-active,
.drawer-mask-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-mask-enter-from,
.drawer-mask-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .drawer-enter-active,
  .drawer-leave-active,
  .drawer-mask-enter-active,
  .drawer-mask-leave-active,
  .drawer-close {
    transition: none;
  }
}
</style>
