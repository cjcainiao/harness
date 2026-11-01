<!--消息区侧边容器-->
<template>
  <aside
    id="chat-message-side-panel"
    ref="mobilePanel"
    class="side-panel"
    :class="{ 'is-desktop-visible': visible, 'is-mobile-open': mobileOpen }"
    :role="mobileOpen ? 'dialog' : undefined"
    :aria-modal="mobileOpen ? 'true' : undefined"
    :aria-label="title"
    :inert="!visible && !mobileOpen"
    :aria-hidden="!visible && !mobileOpen ? 'true' : undefined"
    @keydown="onPanelKeydown"
  >
    <button
      v-if="mobileOpen"
      ref="closeButton"
      class="panel-close"
      type="button"
      @click="closeMobile()"
    >
      <X :size="18" :stroke-width="1.8" aria-hidden="true" />
      <span class="visually-hidden">关闭面板</span>
    </button>
    <header class="panel-header">
      <h2>{{ title }}</h2>
    </header>
    <div class="panel-body">
      <section
        v-if="images.length || galleryError"
        class="image-gallery"
        aria-label="本会话生成的图片"
      >
        <div class="gallery-heading">
          <h3>生成图片</h3>
          <span v-if="images.length" class="gallery-count">{{ images.length }}</span>
        </div>
        <ul v-if="images.length" class="gallery-grid">
          <li v-for="(image, index) in images" :key="image.image_id">
            <button
              class="gallery-thumbnail"
              type="button"
              :aria-label="`预览第 ${index + 1} 张生成图片`"
              :title="`${image.width} × ${image.height}`"
              @click="previewImageId = image.image_id"
            >
              <ImageOff v-if="failedThumbnails.has(image.image_id)" :size="19" aria-hidden="true" />
              <img
                v-else
                :src="generatedImagePreviewUrl(threadId, image.image_id)"
                alt=""
                loading="lazy"
                decoding="async"
                @error="onThumbnailError(image.image_id)"
              />
            </button>
          </li>
        </ul>
        <div v-else class="gallery-empty">
          <span>图片列表加载失败</span>
          <button class="gallery-retry" type="button" @click="refreshImages">重试</button>
        </div>
      </section>
      <slot />
    </div>
  </aside>

  <button
    v-if="showMobileTrigger"
    ref="mobileTrigger"
    class="mobile-trigger"
    type="button"
    aria-controls="chat-message-side-panel"
    :aria-expanded="mobileOpen"
    :aria-label="`打开${title}`"
    :style="{ top: `${triggerPosition * 100}%` }"
    @pointerdown="startDrag"
    @pointermove="moveDrag"
    @pointerup="finishDrag"
    @pointercancel="finishDrag"
    @click="onTriggerClick"
  >
    <PanelRightOpen :size="16" :stroke-width="1.8" aria-hidden="true" />
  </button>

  <Transition name="panel-mask">
    <button
      v-if="mobileOpen"
      class="mobile-mask"
      type="button"
      :aria-label="`关闭${title}`"
      @click="closeMobile()"
    />
  </Transition>
  <ImagePreview
    :src="previewImageId ? generatedImagePreviewUrl(threadId, previewImageId) : null"
    alt="生成图片"
    @close="previewImageId = null"
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ImageOff, PanelRightOpen, X } from 'lucide-vue-next'
import { generatedImagePreviewUrl, type GeneratedImageInfo } from '@/api/generatedImages'
import ImagePreview from '@/components/ImagePreview.vue'
import { useChatImagesStore } from '@/stores/chatImages'
import { useChatSessionsStore } from '@/stores/chatSessions'

const props = withDefaults(
  defineProps<{
    threadId: string
    title?: string
    showMobileTrigger?: boolean
    visible?: boolean
  }>(),
  { title: '会话信息', showMobileTrigger: true, visible: false },
)
const emit = defineEmits<{ 'update:visible': [visible: boolean] }>()
const chatSessions = useChatSessionsStore()
const chatImages = useChatImagesStore()

const mobileOpen = ref(false)
const galleryError = computed(() => chatImages.hasError(props.threadId))
const failedThumbnails = ref(new Set<string>())
const previewImageId = ref<string | null>(null)
const triggerPosition = ref(0.5)
const mobileTrigger = ref<HTMLButtonElement | null>(null)
const mobilePanel = ref<HTMLElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)
let mobileQuery: MediaQueryList | null = null
let sizeObserver: ResizeObserver | null = null
let activePointerId: number | null = null
let dragStartY = 0
let dragStartPosition = 0.5
let dragged = false
let suppressClick = false

