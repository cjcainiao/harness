<!--会话历史列表-->
<template>
  <div ref="listRef" class="conversation-list" @scroll="onListScroll">
    <section v-for="group in groups" :key="group.label" class="history-group">
      <h4 class="group-label">{{ group.label }}</h4>
      <div
        v-for="item in group.items"
        :key="item.id"
        class="history-swipe-item"
        :data-session-id="item.id"
      >
        <div
          class="history-actions"
          :aria-hidden="revealedSessionId !== item.id && swipingSessionId !== item.id"
        >
          <button class="swipe-action is-rename" type="button" disabled>
            <Pencil :size="16" aria-hidden="true" />
            <span>重命名</span>
          </button>
          <button class="swipe-action is-delete" type="button" disabled>
            <Trash2 :size="16" aria-hidden="true" />
            <span>删除</span>
          </button>
        </div>
        <button
          class="history-item"
          :class="{
            'is-active': route.query.thread_id === item.id,
            'is-dragging': swipingSessionId === item.id,
          }"
          :style="{ transform: `translateX(${rowOffset(item.id)}px)` }"
          type="button"
          :aria-current="route.query.thread_id === item.id ? 'page' : undefined"
          :aria-busy="chatSessions.respondingThreadIds.has(item.id) || undefined"
          @click="openConversation(item.id)"
          @contextmenu.prevent="openContextMenu($event, item)"
          @pointerdown="onRowPointerDown($event, item.id)"
          @pointermove="onRowPointerMove($event, item.id)"
          @pointerup="onRowPointerUp($event, item.id)"
          @pointercancel="onRowPointerCancel($event, item.id)"
        >
          <MessageSquare :size="14" />
          <span class="item-title">{{ item.title }}</span>
          <DotsMatrix v-if="chatSessions.respondingThreadIds.has(item.id)" class="item-dots" />
          <span v-else-if="chatSessions.isUnread(item.id)" class="item-unread" aria-hidden="true" />
        </button>
      </div>
    </section>

    <!-- 翻页状态提示 -->
    <p v-if="chatSessions.threadsLoading" class="list-tip">加载中…</p>
    <p v-else-if="chatSessions.threadsEnded" class="list-tip">没有更早的历史消息了</p>
    <Teleport to="body">
      <div
        v-if="contextMenu"
        ref="contextMenuRef"
        class="conversation-context-menu"
        :class="{ 'is-above': contextMenu.placement === 'above' }"
        role="menu"
        :aria-label="`${contextMenu.title} 的操作菜单`"
        :style="{
          left: `${contextMenu.x}px`,
          top: `${contextMenu.y}px`,
          '--arrow-x': `${contextMenu.arrowX}px`,
        }"
        @contextmenu.prevent
      >
        <div class="context-menu-item" role="menuitem" aria-disabled="true">
          <Pencil :size="15" aria-hidden="true" />
          <span>重命名</span>
        </div>
        <div class="context-menu-item is-danger" role="menuitem" aria-disabled="true">
          <Trash2 :size="15" aria-hidden="true" />
          <span>删除会话</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { MessageSquare, Pencil, Trash2 } from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DotsMatrix from '@/components/DotsMatrix.vue'
import { useChatSessionsStore } from '@/stores/chatSessions'
import type { ChatSession } from '@/stores/chatSessions'

interface HistoryGroup {
  label: string
  items: ChatSession[]
}

interface ContextMenuState {
  id: string
  title: string
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

// 一天跨度，分组只看落在哪一天
const DAY_MS = 24 * 60 * 60 * 1000

// 距列表底部多少像素内算触底
const SCROLL_EDGE_PX = 40
const SWIPE_ACTIONS_WIDTH = 128
const SWIPE_START_PX = 10

const route = useRoute()
const router = useRouter()
const chatSessions = useChatSessionsStore()
const listRef = ref<HTMLElement | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)
const contextMenu = ref<ContextMenuState | null>(null)
const revealedSessionId = ref<string | null>(null)
const swipingSessionId = ref<string | null>(null)
const swipeOffset = ref(0)
let swipeGesture: SwipeGesture | null = null
let suppressedClickId: string | null = null
let suppressClickTimer: ReturnType<typeof setTimeout> | undefined
// 正在自动补页，同一时刻只跑一轮
let filling = false

