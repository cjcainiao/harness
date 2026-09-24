<template>
  <header class="session-header">
    <div class="session-identity">
      <button
        class="header-action sidebar-toggle"
        type="button"
        aria-label="切换侧栏"
        aria-controls="chat-sidebar"
        :aria-expanded="sidebarOpen"
        @click="emit('toggle-sidebar')"
      >
        <Menu :size="18" :stroke-width="1.8" aria-hidden="true" />
      </button>
      <FolderClosed class="session-icon" :size="16" :stroke-width="1.6" aria-hidden="true" />
      <h1 class="session-title" :title="title">{{ title }}</h1>
    </div>
  </header>
</template>

<script setup lang="ts">
import { FolderClosed, Menu } from 'lucide-vue-next'

defineProps<{
  title: string
  sidebarOpen: boolean
}>()
const emit = defineEmits<{
  'toggle-sidebar': []
}>()
</script>

<style scoped>
.session-header {
  display: flex;
  align-items: center;
  height: 44px;
  min-width: 0;
  padding: 0 17px 0 20px;
  border-bottom: 1px solid #e8e9eb;
  background: #fff;
}
.session-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.session-icon {
  flex-shrink: 0;
  color: #565d64;
}
.session-title {
  overflow: hidden;
  color: #202327;
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    color 0.16s ease;
}
.header-action:active,
.header-action:focus-visible {
  background: #f2f3f5;
  color: #343940;
}
@media (hover: hover) {
  .header-action:hover {
    background: #f2f3f5;
    color: #343940;
  }
}
.header-action:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 1px;
}
.sidebar-toggle {
  display: none;
}
@media (any-pointer: coarse) {
  .header-action {
    min-width: 40px;
    height: 40px;
  }
}
@media (max-width: 600px) {
  .session-header {
    padding: 0 10px 0 14px;
  }
}
@media (max-width: 700px) {
  .sidebar-toggle {
    display: inline-flex;
    flex-shrink: 0;
    margin-left: -5px;
  }
}
</style>