// 当前流式轮次的图片立即显示，历史清单补全更早的图片
const liveImages = computed<GeneratedImageInfo[]>(() => {
  void chatSessions.streamTick(props.threadId)
  const found: GeneratedImageInfo[] = []
  for (const turn of chatSessions.getTurns(props.threadId)) {
    const addReady = (item: (typeof turn.items)[number]): void => {
      if (item.type !== 'image' || item.status !== 'ready') return
      found.push({
        image_id: item.imageId,
        mime_type: item.mimeType,
        width: item.width,
        height: item.height,
      })
    }
    for (const item of turn.items) {
      addReady(item)
      if (item.type !== 'tool' || !item.subagent || !item.toolCallId || item.delegationId) continue
      for (const part of chatSessions.getDelegation(turn.id, item.toolCallId)?.items ?? []) {
        addReady(part)
      }
    }
  }
  return found.reverse()
})

const images = computed(() => {
  const seen = new Set<string>()
  return [...liveImages.value, ...chatImages.getImages(props.threadId)].filter((image) => {
    if (seen.has(image.image_id)) return false
    seen.add(image.image_id)
    return true
  })
})

// 手动重试强制刷新当前会话清单
function refreshImages(): void {
  void chatImages.loadImages(props.threadId, true)
}

function onThumbnailError(imageId: string): void {
  failedThumbnails.value = new Set([...failedThumbnails.value, imageId])
}

watch(
  () => props.threadId,
  () => {
    failedThumbnails.value = new Set()
    previewImageId.value = null
    void chatImages.loadImages(props.threadId)
  },
  { immediate: true },
)

// 拖动位置限制在消息区内
function clampTriggerPosition(position: number): number {
  const trigger = mobileTrigger.value
  const areaHeight = trigger?.parentElement?.getBoundingClientRect().height ?? 0
  if (!trigger || areaHeight <= 0) return 0.5
  const edge = Math.min(0.5, trigger.offsetHeight / (2 * areaHeight))
  return Math.max(edge, Math.min(1 - edge, position))
}

function startDrag(event: PointerEvent): void {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  activePointerId = event.pointerId
  dragStartY = event.clientY
  dragStartPosition = triggerPosition.value
  dragged = false
  suppressClick = false
  mobileTrigger.value?.setPointerCapture(event.pointerId)
}

function moveDrag(event: PointerEvent): void {
  if (activePointerId !== event.pointerId) return
  const distance = event.clientY - dragStartY
  if (!dragged && Math.abs(distance) < 6) return
  dragged = true
  const areaHeight = mobileTrigger.value?.parentElement?.getBoundingClientRect().height ?? 0
  if (areaHeight > 0) {
    triggerPosition.value = clampTriggerPosition(dragStartPosition + distance / areaHeight)
  }
}

function finishDrag(event: PointerEvent): void {
  if (activePointerId !== event.pointerId) return
  if (dragged) suppressClick = true
  if (mobileTrigger.value?.hasPointerCapture(event.pointerId)) {
    mobileTrigger.value.releasePointerCapture(event.pointerId)
  }
  activePointerId = null
  dragged = false
}

function onTriggerClick(event: MouseEvent): void {
  if (suppressClick && event.detail !== 0) {
    suppressClick = false
    return
  }
  suppressClick = false
  openMobile()
  emit('update:visible', true)
}

function openMobile(): void {
  mobileOpen.value = true
  void nextTick(() => closeButton.value?.focus())
}

function closeMobile(restoreFocus = true): void {
  mobileOpen.value = false
  emit('update:visible', false)
  if (restoreFocus) void nextTick(() => mobileTrigger.value?.focus())
}

// 顶栏图标控制开合：移动端同步抽屉状态
watch(
  () => props.visible,
  (visible) => {
    if (!mobileQuery?.matches) return
    if (visible) openMobile()
    else if (mobileOpen.value) closeMobile(false)
  },
)

// 面板打开时将键盘焦点留在面板内
function onPanelKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Tab') return
  const focusable = Array.from(
    mobilePanel.value?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) ?? [],
  ).filter((element) => element.getClientRects().length > 0)
  const first = focusable[0]
  const last = focusable.at(-1)
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function onEscape(event: KeyboardEvent): void {
  if (event.target instanceof Element && event.target.closest('.image-preview')) return
  if (mobileOpen.value && event.key === 'Escape') closeMobile()
}

function onBreakpointChange(): void {
  if (!mobileQuery?.matches && mobileOpen.value) closeMobile(false)
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 700px)')
  mobileQuery.addEventListener('change', onBreakpointChange)
  window.addEventListener('keydown', onEscape)
  const messageArea = mobilePanel.value?.parentElement
  if (messageArea) {
    sizeObserver = new ResizeObserver(() => {
      triggerPosition.value = clampTriggerPosition(triggerPosition.value)
    })
    sizeObserver.observe(messageArea)
  }
})

