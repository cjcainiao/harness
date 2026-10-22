<!--PPT 页面缩略图列表-->
<template>
  <aside
    ref="drawer"
    id="ppt-slide-filmstrip"
    class="slide-filmstrip"
    :class="{ 'is-open': mobileOpen }"
    :role="mobileOpen ? 'dialog' : undefined"
    :aria-modal="mobileOpen ? 'true' : undefined"
    aria-label="幻灯片列表"
    @keydown.esc.stop="emit('close')"
    @keydown.tab="trapFocus"
  >
    <div class="drawer-heading">
      <strong>幻灯片</strong>
      <button ref="closeButton" type="button" aria-label="关闭幻灯片列表" @click="emit('close')">
        <X :size="18" :stroke-width="1.8" />
      </button>
    </div>
    <div class="filmstrip-content">
      <div
        v-for="(slide, index) in slides"
        :key="slide.id"
        class="slide-swipe-row"
        :data-slide-id="slide.id"
      >
        <button
          class="swipe-delete"
          type="button"
          :aria-label="`删除第 ${index + 1} 页幻灯片`"
          :aria-hidden="revealedSlideId !== slide.id && swipingSlideId !== slide.id"
          :tabindex="revealedSlideId === slide.id ? 0 : -1"
          :disabled="slides.length <= 1"
          @click.stop="openDeleteDialog(slide.id)"
        >
          <Trash2 :size="17" aria-hidden="true" />
          <span>删除</span>
        </button>
        <button
          class="slide-item"
          :class="{ 'is-dragging': swipingSlideId === slide.id }"
          :style="{ transform: `translateX(${rowOffset(slide.id)}px)` }"
          type="button"
          :aria-label="`第 ${index + 1} 页${slide.id === activeSlideId ? '，当前页面' : ''}`"
          :aria-current="slide.id === activeSlideId ? 'page' : undefined"
          @click="selectFromRow(slide.id)"
          @contextmenu.prevent="openContextMenu($event, slide.id, index + 1)"
          @pointerdown="onRowPointerDown($event, slide.id)"
          @pointermove="onRowPointerMove($event, slide.id)"
          @pointerup="onRowPointerUp($event, slide.id)"
          @pointercancel="onRowPointerCancel($event, slide.id)"
        >
          <span class="slide-index">{{ index + 1 }}</span>
          <span
            class="thumbnail"
            :class="{ selected: slide.id === activeSlideId }"
            aria-hidden="true"
          >
            <span
              v-for="element in slide.elements"
              :key="element.id"
              class="thumbnail-text"
              :style="{
                left: `${(element.x / 960) * 100}%`,
                top: `${(element.y / 540) * 100}%`,
                width: `${(element.width / 960) * 100}%`,
                fontSize: `${Math.max(5, element.fontSize * 0.22)}px`,
              }"
              >{{ element.text }}</span
            >
          </span>
        </button>
      </div>
      <button class="add-slide" type="button" @click="emit('add')">
        <Plus :size="14" :stroke-width="1.8" /> 新建幻灯片
      </button>
    </div>
    <nav class="filmstrip-nav" aria-label="项目页面">
      <RouterLink :to="{ name: 'ppt-index' }">返回项目</RouterLink>
      <RouterLink :to="{ name: 'ppt-outline', params: { projectId } }">查看大纲</RouterLink>
    </nav>
  </aside>
  <Teleport to="body">
    <div
      v-if="contextMenu"
      ref="contextMenuRef"
      class="slide-context-menu"
      :class="{ 'is-above': contextMenu.placement === 'above' }"
      role="menu"
      :aria-label="`第 ${contextMenu.pageNumber} 页操作菜单`"
      :style="{
        left: `${contextMenu.x}px`,
        top: `${contextMenu.y}px`,
        '--arrow-x': `${contextMenu.arrowX}px`,
      }"
      @contextmenu.prevent
    >
      <button
        class="context-delete"
        type="button"
        role="menuitem"
        :disabled="slides.length <= 1"
        @click="openDeleteDialog(contextMenu.id)"
      >
        <Trash2 :size="15" aria-hidden="true" />
        <span>{{ slides.length <= 1 ? '至少保留一页' : '删除幻灯片' }}</span>
      </button>
    </div>
  </Teleport>
  <SlideDeleteDialog
    :visible="deleteDialogVisible"
    :page-number="deleteTarget?.pageNumber ?? 0"
    @close="deleteDialogVisible = false"
    @confirm="confirmDelete"
    @closed="deleteTarget = null"
  />
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Plus, Trash2, X } from 'lucide-vue-next'
import SlideDeleteDialog from '@/views/ppt/components/editor/SlideDeleteDialog.vue'
import type { PptSlide } from '@/views/ppt/data/deckTypes'

