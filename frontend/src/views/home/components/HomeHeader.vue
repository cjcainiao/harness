<!--首页顶部导航-->
<template>
  <div class="home-header-inner">
    <!-- 品牌标识 -->
    <div class="header-brand">
      <span class="brand-name">Harness</span>
    </div>
    <!-- 搜索框 -->
    <div
      class="header-search"
      role="button"
      tabindex="0"
      aria-haspopup="dialog"
      :aria-expanded="searchVisible"
      @click="searchVisible = true"
      @keydown.enter.prevent="searchVisible = true"
      @keydown.space.prevent="searchVisible = true"
    >
      <Search class="header-search-icon" :size="15" :stroke-width="1.8" aria-hidden="true" />
      <input
        class="header-search-input"
        type="text"
        placeholder="搜索"
        aria-label="搜索"
        readonly
        tabindex="-1"
      />
      <kbd class="header-search-kbd">Ctrl K</kbd>
    </div>
    <!-- 右侧操作区 -->
    <div class="header-actions">
      <!-- 顶部菜单 -->
      <el-menu class="header-menu" mode="horizontal" :ellipsis="false">
        <el-menu-item index="version">
          <span class="menu-label">v0.0.0</span>
        </el-menu-item>
        <el-menu-item index="doc">
          <span class="menu-label">文档</span>
        </el-menu-item>
        <el-menu-item index="chat">
          <span class="menu-label">对话</span>
        </el-menu-item>
        <el-menu-item index="config">
          <span class="menu-label">设置</span>
        </el-menu-item>
      </el-menu>
      <!-- 主题切换与分隔线 -->
      <div class="theme-group">
        <span class="actions-divider" aria-hidden="true" />
        <ElTooltip
          :content="isDark ? '切换到浅色主题' : '切换到深色主题'"
          placement="bottom"
          :fallback-placements="['bottom', 'top']"
          :show-after="300"
          :enterable="false"
          :trigger="['hover', 'focus']"
          :disabled="!canHover"
        >
          <button
            class="theme-switch"
            :class="{ 'is-dark': isDark }"
            type="button"
            role="switch"
            :aria-checked="isDark"
            aria-label="切换主题"
            @click="toggleTheme"
          >
            <span class="theme-knob">
              <Sun class="knob-icon is-sun" :size="13" :stroke-width="1.9" aria-hidden="true" />
              <Moon class="knob-icon is-moon" :size="13" :stroke-width="1.9" aria-hidden="true" />
            </span>
          </button>
        </ElTooltip>
        <span class="actions-divider" aria-hidden="true" />
      </div>
      <!-- GitHub 入口 -->
      <div class="github-group">
        <ElTooltip
          content="GitHub 仓库"
          placement="bottom"
          :fallback-placements="['bottom', 'top']"
          :show-after="300"
          :enterable="false"
          :trigger="['hover', 'focus']"
          :disabled="!canHover"
        >
          <button class="header-github" type="button" aria-label="GitHub">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" aria-hidden="true">
              <path
                d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
              />
            </svg>
          </button>
        </ElTooltip>
      </div>
    </div>
    <!-- 搜索弹窗 -->
    <HomeSearch v-model:visible="searchVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Moon, Search, Sun } from 'lucide-vue-next'
import { ElTooltip } from 'element-plus'
import 'element-plus/es/components/tooltip/style/css'

import HomeSearch from './HomeSearch.vue'

// 深色态
const isDark = ref(false)
const canHover = window.matchMedia('(hover: hover)').matches
const searchVisible = ref(false)

// 切换主题
function toggleTheme(): void {
  isDark.value = !isDark.value
}
</script>

