<template>
  <div class="chat-layout" @keydown.esc="sidebarOpen = false">
    <!-- 左侧导航栏 -->
    <ChatSidebar
      id="chat-sidebar"
      :class="{ 'is-open': sidebarOpen }"
      :inert="mobileViewport && !sidebarOpen"
      :aria-hidden="mobileViewport && !sidebarOpen"
      @click="onSidebarClick"
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
          :sidebar-open="sidebarOpen"
          @toggle-sidebar="sidebarOpen = !sidebarOpen"
        />
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import ChatSidebar from './components/sidebar/ChatSidebar.vue'

const sidebarOpen = ref(false)
const mobileViewport = ref(false)
let mobileQuery: MediaQueryList | undefined

function updateMobileViewport() {
  mobileViewport.value = mobileQuery?.matches ?? false
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 700px)')
  updateMobileViewport()
  mobileQuery.addEventListener('change', updateMobileViewport)
})

onUnmounted(() => mobileQuery?.removeEventListener('change', updateMobileViewport))

function onSidebarClick(event: MouseEvent) {
  if ((event.target as Element).closest('button')) sidebarOpen.value = false
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
    transition-duration: 0s;
  }
}
</style>
