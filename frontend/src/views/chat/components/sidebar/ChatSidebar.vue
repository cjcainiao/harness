<!--左侧导航栏-->
<template>
  <aside class="chat-sidebar">
    <!-- 顶部菜单，固定 -->
    <header class="sidebar-top">
      <div class="sidebar-top-row">
        <div class="sidebar-logo">Harness</div>
        <button
          class="sidebar-collapse"
          type="button"
          aria-label="收起侧边栏"
          aria-controls="chat-sidebar"
          @click="emit('collapse-sidebar')"
        >
          <PanelLeftClose :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </div>
      <nav class="sidebar-menu">
        <button class="menu-item" type="button" @click="startNewConversation">
          <SquarePen :size="16" />
          <span>新对话</span>
        </button>
        <button
          class="menu-item"
          type="button"
          aria-haspopup="dialog"
          :aria-expanded="searchVisible"
          @click="searchVisible = true"
        >
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
      <ElPopover
        v-model:visible="settingsVisible"
        placement="top"
        trigger="click"
        role="dialog"
        popper-class="sidebar-settings-popper"
        :popper-style="settingsPopperStyle"
        :width="272"
        :offset="10"
        :show-arrow="true"
        :hide-after="0"
        :persistent="false"
      >
        <template #reference>
          <button
            ref="settingsButtonRef"
            class="menu-item menu-icon"
            type="button"
            data-sidebar-keep-open
            aria-haspopup="dialog"
            :aria-expanded="settingsVisible"
            aria-label="设置"
          >
            <Settings :size="16" />
          </button>
        </template>

        <div class="settings-menu" aria-label="设置">
          <div class="settings-options">
            <button
              v-for="option in settingOptions"
              :key="option.id"
              class="settings-option"
              type="button"
              @click="selectSetting(option.id)"
            >
              <component
                :is="option.icon"
                class="settings-option-icon"
                :size="15"
                :stroke-width="1.7"
                aria-hidden="true"
              />
              <span class="settings-option-copy">
                <span class="settings-option-title">{{ option.label }}</span>
                <span class="settings-option-description">{{ option.description }}</span>
              </span>
              <ArrowUpRight
                v-if="option.route"
                class="settings-option-arrow"
                :size="14"
                :stroke-width="1.8"
                aria-hidden="true"
              />
              <Check
                v-else-if="option.id === selectedSettingId"
                class="settings-option-check"
                :size="14"
                :stroke-width="1.8"
                aria-hidden="true"
              />
            </button>
          </div>
        </div>
      </ElPopover>
    </footer>
    <!-- 搜索弹窗，Teleport 到 body，不受侧栏收起时的 inert 影响 -->
    <ConversationSearch v-model:visible="searchVisible" />
  </aside>
</template>

<script setup lang="ts">
import { ElPopover } from 'element-plus'
import type { Component } from 'vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ArrowUpRight,
  Check,
  PanelLeftClose,
  Search,
  Settings,
  SlidersHorizontal,
  SquarePen,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useChatSessionsStore } from '@/stores/chatSessions'

import ConversationList from './ConversationList.vue'
import ConversationSearch from './ConversationSearch.vue'

interface SettingOption {
  id: string
  label: string
  description: string
  icon: Component
  route?: string
}

const props = withDefaults(defineProps<{ sidebarVisible?: boolean }>(), { sidebarVisible: true })
const emit = defineEmits<{ 'collapse-sidebar': [] }>()
const router = useRouter()
const chatSessions = useChatSessionsStore()

const isSettingsOpen = ref(false)
const searchVisible = ref(false)
// 气泡挂在 body 上，侧栏不可见时必须显式关闭
const settingsVisible = computed({
  get: () => isSettingsOpen.value && props.sidebarVisible,
  set: (visible) => {
    if (props.sidebarVisible) isSettingsOpen.value = visible
  },
})

watch(
  () => props.sidebarVisible,
  (visible) => {
    if (!visible) isSettingsOpen.value = false
  },
)

