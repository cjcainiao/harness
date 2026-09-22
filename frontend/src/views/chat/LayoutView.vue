<template>
  <div class="chat-layout">
    <aside class="chat-sidebar">
      <!-- 新建会话入口 -->
      <div class="sidebar-header">
        <span class="new-chat">新建对话</span>
      </div>
      <!-- 会话/项目历史列表 -->
      <ConversationList class="sidebar-history" />
    </aside>
    <main class="chat-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import ConversationList from './components/ConversationList.vue'
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
}
.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
}
.sidebar-header {
  padding: 12px 16px;
}
.sidebar-history {
  flex: 1;
  overflow-y: auto;
}
.chat-main {
  flex: 1;
  min-width: 0;
}
</style>
