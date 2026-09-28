<template>
  <div class="chat-layout" @keydown.esc="sidebarOpen = false">
    <!-- 左侧导航栏 -->
    <ChatSidebar
      id="chat-sidebar"
      :class="{ 'is-open': sidebarOpen, 'is-collapsed': !mobileViewport && sidebarCollapsed }"
      :inert="mobileViewport ? !sidebarOpen : sidebarCollapsed"
      :aria-hidden="mobileViewport ? !sidebarOpen : sidebarCollapsed"
      @click="onSidebarClick"
      @collapse-sidebar="collapseSidebar"
    />
    <button
      v-if="sidebarOpen"
      class="sidebar-backdrop"
      type="button"
      aria-label="关闭侧栏"
      @click="sidebarOpen = false"
    />
    <!-- 右侧内容区 -->
    <main class="chat-main">
      <router-view v-slot="{ Component }">
        <component
          :is="Component"
          :sidebar-open="mobileViewport ? sidebarOpen : !sidebarCollapsed"
          @toggle-sidebar="toggleSidebar"
        />
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import ChatSidebar from './components/sidebar/ChatSidebar.vue'

const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false)
const mobileViewport = ref(false)
let mobileQuery: MediaQueryList | undefined

// 移动端和桌面端分别维护侧栏展开状态
function updateMobileViewport() {
  mobileViewport.value = mobileQuery?.matches ?? false
  if (!mobileViewport.value) sidebarOpen.value = false
}

function collapseSidebar(): void {
  if (mobileViewport.value) sidebarOpen.value = false
  else sidebarCollapsed.value = true
}

function toggleSidebar(): void {
  if (mobileViewport.value) sidebarOpen.value = !sidebarOpen.value
  else sidebarCollapsed.value = !sidebarCollapsed.value
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 700px)')
  updateMobileViewport()
  mobileQuery.addEventListener('change', updateMobileViewport)
})

onUnmounted(() => mobileQuery?.removeEventListener('change', updateMobileViewport))

function onSidebarClick(event: MouseEvent) {
  if (mobileViewport.value && (event.target as Element).closest('button')) sidebarOpen.value = false
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
}
.chat-main {
  flex: 1;
  min-width: 0;
  background: #fff;
}
.chat-sidebar {
  overflow: hidden;
  transition:
    width 0.2s ease,
    border-color 0.2s ease;
}
.chat-sidebar.is-collapsed {
  width: 0;
  border-right-color: transparent;
}
.sidebar-backdrop {
  display: none;
}
@media (max-width: 700px) {
  .chat-layout {
    height: 100dvh;
  }
  .chat-sidebar {
    position: fixed;
    z-index: 31;
    inset: 0 auto 0 0;
    width: min(280px, calc(100vw - 56px));
    background: #f8faff;
    box-shadow: 8px 0 24px rgba(20, 24, 29, 0.12);
    transform: translateX(-105%);
    transition: transform 0.2s ease;
  }
  .chat-sidebar.is-open {
    transform: translateX(0);
  }
  .sidebar-backdrop {
    position: fixed;
    z-index: 30;
    inset: 0;
    display: block;
    width: 100%;
    padding: 0;
    border: 0;
    background: rgba(18, 22, 28, 0.3);
  }
}
@media (prefers-reduced-motion: reduce) {
  .chat-sidebar {
    transition: none;
  }
}
</style>
