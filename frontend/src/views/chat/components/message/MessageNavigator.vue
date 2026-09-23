<template>
  <nav
    ref="navigatorRef"
    class="message-navigator"
    aria-label="消息定位"
    :data-scrubbing="scrubId !== null || undefined"
    :data-touch-input="touchInput || undefined"
    @pointerdown.capture="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup.capture="onPointerEnd"
    @pointercancel.capture="onPointerEnd"
    @lostpointercapture.capture="onPointerEnd"
    @pointerleave="onPointerLeave"
  >
    <button
      v-for="(item, index) in items"
      :key="item.id"
      class="navigator-tick"
      :data-message-id="item.id"
      :data-scrub-target="scrubId === item.id || undefined"
      :aria-label="`跳转到第 ${index + 1} 条消息：${item.title}`"
      :aria-current="item.id === activeId ? 'true' : undefined"
      type="button"
      @pointerenter="onTickEnter($event)"
      @focus="onTickFocus($event)"
      @blur="onTickBlur"
      @click="onTickClick(item.id)"
    >
      <span class="navigator-marker"><span class="navigator-line" /></span>
    </button>
    <ElTooltip
      :visible="tooltipItem !== undefined"
      :virtual-ref="tooltipTarget"
      virtual-triggering
      effect="light"
      placement="right"
      :offset="0"
      :show-arrow="false"
      :enterable="false"
      :popper-style="tooltipStyle"
    >
      <template #content>
        <div v-if="tooltipItem" class="navigator-tip">
          <strong class="navigator-tip-title">{{ tooltipItem.title }}</strong>
          <p v-if="tooltipItem.preview" class="navigator-tip-preview">{{ tooltipItem.preview }}</p>
        </div>
      </template>
    </ElTooltip>
  </nav>
</template>

<script setup lang="ts">
import { ElTooltip } from 'element-plus'
import 'element-plus/es/components/tooltip/style/css'
import { computed, onBeforeUnmount, ref } from 'vue'

interface MessageAnchor {
  id: string
  title: string
  preview?: string
}

const props = defineProps<{ items: MessageAnchor[]; activeId: string }>()
const emit = defineEmits<{ select: [id: string, behavior: ScrollBehavior] }>()
const navigatorRef = ref<HTMLElement>()
const tooltipTarget = ref<HTMLElement>()
const tooltipId = ref<string | null>(null)
const scrubId = ref<string | null>(null)
const touchInput = ref(false)
const tooltipItem = computed(() => props.items.find((item) => item.id === tooltipId.value))
const tooltipStyle = {
  width: '320px',
  maxWidth: 'calc(100vw - 16px)',
  padding: '8px',
  borderRadius: '12px',
  border: '1px solid rgba(32, 35, 38, 0.08)',
  background: 'rgba(255, 255, 255, 0.95)',
  boxShadow: '0 10px 28px rgba(20, 24, 29, 0.14)',
  backdropFilter: 'blur(8px)',
}

let pointerId: number | null = null
let activePointerType: string | null = null
let captureTarget: HTMLButtonElement | null = null
let suppressClick = false
let suppressClickTimer = 0
let tooltipTimer = 0
let autoScrollFrame = 0
let pointerClientY = 0

function tickFromElement(element: Element | null): HTMLButtonElement | null {
  const tick = element?.closest<HTMLButtonElement>('.navigator-tick')
  return tick && navigatorRef.value?.contains(tick) ? tick : null
}

function showTooltip(tick: HTMLButtonElement, immediate = false) {
  window.clearTimeout(tooltipTimer)
  const update = () => {
    tooltipTarget.value = tick
    tooltipId.value = tick.dataset.messageId ?? null
  }
  if (immediate) update()
  else tooltipTimer = window.setTimeout(update, 150)
}

function hideTooltip() {
  window.clearTimeout(tooltipTimer)
  tooltipId.value = null
}

function onTickEnter(event: PointerEvent) {
  if (event.pointerType === 'touch' || pointerId !== null) return
  touchInput.value = false
  const tick = tickFromElement(event.currentTarget as Element)
  if (tick) showTooltip(tick)
}

function onTickFocus(event: FocusEvent) {
  const tick = tickFromElement(event.currentTarget as Element)
  if (tick?.matches(':focus-visible')) showTooltip(tick, true)
}

