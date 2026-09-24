<template>
  <div class="chat-index">
    <SessionHeader
      :title="sessionTitle"
      :sidebar-open="sidebarOpen"
      @toggle-sidebar="emit('toggle-sidebar')"
    />
    <!-- 消息显示区 -->
    <div class="chat-messages" />
    <!-- 底部固定区 -->
    <footer class="chat-bottom">
      <ChatInput />
      <UsageBar />
    </footer>
  </div>
</template>

<script setup lang="ts">
import ChatInput from './components/input/ChatInput.vue'
import UsageBar from './components/input/UsageBar.vue'
import SessionHeader from './components/message/SessionHeader.vue'

withDefaults(defineProps<{ sidebarOpen?: boolean }>(), { sidebarOpen: false })
const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const sessionTitle = '新对话'
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
}
.chat-bottom {
  flex-shrink: 0;
  padding-top: 12px;
}
</style>