interface ContextMenuState {
  id: string
  pageNumber: number
  x: number
  y: number
  arrowX: number
  placement: 'above' | 'below'
}

interface SwipeGesture {
  id: string
  pointerId: number
  startX: number
  startY: number
  startOffset: number
  horizontal: boolean
}

const SWIPE_ACTION_WIDTH = 64
const SWIPE_START_PX = 10

const props = defineProps<{
  projectId: string
  mobileOpen: boolean
  slides: PptSlide[]
  activeSlideId: string
}>()
const emit = defineEmits<{ close: []; select: [id: string]; add: []; delete: [id: string] }>()
const drawer = ref<HTMLElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)
const contextMenu = ref<ContextMenuState | null>(null)
const deleteDialogVisible = ref(false)
const deleteTarget = ref<{ id: string; pageNumber: number } | null>(null)
const revealedSlideId = ref<string | null>(null)
const swipingSlideId = ref<string | null>(null)
const swipeOffset = ref(0)
let swipeGesture: SwipeGesture | null = null
let suppressedClickId: string | null = null
let suppressClickTimer: ReturnType<typeof setTimeout> | undefined
let focusTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.mobileOpen,
  (open) => {
    clearTimeout(focusTimer)
    if (!open) {
      closeContextMenu()
      closeSwipeActions()
    }
    if (open) {
      focusTimer = setTimeout(() => {
        if (props.mobileOpen) closeButton.value?.focus()
      }, 220)
    }
  },
)

function rowOffset(id: string): number {
  if (swipingSlideId.value === id) return swipeOffset.value
  return revealedSlideId.value === id ? -SWIPE_ACTION_WIDTH : 0
}

function closeSwipeActions() {
  revealedSlideId.value = null
}

function selectFromRow(id: string) {
  if (suppressedClickId === id) {
    suppressedClickId = null
    return
  }
  closeContextMenu()
  closeSwipeActions()
  emit('select', id)
}

function onRowPointerDown(event: PointerEvent, id: string) {
  if (event.pointerType === 'mouse' || !event.isPrimary || props.slides.length <= 1) return
  if (suppressedClickId === id) suppressedClickId = null
  swipeGesture = {
    id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startOffset: revealedSlideId.value === id ? -SWIPE_ACTION_WIDTH : 0,
    horizontal: false,
  }
}

function onRowPointerMove(event: PointerEvent, id: string) {
  const gesture = swipeGesture
  if (!gesture || gesture.id !== id || gesture.pointerId !== event.pointerId) return
  const dx = event.clientX - gesture.startX
  const dy = event.clientY - gesture.startY
  if (!gesture.horizontal) {
    if (Math.abs(dy) > SWIPE_START_PX && Math.abs(dy) > Math.abs(dx)) {
      swipeGesture = null
      return
    }
    if (Math.abs(dx) < SWIPE_START_PX || Math.abs(dx) <= Math.abs(dy)) return
    gesture.horizontal = true
    if (revealedSlideId.value !== id) closeSwipeActions()
    swipingSlideId.value = id
  }
  swipeOffset.value = Math.max(-SWIPE_ACTION_WIDTH, Math.min(0, gesture.startOffset + dx))
}

function onRowPointerUp(event: PointerEvent, id: string) {
  const gesture = swipeGesture
  if (!gesture || gesture.id !== id || gesture.pointerId !== event.pointerId) return
  if (gesture.horizontal) {
    revealedSlideId.value = swipeOffset.value < -SWIPE_ACTION_WIDTH / 2 ? id : null
    suppressedClickId = id
    if (suppressClickTimer) clearTimeout(suppressClickTimer)
    suppressClickTimer = setTimeout(() => {
      suppressedClickId = null
      suppressClickTimer = undefined
    }, 400)
  }
  swipeGesture = null
  swipingSlideId.value = null
  swipeOffset.value = 0
}