function onTickBlur() {
  if (pointerId === null && !navigatorRef.value?.matches(':hover')) hideTooltip()
}

function onPointerLeave() {
  if (pointerId === null && !navigatorRef.value?.querySelector('.navigator-tick:focus-visible')) {
    hideTooltip()
  }
}

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  const tick = tickFromElement(event.target as Element)
  if (!tick) return
  window.clearTimeout(suppressClickTimer)
  pointerId = event.pointerId
  activePointerType = event.pointerType
  touchInput.value = event.pointerType === 'touch'
  captureTarget = tick
  suppressClick = false
  pointerClientY = event.clientY
  scrubId.value = tick.dataset.messageId ?? null
  showTooltip(tick, true)
  tick.setPointerCapture?.(event.pointerId)
  scheduleAutoScroll()
}

function scrubAt(clientY: number) {
  if (!navigatorRef.value) return
  const bounds = navigatorRef.value.getBoundingClientRect()
  const x = bounds.left + bounds.width / 2
  const y = Math.max(bounds.top, Math.min(clientY, bounds.bottom - 1))
  const tick = tickFromElement(document.elementFromPoint(x, y))
  const id = tick?.dataset.messageId
  if (!tick || !id || id === scrubId.value) return
  scrubId.value = id
  suppressClick = true
  showTooltip(tick, true)
  emit('select', id, 'instant')
}

function runAutoScroll() {
  autoScrollFrame = 0
  const navigator = navigatorRef.value
  if (pointerId === null || activePointerType !== 'touch' || !navigator) return
  const bounds = navigator.getBoundingClientRect()
  const edge = 24
  const distanceFromTop = pointerClientY - bounds.top
  const distanceFromBottom = bounds.bottom - pointerClientY
  let step = 0
  if (distanceFromTop < edge) step = -Math.min(12, Math.max(2, (edge - distanceFromTop) / 2))
  else if (distanceFromBottom < edge)
    step = Math.min(12, Math.max(2, (edge - distanceFromBottom) / 2))
  if (!step) return
  const previous = navigator.scrollTop
  navigator.scrollTop += step
  if (navigator.scrollTop !== previous) {
    scrubAt(pointerClientY)
    autoScrollFrame = window.requestAnimationFrame(runAutoScroll)
  }
}

function scheduleAutoScroll() {
  if (activePointerType === 'touch' && !autoScrollFrame) {
    autoScrollFrame = window.requestAnimationFrame(runAutoScroll)
  }
}

function onPointerMove(event: PointerEvent) {
  if (event.pointerType === 'mouse') touchInput.value = false
  if (pointerId !== event.pointerId) return
  if (event.pointerType !== 'touch' && (event.buttons & 1) === 0) {
    onPointerEnd(event)
    return
  }
  pointerClientY = event.clientY
  scrubAt(pointerClientY)
  scheduleAutoScroll()
}

function onPointerEnd(event: PointerEvent) {
  if (pointerId !== event.pointerId) return
  window.cancelAnimationFrame(autoScrollFrame)
  autoScrollFrame = 0
  const target = captureTarget
  const wasTouch = activePointerType === 'touch'
  pointerId = null
  activePointerType = null
  captureTarget = null
  scrubId.value = null
  if (target?.hasPointerCapture?.(event.pointerId)) target.releasePointerCapture(event.pointerId)
  if (wasTouch) hideTooltip()
  if (suppressClick) {
    suppressClickTimer = window.setTimeout(() => {
      suppressClick = false
    }, 500)
  }
}

function onTickClick(id: string) {
  if (suppressClick) {
    window.clearTimeout(suppressClickTimer)
    suppressClick = false
    return
  }
  emit('select', id, 'smooth')
}

onBeforeUnmount(() => {
  window.clearTimeout(tooltipTimer)
  window.clearTimeout(suppressClickTimer)
  window.cancelAnimationFrame(autoScrollFrame)
})
</script>

