<template>
  <div class="conversation-list">
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
        @click="openConversation(item.id)"
      >
        <MessageSquare :size="14" />
        <span class="item-title">{{ item.title }}</span>
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { MessageSquare } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatSessionsStore } from '@/stores/chatSessions'
import type { ChatSession } from '@/stores/chatSessions'

interface HistoryGroup {
  label: string
  items: ChatSession[]
}

const route = useRoute()
const router = useRouter()
const chatSessions = useChatSessionsStore()
const groups = computed<HistoryGroup[]>(() =>
  chatSessions.sessions.length ? [{ label: '今天', items: chatSessions.sessions }] : [],
)

function openConversation(threadId: string): void {
  void router.push({ name: 'chat-index', query: { thread_id: threadId } })
}
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
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