function onRowPointerCancel(event: PointerEvent, id: string) {
  if (swipeGesture?.id !== id || swipeGesture.pointerId !== event.pointerId) return
  swipeGesture = null
  swipingSlideId.value = null
  swipeOffset.value = 0
}

function closeContextMenu() {
  contextMenu.value = null
}

async function openContextMenu(event: MouseEvent, id: string, pageNumber: number) {
  if (window.matchMedia('(hover: none)').matches) return
  closeSwipeActions()
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const keyboardTriggered = event.clientX === 0 && event.clientY === 0
  const pointerX = keyboardTriggered ? rect.left + 24 : event.clientX
  const pointerY = keyboardTriggered ? rect.bottom : event.clientY
  contextMenu.value = {
    id,
    pageNumber,
    x: pointerX,
    y: pointerY,
    arrowX: 16,
    placement: 'below',
  }

  await nextTick()
  const menu = contextMenuRef.value
  if (!menu || contextMenu.value?.id !== id) return
  const gap = 9
  const placement = pointerY + gap + menu.offsetHeight + 8 <= window.innerHeight ? 'below' : 'above'
  const x = Math.max(8, Math.min(pointerX - 16, window.innerWidth - menu.offsetWidth - 8))
  const desiredY = placement === 'below' ? pointerY + gap : pointerY - menu.offsetHeight - gap
  contextMenu.value = {
    ...contextMenu.value,
    x,
    y: Math.max(8, Math.min(desiredY, window.innerHeight - menu.offsetHeight - 8)),
    arrowX: Math.max(14, Math.min(pointerX - x, menu.offsetWidth - 14)),
    placement,
  }
}

function openDeleteDialog(id: string) {
  const index = props.slides.findIndex((slide) => slide.id === id)
  if (index < 0 || props.slides.length <= 1) return
  closeContextMenu()
  closeSwipeActions()
  deleteTarget.value = { id, pageNumber: index + 1 }
  deleteDialogVisible.value = true
}

function confirmDelete() {
  const id = deleteTarget.value?.id
  if (!id) return
  deleteDialogVisible.value = false
  emit('delete', id)
}

function onDocumentPointerDown(event: PointerEvent) {
  if (contextMenuRef.value?.contains(event.target as Node)) return
  closeContextMenu()
  if (!revealedSlideId.value) return
  const row = event.target instanceof Element ? event.target.closest('.slide-swipe-row') : null
  if (row?.getAttribute('data-slide-id') !== revealedSlideId.value) closeSwipeActions()
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeContextMenu()
    closeSwipeActions()
  }
}

onMounted(() => {
  window.addEventListener('resize', closeContextMenu)
  window.addEventListener('scroll', closeContextMenu, true)
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeydown)
})

onBeforeUnmount(() => {
  clearTimeout(focusTimer)
  if (suppressClickTimer) clearTimeout(suppressClickTimer)
  window.removeEventListener('resize', closeContextMenu)
  window.removeEventListener('scroll', closeContextMenu, true)
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})

