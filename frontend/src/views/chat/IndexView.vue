<template>
  <div class="chat-index">
    <!-- 消息流式渲染区 -->
    <MessageStream class="chat-messages" />
    <!-- 消息输入区 -->
    <ChatInput class="chat-input" />
  </div>
</template>

<script setup lang="ts">
import MessageStream from './components/MessageStream.vue'
import ChatInput from './components/ChatInput.vue'
</script>

<style scoped>
.chat-index {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
}
.chat-input {
  flex-shrink: 0;
  border-top: 1px solid #e4e7ed;
}
</style>
