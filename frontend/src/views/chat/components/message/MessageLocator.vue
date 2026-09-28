<template>
  <div v-if="markers.length" ref="locatorRoot" class="message-locator">
    <nav
      ref="rail"
      class="locator-rail"
      aria-label="消息定位"
      @wheel="onWheel"
      @keydown="onKeydown"
      @pointerenter="onRailPointerEnter"
      @pointerleave="onRailPointerLeave"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="finishDrag"
      @pointercancel="finishDrag"
    >
      <button
        v-for="(marker, index) in markers"
        :key="marker.id"
        type="button"
        class="locator-mark"
        :class="{ active: marker.id === activeId, hovered: marker.id === previewMarker?.id }"
        :data-marker-id="marker.id"
        :aria-label="`跳转到${marker.label}`"
        :aria-current="marker.id === activeId ? 'location' : undefined"
        @pointerenter="showPreview(marker, $event)"
        @focus="showPreview(marker, $event)"
        @blur="hidePreview"
        @click="scrollToMarker(marker.id)"
      >
        <span class="locator-line" :style="{ width: `${lineWidth(index, marker)}px` }" />
      </button>
    </nav>
    <div
      v-if="previewMarker"
      class="locator-preview"
      role="tooltip"
      :style="{ top: `${previewTop}px` }"
    >
      <span>{{ previewMarker.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

interface LocatorItem {
  id: number
  label: string
}

type Marker = LocatorItem

const props = defineProps<{
  container: HTMLElement | null
  items: LocatorItem[]
}>()

const markers = ref<Marker[]>([])
const activeId = ref<number | null>(null)
const previewMarker = ref<Marker | null>(null)
const waveCenter = ref<number | null>(null)
const previewTop = ref(0)
const locatorRoot = ref<HTMLElement | null>(null)
const rail = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null
let frameId: number | null = null
let pointerOverRail: boolean = false
let dragging = false
let draggedId: number | null = null

function getTarget(id: number): HTMLElement | null {
  return props.container?.querySelector<HTMLElement>(`[data-locator-id="${id}"]`) ?? null
}

// 鼠标附近的刻度逐级变长，形成跟随鼠标的起伏
function lineWidth(index: number, marker: Marker): number {
  if (waveCenter.value === null) return marker.id === activeId.value ? 10 : 6
  const distance = Math.abs(index - waveCenter.value)
  const strength = Math.max(0, 1 - distance / 3)
  return 6 + 20 * Math.pow(strength, 1.2)
}

function updateWave(event: PointerEvent): void {
  const list = rail.value
  if (!list) return
  const position = (event.clientY - list.getBoundingClientRect().top + list.scrollTop - 5) / 10
  waveCenter.value = Math.max(0, Math.min(markers.value.length - 1, position))
}

// 刻度固定排列在中间，滚动位置只用于判断当前 turn
function updateMarkers(): void {
  const container = props.container
  if (!container) return

  const containerTop = container.getBoundingClientRect().top
  const readingPosition = container.scrollTop + Math.min(container.clientHeight * 0.25, 120)
  let currentId: number | null = null

  markers.value = props.items.flatMap((item) => {
    const target = getTarget(item.id)
    if (!target) return []

    const position = target.getBoundingClientRect().top - containerTop + container.scrollTop
    if (position <= readingPosition) currentId = item.id

    return [item]
  })

  const atBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 2
  const nextActiveId = atBottom
    ? (markers.value.at(-1)?.id ?? null)
    : (currentId ?? markers.value[0]?.id ?? null)
  if (nextActiveId !== activeId.value) {
    activeId.value = nextActiveId
    if (!pointerOverRail) void nextTick(ensureActiveVisible)
  }
}

function ensureActiveVisible(): void {
  const list = rail.value
  const button = list?.querySelector<HTMLElement>(`[data-marker-id="${activeId.value}"]`)
  if (!list || !button) return

  const top = button.getBoundingClientRect().top - list.getBoundingClientRect().top + list.scrollTop
  const bottom = top + button.offsetHeight
  if (top < list.scrollTop) list.scrollTop = top
  else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight
}

// 将连续滚动和尺寸变化合并到下一帧
function scheduleUpdate(): void {
  if (frameId !== null) return
  frameId = window.requestAnimationFrame(() => {
    frameId = null
    updateMarkers()
  })
}

function bindContainer(container: HTMLElement | null, previous?: HTMLElement | null): void {
  previous?.removeEventListener('scroll', scheduleUpdate)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (!container) return

  container.addEventListener('scroll', scheduleUpdate, { passive: true })
  resizeObserver = new ResizeObserver(scheduleUpdate)
  resizeObserver.observe(container)
  const messageList = container.querySelector('.message-list')
  if (messageList) resizeObserver.observe(messageList)
  void nextTick(scheduleUpdate)
}

function showPreviewAtElement(marker: Marker, button: HTMLElement): void {
  const root = locatorRoot.value
  if (!root) return
  const top = button.getBoundingClientRect().top - root.getBoundingClientRect().top + 5
  previewTop.value = Math.max(30, Math.min(root.clientHeight - 30, top))
  previewMarker.value = marker
}

function showPreview(marker: Marker, event: Event): void {
  if (event instanceof PointerEvent) updateWave(event)
  else waveCenter.value = markers.value.findIndex((item) => item.id === marker.id)
  showPreviewAtElement(marker, event.currentTarget as HTMLElement)
}

function hidePreview(): void {
  previewMarker.value = null
  waveCenter.value = null
}

function onRailPointerEnter(event: PointerEvent): void {
  pointerOverRail = true
  updateWave(event)
}

function onRailPointerLeave(): void {
  pointerOverRail = false
  if (!dragging) hidePreview()
}

function onWheel(event: WheelEvent): void {
  const list = rail.value
  if (!list) return
  event.preventDefault()
  hidePreview()
  if (list.scrollHeight > list.clientHeight + 1) list.scrollTop += event.deltaY
  else if (props.container) props.container.scrollTop += event.deltaY
}

function onKeydown(event: KeyboardEvent): void {
  const current = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-marker-id]')
  if (!current) return
  const index = markers.value.findIndex((marker) => marker.id === Number(current.dataset.markerId))
  if (index < 0) return

  let nextIndex = index
  if (event.key === 'ArrowUp') nextIndex = Math.max(0, index - 1)
  else if (event.key === 'ArrowDown') nextIndex = Math.min(markers.value.length - 1, index + 1)
  else if (event.key === 'Home') nextIndex = 0
  else if (event.key === 'End') nextIndex = markers.value.length - 1
  else return

  event.preventDefault()
  const next = markers.value[nextIndex]
  if (!next) return
  rail.value?.querySelector<HTMLButtonElement>(`[data-marker-id="${next.id}"]`)?.focus()
  scrollToMarker(next.id)
}

// 拖动时跳到离指针最近的可见刻度
function scrubToPointer(event: PointerEvent): void {
  const list = rail.value
  if (!list) return
  const bounds = list.getBoundingClientRect()
  const buttons = [...list.querySelectorAll<HTMLButtonElement>('[data-marker-id]')].filter(
    (button) => {
      const rect = button.getBoundingClientRect()
      return rect.bottom > bounds.top && rect.top < bounds.bottom
    },
  )
  const nearest = buttons.reduce<HTMLButtonElement | null>((selected, button) => {
    if (!selected) return button
    const distance = Math.abs(
      button.getBoundingClientRect().top + button.offsetHeight / 2 - event.clientY,
    )
    const selectedDistance = Math.abs(
      selected.getBoundingClientRect().top + selected.offsetHeight / 2 - event.clientY,
    )
    return distance < selectedDistance ? button : selected
  }, null)
  const id = Number(nearest?.dataset.markerId)
  if (!Number.isFinite(id) || id === draggedId) return
  draggedId = id
  scrollToMarker(id, 'auto')
  const marker = markers.value.find((item) => item.id === id)
  if (marker && nearest) showPreviewAtElement(marker, nearest)
}

function onPointerDown(event: PointerEvent): void {
  if (event.pointerType !== 'mouse' || event.button !== 0) return
  dragging = true
  draggedId = null
  rail.value?.setPointerCapture(event.pointerId)
  scrubToPointer(event)
}

function onPointerMove(event: PointerEvent): void {
  updateWave(event)
  if (dragging) {
    scrubToPointer(event)
    return
  }
  const marker = markers.value[Math.round(waveCenter.value ?? 0)]
  if (!marker || marker.id === previewMarker.value?.id) return
  const button = rail.value?.querySelector<HTMLElement>(`[data-marker-id="${marker.id}"]`)
  if (button) showPreviewAtElement(marker, button)
}

function finishDrag(event: PointerEvent): void {
  if (!dragging) return
  dragging = false
  draggedId = null
  if (rail.value?.hasPointerCapture(event.pointerId))
    rail.value.releasePointerCapture(event.pointerId)
  if (!pointerOverRail) hidePreview()
}

function scrollToMarker(id: number, behavior: ScrollBehavior = 'smooth'): void {
  const container = props.container
  const target = getTarget(id)
  if (!container || !target) return

  const top =
    target.getBoundingClientRect().top -
    container.getBoundingClientRect().top +
    container.scrollTop -
    16
  activeId.value = id
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  container.scrollTo({ top, behavior: reducedMotion ? 'auto' : behavior })
}

watch(() => props.container, bindContainer, { immediate: true, flush: 'post' })
watch(
  () => props.items.map((item) => item.id).join(','),
  () => void nextTick(scheduleUpdate),
  { flush: 'post' },
)

onMounted(() => window.addEventListener('resize', scheduleUpdate))
onUnmounted(() => {
  props.container?.removeEventListener('scroll', scheduleUpdate)
  window.removeEventListener('resize', scheduleUpdate)
  resizeObserver?.disconnect()
  if (frameId !== null) window.cancelAnimationFrame(frameId)
})
</script>

<style scoped>
.message-locator {
  position: absolute;
  inset: 0 auto 0 0;
  z-index: 1;
  width: 38px;
  pointer-events: none;
}
.locator-rail {
  position: absolute;
  top: 50%;
  left: 9px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 28px;
  max-height: calc(100% - 80px);
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: none;
  overscroll-behavior: contain;
  pointer-events: auto;
  transform: translateY(-50%);
}
.locator-rail::-webkit-scrollbar {
  display: none;
}
.locator-mark {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex: 0 0 10px;
  width: 28px;
  height: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.locator-line {
  height: 2px;
  border-radius: 1px;
  background: #d1d5d8;
  transition:
    width 120ms cubic-bezier(0.2, 0.8, 0.2, 1),
    background-color 120ms ease;
}
.locator-mark.active .locator-line {
  background: #818991;
}
.locator-mark.hovered .locator-line {
  background: #33383d;
}
.locator-mark:focus-visible {
  outline: 2px solid #8ab4e0;
  outline-offset: -2px;
}
.locator-preview {
  position: absolute;
  left: 44px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: max-content;
  max-width: min(260px, calc(100vw - 72px));
  padding: 8px 10px;
  border: 1px solid #e6e8eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 16px #00000012;
  color: #363c42;
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
  pointer-events: none;
  transform: translateY(-50%);
}
@media (max-width: 640px) {
  .locator-rail {
    left: 3px;
  }
  .locator-preview {
    left: 38px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .locator-line {
    transition: none;
  }
}
</style>