// 居中于按钮且不出屏所需的最大宽度
const settingsPopperStyle = ref<Record<string, string>>({})
const settingsButtonRef = ref<HTMLElement | null>(null)

// 更新气泡宽度：居中需要两侧都有空间
function updateSettingsPopperWidth(): void {
  const anchor = settingsButtonRef.value
  if (!anchor) return

  const viewport = document.documentElement.clientWidth
  const rect = anchor.getBoundingClientRect()
  // 居中时两侧各占一半，取较小一侧算总宽
  const centered = Math.min(rect.left, viewport - rect.right) * 2 - 24
  settingsPopperStyle.value = {
    maxWidth: `${Math.min(272, Math.max(200, Math.round(centered)))}px`,
  }
}

// 变窄时收窄气泡并收起侧栏，避免被 popper 推回后偏离按钮
function onViewportResize(): void {
  updateSettingsPopperWidth()
  if (document.documentElement.clientWidth <= 700 && !props.sidebarVisible) {
    isSettingsOpen.value = false
  }
}

// 打开前先算好宽度，避免首帧用旧位置
watch(settingsVisible, (visible) => {
  if (visible) updateSettingsPopperWidth()
})

let buttonObserver: ResizeObserver | undefined

onMounted(() => {
  // 打开侧栏时同步服务端会话
  void chatSessions.loadThreads()
  window.addEventListener('resize', onViewportResize)
  if (settingsButtonRef.value) {
    buttonObserver = new ResizeObserver(() => updateSettingsPopperWidth())
    buttonObserver.observe(settingsButtonRef.value)
  }
  updateSettingsPopperWidth()
})

onUnmounted(() => {
  window.removeEventListener('resize', onViewportResize)
  buttonObserver?.disconnect()
})

const selectedSettingId = ref('general')
const settingOptions: SettingOption[] = [
  {
    id: 'general',
    label: '通用设置',
    description: '模型与系统配置',
    icon: SlidersHorizontal,
    route: '/config',
  },
  {
    id: 'permission',
    label: '访问权限',
    description: '工具调用审批方式',
    icon: Settings,
  },
]

function selectSetting(id: string): void {
  const option = settingOptions.find((item) => item.id === id)
  if (!option) return

  selectedSettingId.value = id
  isSettingsOpen.value = false
  if (option.route) void router.push(option.route)
}

function startNewConversation(): void {
  const threadId = chatSessions.createSession()
  void router.push({ name: 'chat-index', query: { thread_id: threadId } })
}
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
.sidebar-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 2px 12px;
}
.sidebar-logo {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.sidebar-collapse {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #565d64;
  cursor: pointer;
}
.sidebar-collapse:hover,
.sidebar-collapse:active {
  background: #eceff3;
}
.sidebar-collapse:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 1px;
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
  /* 滚动条先占位不上色，悬停才显形，显隐切换不会挤动列表 */
  scrollbar-color: transparent transparent;
}
.sidebar-history::-webkit-scrollbar-thumb {
  background: transparent;
}
.sidebar-history:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}
.sidebar-history:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
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
.settings-menu {
  padding: 0;
}
.settings-options {
  display: grid;
  gap: 2px;
}
.settings-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 46px;
  padding: 7px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #303030;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}
.settings-option:active {
  background: #eceef1;
}
.settings-option-icon {
  flex-shrink: 0;
  color: #555b63;
}
.settings-option-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 17px;
}
.settings-option-title {
  font-size: 13px;
  font-weight: 500;
}
.settings-option-description {
  color: #888;
  font-size: 11.5px;
}
.settings-option-arrow,
.settings-option-check {
  flex-shrink: 0;
  margin-left: auto;
  color: #8b9098;
}
.settings-option-check {
  color: #303133;
}
@media (hover: hover) {
  .settings-option:hover {
    background: #f3f4f6;
  }
}
@media (any-pointer: coarse) {
  .settings-option {
    min-height: 48px;
  }
}
/* 气泡挂在 body 上，宽度由 settingsPopperStyle 按视口计算 */
:global(.sidebar-settings-popper) .settings-option-title {
  white-space: nowrap;
}
</style>
