<!--会话历史列表-->
<template>
  <div ref="listRef" class="conversation-list" @scroll="checkViewport">
    <!-- 会话历史列表 -->
    <section v-for="group in groups" :key="group.label" class="history-group">
      <h4 class="group-label">{{ group.label }}</h4>
      <button
        v-for="item in group.items"
        :key="item.id"
        class="history-item"
        :class="{ 'is-active': route.query.thread_id === item.id }"
        type="button"
        :aria-current="route.query.thread_id === item.id ? 'page' : undefined"
        :aria-busy="chatSessions.respondingThreadIds.has(item.id) || undefined"
        @click="openConversation(item.id)"
      >
        <MessageSquare :size="14" />
        <span class="item-title">{{ item.title }}</span>
        <DotsMatrix v-if="chatSessions.respondingThreadIds.has(item.id)" class="item-dots" />
        <span v-else-if="chatSessions.isUnread(item.id)" class="item-unread" aria-hidden="true" />
      </button>
    </section>

    <!-- 翻页状态提示 -->
    <p v-if="chatSessions.threadsLoading" class="list-tip">加载中…</p>
    <p v-else-if="chatSessions.threadsEnded" class="list-tip">没有更早的历史消息了</p>
  </div>
</template>

<script setup lang="ts">
import { MessageSquare } from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DotsMatrix from '@/components/DotsMatrix.vue'
import { useChatSessionsStore } from '@/stores/chatSessions'
import type { ChatSession } from '@/stores/chatSessions'

interface HistoryGroup {
  label: string
  items: ChatSession[]
}

// 一天跨度，分组只看落在哪一天
const DAY_MS = 24 * 60 * 60 * 1000

// 距列表底部多少像素内算触底
const SCROLL_EDGE_PX = 40

const route = useRoute()
const router = useRouter()
const chatSessions = useChatSessionsStore()
const listRef = ref<HTMLElement | null>(null)
// 正在自动补页，同一时刻只跑一轮
let filling = false

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
  void router.push({ name: 'chat-index', query: { thread_id: threadId } })
}

// 首页到手或列表变化后补页，窗口变高同理
watch(() => chatSessions.sessions.length, checkViewport, { flush: 'post' })

onMounted(() => {
  window.addEventListener('resize', checkViewport)
  checkViewport()
})

onUnmounted(() => window.removeEventListener('resize', checkViewport))
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
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
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
</style>