onUnmounted(() => {
  mobileQuery?.removeEventListener('change', onBreakpointChange)
  window.removeEventListener('keydown', onEscape)
  sizeObserver?.disconnect()
})
</script>

<style scoped>
.side-panel {
  display: none;
  flex: none;
  flex-direction: column;
  width: 0;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid transparent;
  background: #fff;
}
/* 桌面端由顶栏图标开合，宽度过渡与左侧栏一致 */
@media (min-width: 701px) {
  .side-panel {
    display: flex;
    transition:
      width 0.2s ease,
      border-color 0.2s ease;
  }
  .side-panel.is-desktop-visible {
    width: clamp(260px, 24vw, 340px);
    border-left-color: #e7e9ec;
  }
  /* 收起时保持内容原宽，跟着面板裁切，不做逐帧挤压 */
  .panel-header,
  .panel-body {
    min-width: clamp(260px, 24vw, 340px);
  }
}
.panel-header {
  display: flex;
  flex: none;
  align-items: center;
  min-height: 44px;
  padding: 0 14px;
  border-bottom: 1px solid #e8e9eb;
}
.panel-header h2 {
  color: #30363d;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}
.panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.image-gallery {
  padding: 0 14px 14px;
  border-bottom: 1px solid #eff0f2;
}
.gallery-heading {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 42px;
}
.gallery-heading h3 {
  color: #68717b;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
}
.gallery-count {
  color: #8b939c;
  font-size: 12px;
}
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
  gap: 8px;
  max-height: 224px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.gallery-thumbnail {
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 1;
  padding: 0;
  overflow: hidden;
  border: 1px solid #e7e9ec;
  border-radius: 6px;
  background: #f5f6f7;
  color: #a4abb3;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.gallery-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gallery-thumbnail:focus-visible,
.gallery-retry:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
}
.gallery-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  color: #9aa1a9;
  font-size: 12px;
}
.gallery-retry {
  padding: 0;
  border: 0;
  background: transparent;
  color: #5d728e;
  cursor: pointer;
}
.mobile-trigger,
.mobile-mask {
  display: none;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
@media (max-width: 700px) {
  .panel-header {
    min-height: 56px;
    padding-right: 52px;
  }
  .mobile-trigger {
    position: absolute;
    z-index: 3;
    right: 0;
    display: grid;
    place-items: center;
    width: 20px;
    height: 40px;
    padding: 0;
    border: 0;
    background: transparent;
    color: #626b76;
    cursor: pointer;
    touch-action: none;
    transform: translateY(-50%);
    -webkit-tap-highlight-color: transparent;
  }
  .mobile-mask {
    position: fixed;
    z-index: 39;
    inset: 0;
    display: block;
    width: 100%;
    padding: 0;
    border: 0;
    background: rgb(18 22 28 / 32%);
  }
  .side-panel {
    position: fixed;
    z-index: 40;
    inset: 0 0 0 auto;
    display: flex;
    width: min(320px, calc(100vw - 24px));
    height: 100vh;
    padding-bottom: env(safe-area-inset-bottom);
    border-left: 1px solid #e7e9ec;
    box-shadow: -8px 0 28px rgb(25 34 45 / 13%);
    visibility: hidden;
    pointer-events: none;
    transform: translateX(105%);
    transition:
      transform 0.2s ease,
      visibility 0.2s ease;
  }
  .side-panel.is-mobile-open {
    visibility: visible;
    pointer-events: auto;
    transform: none;
  }
  .panel-close {
    position: absolute;
    z-index: 1;
    top: 8px;
    right: 8px;
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    padding: 0;
    border: 0;
    background: transparent;
    color: #68717b;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .mobile-trigger:focus-visible,
  .panel-close:focus-visible {
    outline: 2px solid #8b9fc7;
    outline-offset: 2px;
  }
  .panel-mask-enter-active,
  .panel-mask-leave-active {
    transition: opacity 0.2s ease;
  }
  .panel-mask-enter-from,
  .panel-mask-leave-to {
    opacity: 0;
  }
}
@media (max-width: 700px) and (hover: hover) {
  .mobile-trigger:hover {
    color: #30363d;
  }
  .panel-close:hover {
    background: #f5f6f7;
    color: #30363d;
  }
}
@media (hover: hover) {
  .gallery-thumbnail:hover {
    border-color: #b9c5d1;
  }
  .gallery-retry:hover {
    color: #344963;
  }
}
@media (any-pointer: coarse) {
  .gallery-retry {
    min-height: 36px;
  }
}
@media (max-width: 700px) {
  @supports (height: 100dvh) {
    .side-panel {
      height: 100dvh;
    }
  }
}
@media (prefers-reduced-motion: reduce) {
  .side-panel,
  .panel-mask-enter-active,
  .panel-mask-leave-active {
    transition: none;
  }
}
</style>