function trapFocus(event: KeyboardEvent) {
  if (!props.mobileOpen) return
  const focusable = drawer.value?.querySelectorAll<HTMLElement>('button, a[href]')
  if (!focusable?.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}
</script>

<style scoped>
.slide-filmstrip {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  justify-content: space-between;
  border-right: 1px solid #d5d5d5;
  background: #f1f1f1;
}

.drawer-heading {
  display: none;
}

.filmstrip-content {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding: 8px 20px 16px 5px;
}

.slide-swipe-row {
  position: relative;
  flex: none;
  overflow: hidden;
}

.swipe-delete {
  position: absolute;
  inset: 0 0 0 auto;
  display: flex;
  width: 64px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0;
  border: 0;
  background: #e56565;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.swipe-delete:disabled {
  background: #b8bec7;
  cursor: not-allowed;
}

.slide-item {
  position: relative;
  z-index: 1;
  display: grid;
  width: 100%;
  grid-template-columns: 20px minmax(0, 1fr);
  align-items: start;
  padding: 0;
  border: 0;
  background: #f1f1f1;
  cursor: pointer;
  touch-action: pan-y;
  -webkit-tap-highlight-color: transparent;
  transition: transform 200ms cubic-bezier(0.2, 0.75, 0.25, 1);
}

.slide-item.is-dragging {
  transition: none;
}

.slide-index {
  color: #777;
  font-size: 15px;
  line-height: 22px;
  text-align: left;
}

.thumbnail {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 250 / 145;
  overflow: hidden;
  border: 2px solid #d4d4d4;
  border-radius: 7px;
  background: #fff;
  box-shadow: 0 1px 2px rgb(0 0 0 / 7%);
}

.thumbnail.selected {
  border-color: #b74426;
}

.slide-item[aria-current='page'] .slide-index {
  color: #b74324;
}

.thumbnail-text {
  position: absolute;
  overflow: hidden;
  color: #202020;
  line-height: 1.2;
  text-align: left;
  white-space: pre-wrap;
}

.add-slide {
  display: flex;
  min-height: 34px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-left: 20px;
  border: 1px dashed #c9c9c9;
  border-radius: 6px;
  background: transparent;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.filmstrip-nav {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px 12px 25px;
  color: #858585;
  font-size: 11px;
}

.filmstrip-nav a {
  min-height: 24px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.slide-context-menu {
  position: fixed;
  z-index: 2000;
  width: 158px;
  padding: 5px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 30px rgb(25 35 50 / 14%);
}

.slide-context-menu::before {
  position: absolute;
  top: -5px;
  left: calc(var(--arrow-x) - 5px);
  width: 8px;
  height: 8px;
  border-top: 1px solid #e5e7eb;
  border-left: 1px solid #e5e7eb;
  background: #fff;
  transform: rotate(45deg);
  content: '';
}

.slide-context-menu.is-above::before {
  top: auto;
  bottom: -5px;
  border: 0;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.context-delete {
  display: flex;
  width: 100%;
  min-height: 38px;
  align-items: center;
  gap: 9px;
  padding: 0 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #d35b5b;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.context-delete:disabled {
  color: #a9adb3;
  cursor: not-allowed;
}

.context-delete:focus-visible {
  outline: 2px solid #909399;
  outline-offset: -2px;
}

@media (hover: hover) {
  .slide-item:hover .thumbnail {
    border-color: #b76b54;
  }

  .add-slide:hover {
    border-color: #b74426;
    color: #b74426;
  }

  .filmstrip-nav a:hover {
    color: #b74426;
  }

  .context-delete:not(:disabled):hover {
    background: #fff2f2;
  }
}

@media (max-width: 700px) {
  .slide-filmstrip {
    position: fixed;
    z-index: 11;
    top: 0;
    left: 0;
    width: clamp(160px, 48vw, 208px);
    height: 100vh;
    border-right: 1px solid #d5d5d5;
    box-shadow: 4px 0 18px rgb(0 0 0 / 10%);
    transform: translateX(-100%);
    transition:
      transform 0.2s ease,
      visibility 0.2s ease;
    visibility: hidden;
    pointer-events: none;
  }

  .slide-filmstrip.is-open {
    transform: translateX(0);
    visibility: visible;
    pointer-events: auto;
  }

  .drawer-heading {
    display: flex;
    height: 52px;
    flex: none;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px 0 20px;
    border-bottom: 1px solid #dedede;
    color: #333;
    font-size: 14px;
  }

  .drawer-heading button {
    display: grid;
    width: 34px;
    height: 34px;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: #666;
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .filmstrip-content {
    flex: 1;
    overflow-y: auto;
    padding: 14px 20px 16px 5px;
  }

  .filmstrip-nav {
    border-top: 1px solid #dedede;
    padding: 12px 16px max(12px, env(safe-area-inset-bottom)) 20px;
    font-size: 12px;
  }
}

@supports (height: 100dvh) {
  @media (max-width: 700px) {
    .slide-filmstrip {
      height: 100dvh;
    }
  }
}

@media (hover: hover) {
  .drawer-heading button:hover {
    background: #e8e8e8;
    color: #333;
  }
}

@media (any-pointer: coarse) {
  .swipe-delete {
    min-height: 40px;
  }

  .add-slide {
    min-height: 40px;
  }
  .drawer-heading button {
    min-width: 40px;
    min-height: 40px;
  }

  .filmstrip-nav a {
    display: flex;
    min-height: 36px;
    align-items: center;
  }
}
</style>