function rowOffset(id: string): number {
  if (swipingSessionId.value === id) return swipeOffset.value
  return revealedSessionId.value === id ? -SWIPE_ACTIONS_WIDTH : 0
}

function closeSwipeActions(): void {
  revealedSessionId.value = null
}

function onRowPointerDown(event: PointerEvent, id: string): void {
  if (event.pointerType === 'mouse' || !event.isPrimary) return
  if (suppressedClickId === id) suppressedClickId = null
  swipeGesture = {
    id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startOffset: revealedSessionId.value === id ? -SWIPE_ACTIONS_WIDTH : 0,
    horizontal: false,
  }
}

function onRowPointerMove(event: PointerEvent, id: string): void {
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
    if (revealedSessionId.value !== id) closeSwipeActions()
    swipingSessionId.value = id
  }
  swipeOffset.value = Math.max(-SWIPE_ACTIONS_WIDTH, Math.min(0, gesture.startOffset + dx))
}

function onRowPointerUp(event: PointerEvent, id: string): void {
  const gesture = swipeGesture
  if (!gesture || gesture.id !== id || gesture.pointerId !== event.pointerId) return
  if (gesture.horizontal) {
    revealedSessionId.value = swipeOffset.value < -SWIPE_ACTIONS_WIDTH / 2 ? id : null
    suppressedClickId = id
    if (suppressClickTimer) clearTimeout(suppressClickTimer)
    suppressClickTimer = setTimeout(() => {
      suppressedClickId = null
      suppressClickTimer = undefined
    }, 400)
  }
  swipeGesture = null
  swipingSessionId.value = null
  swipeOffset.value = 0
}

function onRowPointerCancel(event: PointerEvent, id: string): void {
  if (swipeGesture?.id !== id || swipeGesture.pointerId !== event.pointerId) return
  swipeGesture = null
  swipingSessionId.value = null
  swipeOffset.value = 0
}

function closeContextMenu(): void {
  contextMenu.value = null
}

async function openContextMenu(event: MouseEvent, item: ChatSession): Promise<void> {
  if (window.matchMedia('(hover: none)').matches) return
  closeSwipeActions()
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const keyboardTriggered = event.clientX === 0 && event.clientY === 0
  const pointerX = keyboardTriggered ? rect.left + 24 : event.clientX
  const pointerY = keyboardTriggered ? rect.bottom : event.clientY
  const initialMenu: ContextMenuState = {
    id: item.id,
    title: item.title,
    x: pointerX,
    y: pointerY,
    arrowX: 16,
    placement: 'below',
  }
  contextMenu.value = initialMenu

  await nextTick()
  const menu = contextMenuRef.value
  if (!menu || contextMenu.value?.id !== item.id) return
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

function onDocumentPointerDown(event: PointerEvent): void {
  if (contextMenuRef.value?.contains(event.target as Node)) return
  closeContextMenu()
  if (!revealedSessionId.value) return
  const row = event.target instanceof Element ? event.target.closest('.history-swipe-item') : null
  if (row?.getAttribute('data-session-id') !== revealedSessionId.value) closeSwipeActions()
}

function onDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') closeContextMenu()
}

// 剩余空间是否在触底范围内，没出滚动条时也算到底
function atBottom(list: HTMLElement): boolean {
  return list.scrollHeight - list.scrollTop - list.clientHeight <= SCROLL_EDGE_PX
}

// 触底就一直往前翻，直到撑出滚动条或取完
async function fillViewport(): Promise<void> {
  const list = listRef.value
  if (!list || filling || !atBottom(list) || chatSessions.threadsEnded) return

  filling = true
  try {
    while (atBottom(list) && !chatSessions.threadsEnded) {
      const before = chatSessions.sessions.length
      await chatSessions.loadMoreThreads()
      await nextTick()
      // 一页没拿到新会话就停，别把循环卡死
      if (chatSessions.sessions.length === before) break
    }
  } finally {
    filling = false
  }
}

// 滚动和窗口变高都重新判断一次
function checkViewport(): void {
  void fillViewport()
}

function onListScroll(): void {
  checkViewport()
  closeSwipeActions()
}

// 按创建时间落在今天/昨天/更早哪一档
function groupLabel(createdAt: number, todayStart: number): string {
  if (createdAt >= todayStart) return '今天'
  if (createdAt >= todayStart - DAY_MS) return '昨天'
  return '更早'
}

