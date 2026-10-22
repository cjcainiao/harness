<!--PPT 页面画布-->
<template>
  <div class="canvas-stage" aria-label="当前幻灯片画布">
    <div
      ref="slideCanvas"
      class="slide-canvas"
      :aria-label="`第 ${pageNumber} 页幻灯片`"
      @click.self="emit('select', null)"
    >
      <div
        v-for="element in slide.elements"
        :key="element.id"
        class="text-element"
        :class="{ selected: element.id === selectedElementId }"
        :style="elementStyle(element)"
        role="button"
        tabindex="0"
        :aria-label="`文字：${element.text}，双击编辑`"
        @pointerdown="startDrag($event, element)"
        @pointermove="drag($event)"
        @pointerup="finishDrag($event)"
        @pointercancel="cancelDrag"
        @dblclick="emit('edit', element.id)"
        @keydown.enter="emit('edit', element.id)"
      >
        {{ element.text }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { PptSlide, PptTextElement } from '@/views/ppt/data/deckTypes'

defineProps<{ slide: PptSlide; pageNumber: number; selectedElementId: string | null }>()
const emit = defineEmits<{
  select: [id: string | null]
  move: [id: string, x: number, y: number]
  edit: [id: string]
}>()

const slideCanvas = ref<HTMLElement | null>(null)
const canvasWidth = ref(960)
const dragPosition = ref<{ id: string; x: number; y: number } | null>(null)
let dragStart: {
  id: string
  pointerId: number
  clientX: number
  clientY: number
  x: number
  y: number
  width: number
} | null = null
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (!slideCanvas.value) return
  resizeObserver = new ResizeObserver(([entry]) => {
    canvasWidth.value = entry?.contentRect.width ?? 960
  })
  resizeObserver.observe(slideCanvas.value)
})

onBeforeUnmount(() => resizeObserver?.disconnect())

function elementStyle(element: PptTextElement) {
  const position = dragPosition.value?.id === element.id ? dragPosition.value : element
  return {
    left: `${(position.x / 960) * 100}%`,
    top: `${(position.y / 540) * 100}%`,
    width: `${(element.width / 960) * 100}%`,
    fontSize: `${Math.max(5, element.fontSize * (canvasWidth.value / 960))}px`,
  }
}

function startDrag(event: PointerEvent, element: PptTextElement) {
  if (event.button !== 0) return
  emit('select', element.id)
  dragStart = {
    id: element.id,
    pointerId: event.pointerId,
    clientX: event.clientX,
    clientY: event.clientY,
    x: element.x,
    y: element.y,
    width: element.width,
  }
  const target = event.currentTarget as HTMLElement
  target.setPointerCapture(event.pointerId)
}

function drag(event: PointerEvent) {
  if (!dragStart || event.pointerId !== dragStart.pointerId || !slideCanvas.value) return
  const width = slideCanvas.value.getBoundingClientRect().width
  if (!width) return
  const scale = 960 / width
  dragPosition.value = {
    id: dragStart.id,
    x: Math.max(
      0,
      Math.min(960 - dragStart.width, dragStart.x + (event.clientX - dragStart.clientX) * scale),
    ),
    y: Math.max(0, Math.min(500, dragStart.y + (event.clientY - dragStart.clientY) * scale)),
  }
}

function finishDrag(event: PointerEvent) {
  if (!dragStart || event.pointerId !== dragStart.pointerId) return
  const position = dragPosition.value
  if (position) emit('move', position.id, position.x, position.y)
  cancelDrag()
}

function cancelDrag() {
  dragStart = null
  dragPosition.value = null
}
</script>

<style scoped>
.canvas-stage {
  display: flex;
  min-width: 0;
  min-height: 0;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 8px 24px 18px;
  background: #f1f1f1;
}

.slide-canvas {
  position: relative;
  width: min(100%, 1349px);
  aspect-ratio: 16 / 9;
  flex: none;
  overflow: hidden;
  border: 1px solid #c9c9c9;
  background: #fff;
}

.text-element {
  position: absolute;
  min-height: 24px;
  padding: 2px 4px;
  border: 1px solid transparent;
  color: #202020;
  line-height: 1.2;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  cursor: move;
  touch-action: none;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.text-element.selected,
.text-element:focus-visible {
  border-color: #b74426;
  outline: none;
}

@media (max-width: 700px) {
  .canvas-stage {
    padding: 16px;
  }
}
</style>
