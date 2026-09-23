<template>
  <div class="chat-index">
    <SessionHeader
      :title="sessionTitle"
      :has-messages="messages.length > 0"
      :navigator-visible="navigatorVisible"
      :sidebar-open="sidebarOpen"
      @toggle-navigator="navigatorVisible = !navigatorVisible"
      @toggle-sidebar="emit('toggle-sidebar')"
      @scroll-top="messageStreamRef?.scrollToTop()"
      @scroll-bottom="messageStreamRef?.scrollToBottom()"
    />
    <!-- 消息流式渲染区 -->
    <MessageStream
      ref="messageStreamRef"
      class="chat-messages"
      :messages="messages"
      :show-navigator="navigatorVisible"
    />
    <!-- 底部固定区 -->
    <footer class="chat-bottom">
      <ChatInput />
      <UsageBar />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MessageStream from './components/message/MessageStream.vue'
import SessionHeader from './components/message/SessionHeader.vue'
import type { ChatTurn } from './components/message/messageTypes'
import ChatInput from './components/input/ChatInput.vue'
import UsageBar from './components/input/UsageBar.vue'

withDefaults(defineProps<{ sidebarOpen?: boolean }>(), { sidebarOpen: false })
const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const sessionTitle = ref('新对话')
const messages = ref<ChatTurn[]>([])
const navigatorVisible = ref(true)
const messageStreamRef = ref<InstanceType<typeof MessageStream>>()
</script>

<style scoped>
.chat-index {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.chat-messages {
  flex: 1;
  min-height: 0;
  overflow: visible;
}
.chat-bottom {
  flex-shrink: 0;
  padding-top: 12px;
}
</style>