// 先按创建时间倒序，同档的会话才连在一起
const groups = computed<HistoryGroup[]>(() => {
  const todayStart = new Date().setHours(0, 0, 0, 0)
  const sorted = [...chatSessions.sessions].sort((a, b) => b.createdAt - a.createdAt)
  const result: HistoryGroup[] = []
  for (const session of sorted) {
    const label = groupLabel(session.createdAt, todayStart)
    const last = result[result.length - 1]
    if (last?.label === label) last.items.push(session)
    else result.push({ label, items: [session] })
  }
  return result
})

function openConversation(threadId: string): void {
  if (suppressedClickId === threadId) {
    suppressedClickId = null
    return
  }
  if (revealedSessionId.value === threadId) {
    closeSwipeActions()
    return
  }
  closeSwipeActions()
  closeContextMenu()
  void router.push({ name: 'chat-index', query: { thread_id: threadId } })
}

// 首页到手或列表变化后补页，窗口变高同理
watch(() => chatSessions.sessions.length, checkViewport, { flush: 'post' })

onMounted(() => {
  window.addEventListener('resize', checkViewport)
  window.addEventListener('resize', closeContextMenu)
  window.addEventListener('scroll', closeContextMenu, true)
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeydown)
  checkViewport()
})

onUnmounted(() => {
  if (suppressClickTimer) clearTimeout(suppressClickTimer)
  window.removeEventListener('resize', checkViewport)
  window.removeEventListener('resize', closeContextMenu)
  window.removeEventListener('scroll', closeContextMenu, true)
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})
</script>

<style scoped>
.history-group {
  padding: 4px 0;
}
.group-label {
  padding: 6px 20px;
  font-size: 12px;
  font-weight: 500;
  color: #909399;
}
.history-swipe-item {
  position: relative;
  overflow: hidden;
}
.history-actions {
  position: absolute;
  inset: 0 0 0 auto;
  display: flex;
  width: 128px;
}
.swipe-action {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 0;
  padding: 0;
  border: 0;
  color: #fff;
  font-size: 11px;
  opacity: 1;
}
.swipe-action.is-rename {
  background: #8c98a8;
}
.swipe-action.is-delete {
  background: #e56565;
}
.history-item {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 16px;
  border: none;
  background: #fafafa;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  touch-action: pan-y;
  -webkit-tap-highlight-color: transparent;
  transition: transform 200ms cubic-bezier(0.2, 0.75, 0.25, 1);
}
.history-item.is-dragging {
  transition: none;
}
.history-item:active {
  background: #eceff3;
}
.history-item.is-active {
  background: #e9ebee;
}
@media (hover: hover) {
  .history-item:hover {
    background: #eceff3;
  }
}
@media (any-pointer: coarse) {
  .history-item {
    min-height: 42px;
  }
  .swipe-action {
    min-height: 42px;
  }
}
.item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.item-dots {
  margin-left: 2px;
  opacity: 0.75;
}
.item-unread {
  width: 8px;
  height: 8px;
  flex: none;
  margin-left: 2px;
  border-radius: 50%;
  background: #2f8cff;
}
.list-tip {
  margin: 0;
  padding: 10px 20px 14px;
  color: #a8adb3;
  font-size: 12px;
  text-align: center;
}
.conversation-context-menu {
  position: fixed;
  z-index: 2000;
  width: 164px;
  padding: 5px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 30px rgb(25 35 50 / 14%);
  transform-origin: var(--arrow-x) top;
  animation: context-menu-appear 160ms cubic-bezier(0.2, 1, 0.3, 1) both;
}
.conversation-context-menu::before {
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
.conversation-context-menu.is-above {
  transform-origin: var(--arrow-x) bottom;
}
.conversation-context-menu.is-above::before {
  top: auto;
  bottom: -5px;
  border: 0;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}
.context-menu-item {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 38px;
  padding: 0 11px;
  border-radius: 8px;
  color: #303133;
  font-size: 13px;
}
.context-menu-item.is-danger {
  color: #d35b5b;
}
@keyframes context-menu-appear {
  from {
    opacity: 0;
    transform: scale(0.94) translateY(-3px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .conversation-context-menu {
    animation: none;
  }
  .history-item {
    transition: none;
  }
}
</style>