<style scoped>
.message-navigator {
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 18px;
  display: flex;
  flex-direction: column;
  max-height: min(70vh, 40rem);
  overflow-y: auto;
  transform: translateY(-50%);
  scrollbar-width: none;
  touch-action: none;
  user-select: none;
}
.message-navigator::-webkit-scrollbar {
  display: none;
}
.navigator-tick {
  display: flex;
  align-items: center;
  width: 36px;
  min-height: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  outline: none;
}
.navigator-marker {
  --marker-progress: 0;
  position: relative;
  display: flex;
  width: 26px;
  height: 2px;
  color: #747b83;
  opacity: 0.4;
}
.navigator-line {
  width: 100%;
  height: 100%;
  background: currentColor;
  transform: scaleX(calc(0.2308 + 0.7692 * var(--marker-progress)));
  transform-origin: left;
  transition: transform 0.16s
    linear(
      0,
      0.398 10%,
      0.682 20%,
      0.843 30%,
      0.925 40%,
      0.972 50%,
      1.004 60%,
      1.008 70%,
      1.003 80%,
      1
    );
}
.navigator-tick[aria-current='true'] .navigator-marker {
  color: #202428;
  opacity: 0.6;
}
:is(
    .navigator-tick:has(+ .navigator-tick[data-scrub-target]),
    .navigator-tick[data-scrub-target] + .navigator-tick
  )
  .navigator-marker {
  --marker-progress: 0.7;
}
:is(
    .navigator-tick:has(+ .navigator-tick + .navigator-tick[data-scrub-target]),
    .navigator-tick[data-scrub-target] + .navigator-tick + .navigator-tick
  )
  .navigator-marker {
  --marker-progress: 0.4;
}
:is(
    .navigator-tick:has(+ .navigator-tick + .navigator-tick + .navigator-tick[data-scrub-target]),
    .navigator-tick[data-scrub-target] + .navigator-tick + .navigator-tick + .navigator-tick
  )
  .navigator-marker {
  --marker-progress: 0.2;
}
.navigator-tick:focus-visible .navigator-marker,
.navigator-tick[data-scrub-target] .navigator-marker {
  --marker-progress: 1;
  color: #202428;
  opacity: 1;
}
.message-navigator[data-scrubbing] .navigator-line {
  transition-duration: 0s;
}
.message-navigator:has([data-scrub-target])
  .navigator-tick[aria-current='true']:not([data-scrub-target])
  .navigator-marker {
  color: #747b83;
  opacity: 0.4;
}
@media (hover: hover) {
  .message-navigator:not([data-scrubbing]):not([data-touch-input]):not(
      :has([data-scrub-target])
    ):hover
    .navigator-tick[aria-current='true']:not(:hover):not(:focus-visible)
    .navigator-marker {
    color: #747b83;
    opacity: 0.4;
  }
  .message-navigator:not([data-scrubbing]):not([data-touch-input]):not(
      :has([data-scrub-target])
    ):hover
    :is(.navigator-tick:has(+ .navigator-tick:hover), .navigator-tick:hover + .navigator-tick)
    .navigator-marker {
    --marker-progress: 0.7;
  }
  .message-navigator:not([data-scrubbing]):not([data-touch-input]):not(
      :has([data-scrub-target])
    ):hover
    :is(
      .navigator-tick:has(+ .navigator-tick + .navigator-tick:hover),
      .navigator-tick:hover + .navigator-tick + .navigator-tick
    )
    .navigator-marker {
    --marker-progress: 0.4;
  }
  .message-navigator:not([data-scrubbing]):not([data-touch-input]):not(
      :has([data-scrub-target])
    ):hover
    :is(
      .navigator-tick:has(+ .navigator-tick + .navigator-tick + .navigator-tick:hover),
      .navigator-tick:hover + .navigator-tick + .navigator-tick + .navigator-tick
    )
    .navigator-marker {
    --marker-progress: 0.2;
  }
  .message-navigator:not([data-scrubbing]):not([data-touch-input]):not(
      :has([data-scrub-target])
    ):hover
    .navigator-tick:hover
    .navigator-marker {
    --marker-progress: 1;
    color: #202428;
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .navigator-line {
    transition-duration: 0s;
  }
}
@media (any-pointer: coarse) {
  .navigator-tick {
    width: 44px;
    min-height: 14px;
  }
}
.navigator-tip {
  display: grid;
  gap: 4px;
  width: 302px;
  font-size: 12px;
  line-height: 20px;
}
.navigator-tip-title {
  overflow: hidden;
  color: #24282d;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.navigator-tip-preview {
  display: -webkit-box;
  overflow: hidden;
  color: #70777e;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
</style>