<style scoped>
.home-header-inner {
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
  height: 100%;
}
/* 品牌标识 */
.header-brand {
  display: flex;
  flex-shrink: 0;
  align-items: center;
}
.brand-name {
  color: #1f2328;
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
}
/* 搜索框 */
.header-search {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 7px;
  width: 220px;
  height: 34px;
  padding: 0 8px 0 10px;
  border-radius: 9px;
  background: #f4f5f6;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.header-search:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
.header-search-icon {
  flex: 0 0 auto;
  color: #6b7280;
}
.header-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  color: #24292f;
  font-size: 14px;
}
.header-search-input:focus {
  outline: none;
}
.header-search-input::placeholder {
  color: #6b7280;
}
.header-search-kbd {
  flex: 0 0 auto;
  padding: 2px 6px;
  border: 1px solid #e3e6ea;
  border-radius: 6px;
  background: #fff;
  color: #6b7280;
  font-family: inherit;
  font-size: 12px;
}
/* 右侧操作区 */
.header-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}
/* 顶部菜单 */
.header-menu {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  height: 40px;
  /* 末项内边距补偿 */
  margin-right: -10px;
}
.header-menu :deep(.el-menu-item) {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  height: 40px;
  padding: 0 10px;
  border-radius: 8px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
/* 相邻菜单项间距 */
.header-menu :deep(.el-menu-item + .el-menu-item) {
  margin-left: 12px;
}
.menu-label {
  flex-shrink: 0;
  color: #213547;
  font-family:
    system-ui,
    -apple-system,
    'Segoe UI',
    Roboto,
    sans-serif;
  font-size: 16px;
  font-weight: 500;
  white-space: nowrap;
}
/* 操作区分组 */
.theme-group,
.github-group {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 14px;
}
/* 竖线分隔 */
.actions-divider {
  flex: 0 0 auto;
  width: 0;
  height: 24px;
  border-left: 1px solid #e8eaed;
}
/* 主题切换 */
.theme-switch {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  width: 44px;
  height: 26px;
  padding: 0;
  border: 1px solid #e8eaed;
  border-radius: 999px;
  background: #f4f5f6;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease;
}
.theme-knob {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-left: 1px;
  border: 1px solid #e8eaed;
  border-radius: 50%;
  background: #fff;
  color: #6b7280;
  box-shadow: 0 1px 2px rgba(31, 35, 40, 0.12);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
/* 滑块内图标 */
.knob-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transition:
    transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.2s ease;
}
.is-sun {
  transform: translate(-50%, -50%) rotate(0deg) scale(1);
  opacity: 1;
}
.is-moon {
  transform: translate(-50%, -50%) rotate(-90deg) scale(0.4);
  opacity: 0;
}
/* 深色态 */
.theme-switch.is-dark {
  border-color: #1f2328;
  background: #1f2328;
}
.theme-switch.is-dark .theme-knob {
  transform: translateX(19px);
  border-color: #1f2328;
  color: #1f2328;
}
.theme-switch.is-dark .is-sun {
  transform: translate(-50%, -50%) rotate(90deg) scale(0.4);
  opacity: 0;
}
.theme-switch.is-dark .is-moon {
  transform: translate(-50%, -50%) rotate(0deg) scale(1);
  opacity: 1;
}
/* GitHub 入口 */
.header-github {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
@media (hover: hover) {
  .header-search:hover {
    background: #eef0f2;
  }
  .theme-switch:hover {
    background: #eef0f2;
  }
  .theme-switch.is-dark:hover {
    background: #2d333b;
  }
  .header-github:hover {
    background: #f4f5f6;
    color: #1f2328;
  }
  .header-menu :deep(.el-menu-item:hover) {
    background: #f4f5f6;
  }
}
@media (any-pointer: coarse) {
  .header-search {
    height: 40px;
  }
  .header-search-kbd {
    display: none;
  }
  /* 触屏命中区外扩 */
  .theme-switch {
    position: relative;
  }
  .theme-switch::after {
    content: '';
    position: absolute;
    inset: -6px;
  }
}
/* 窄屏搜索框 */
@media (max-width: 960px) {
  .header-search {
    flex: 1 1 auto;
    width: auto;
    min-width: 0;
    max-width: 220px;
  }
}
/* 窄屏导航 */
@media (max-width: 760px) {
  .home-header-inner {
    gap: 12px;
  }
  .header-search {
    flex: 0 0 auto;
    justify-content: center;
    width: 40px;
    padding: 0;
  }
  .header-search-input,
  .header-search-kbd {
    display: none;
  }
  .header-menu {
    flex: 0 1 auto;
    min-width: 0;
    overscroll-behavior: contain;
    overflow-x: auto;
    touch-action: pan-x;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .header-menu::-webkit-scrollbar {
    display: none;
  }
  .header-actions {
    flex-shrink: 1;
    min-width: 0;
  }
}
/* 极窄屏 */
@media (max-width: 420px) {
  .actions-divider {
    display: none;
  }
  .header-actions,
  .theme-group {
    gap: 10px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .theme-switch,
  .theme-knob,
  .knob-icon {
    transition: none;
  }
}
</style>
