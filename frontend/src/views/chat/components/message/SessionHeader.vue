<template>
  <header class="session-header">
    <div class="session-identity">
      <button
        class="header-action icon-action sidebar-toggle"
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

    <div v-if="hasMessages" class="session-actions">
      <ElDropdown trigger="click" placement="bottom-end" @command="onMenuCommand">
        <button class="header-action icon-action" type="button" aria-label="更多会话操作">
          <Ellipsis :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem command="top">回到顶部</ElDropdownItem>
            <ElDropdownItem command="bottom">回到底部</ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>

      <ElTooltip content="复制当前页面链接" placement="bottom" :show-after="300">
        <button class="header-action share-action" type="button" @click="copyPageLink">
          <Share2 :size="15" :stroke-width="1.7" aria-hidden="true" />
          <span>分享</span>
        </button>
      </ElTooltip>

      <ElTooltip
        :content="navigatorVisible ? '隐藏消息定位条' : '显示消息定位条'"
        placement="bottom"
        :show-after="300"
      >
        <button
          class="header-action icon-action"
          type="button"
          :aria-label="navigatorVisible ? '隐藏消息定位条' : '显示消息定位条'"
          :aria-pressed="navigatorVisible"
          @click="emit('toggle-navigator')"
        >
          <List :size="16" :stroke-width="1.7" aria-hidden="true" />
        </button>
      </ElTooltip>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Ellipsis, FolderClosed, List, Menu, Share2 } from 'lucide-vue-next'
import { ElDropdown, ElDropdownItem, ElDropdownMenu, ElMessage, ElTooltip } from 'element-plus'
import 'element-plus/es/components/dropdown/style/css'
import 'element-plus/es/components/dropdown-item/style/css'
import 'element-plus/es/components/dropdown-menu/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/tooltip/style/css'

defineProps<{
  title: string
  navigatorVisible: boolean
  hasMessages: boolean
  sidebarOpen: boolean
}>()
const emit = defineEmits<{
  'toggle-navigator': []
  'toggle-sidebar': []
  'scroll-top': []
  'scroll-bottom': []
}>()

function onMenuCommand(command: string | number | object) {
  if (command === 'top') emit('scroll-top')
  if (command === 'bottom') emit('scroll-bottom')
}

async function copyPageLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    ElMessage.success('页面链接已复制')
  } catch {
    ElMessage.error('复制失败，请重试')
  }
}
</script>

<style scoped>
.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 44px;
  min-width: 0;
  padding: 0 17px 0 20px;
  border-bottom: 1px solid #e8e9eb;
  background: #fff;
}
.session-identity,
.session-actions {
  display: flex;
  align-items: center;
  min-width: 0;
}
.session-identity {
  gap: 10px;
  flex: 1;
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
.session-actions {
  gap: 7px;
  flex-shrink: 0;
  color: #7b8188;
}
.header-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 28px;
  padding: 0 7px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
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
.icon-action {
  width: 28px;
  padding: 0;
}
.share-action {
  padding: 0 6px;
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
  .session-actions {
    gap: 2px;
  }
  .share-action span {
    display: none;
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
