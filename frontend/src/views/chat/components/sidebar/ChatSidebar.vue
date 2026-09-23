<template>
  <aside class="chat-sidebar">
    <!-- 顶部菜单，固定 -->
    <header class="sidebar-top">
      <div class="sidebar-logo">
        <span>Harness</span>
      </div>
      <nav class="sidebar-menu">
        <button class="menu-item" type="button">
          <SquarePen :size="16" />
          <span>新对话</span>
        </button>
        <button class="menu-item" type="button">
          <Search :size="16" />
          <span>搜索</span>
        </button>
      </nav>
    </header>
    <!-- 中间：会话/项目历史列表，可滚动 -->
    <ConversationList class="sidebar-history" />
    <!-- 底部：用户设置，固定 -->
    <footer class="sidebar-user">
      <div class="user-info">
        <span class="user-avatar">U</span>
        <span class="user-name">用户</span>
      </div>
      <button class="menu-item menu-icon" type="button">
        <Settings :size="16" />
      </button>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { Search, Settings, SquarePen } from 'lucide-vue-next'

import ConversationList from './ConversationList.vue'
</script>

<style scoped>
.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
}
.sidebar-top {
  flex-shrink: 0;
}
.sidebar-logo {
  padding: 14px 12px 6px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.sidebar-menu {
  padding: 4px 8px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}
.menu-item:active {
  background: #eceff3;
}
@media (hover: hover) {
  .menu-item:hover {
    background: #eceff3;
  }
}
@media (any-pointer: coarse) {
  .menu-item {
    min-height: 42px;
  }
  .menu-icon {
    min-width: 42px;
  }
}
.menu-icon {
  width: auto;
  justify-content: center;
}
.sidebar-history {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.sidebar-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 8px;
  border-top: 1px solid #e4e7ed;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  min-width: 0;
}
.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}
.user-name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
