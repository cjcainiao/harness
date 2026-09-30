<template>
  <div class="config-layout">
    <!-- 左侧设置导航 -->
    <aside class="config-nav">
      <div class="nav-search">
        <Search class="nav-search-icon" :size="15" :stroke-width="1.8" aria-hidden="true" />
        <input
          v-model="keyword"
          class="nav-search-input"
          type="text"
          placeholder="搜索设置..."
          aria-label="搜索设置项"
        />
      </div>
      <nav class="nav-groups" aria-label="设置分类">
        <section v-for="group in navGroups" :key="group.label" class="nav-group">
          <h4 class="group-label">{{ group.label }}</h4>
          <button
            v-for="item in group.items"
            :key="item.id"
            class="nav-item"
            :class="{ 'is-active': item.routeName === route.name }"
            type="button"
            :aria-current="item.routeName === route.name ? 'page' : undefined"
            @click="openSection(item.routeName)"
          >
            <component :is="item.icon" class="nav-item-icon" :size="15" :stroke-width="1.7" />
            <span class="nav-item-label">{{ item.label }}</span>
          </button>
        </section>
      </nav>
    </aside>
    <!-- 右侧内容区 -->
    <main class="config-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cpu, Search, User } from 'lucide-vue-next'

interface NavItem {
  id: string
  label: string
  icon: Component
  routeName: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

// 导航分组，routeName 对应 router/modules/config.ts 的子路由
const navGroups: NavGroup[] = [
  {
    label: '个人',
    items: [
      { id: 'profile', label: '个人资料', icon: User, routeName: 'config-index' },
      { id: 'model', label: '模型', icon: Cpu, routeName: 'config-model' },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const keyword = ref('')

// 点击导航项切到对应子路由
function openSection(routeName: string): void {
  void router.push({ name: routeName })
}
</script>

<style scoped>
.config-layout {
  display: flex;
  height: 100vh;
  background: #f7f8fa;
}
.config-nav {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: 252px;
  padding: 12px 12px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  scrollbar-color: #dfe2e6 transparent;
  scrollbar-width: thin;
}
.config-nav::-webkit-scrollbar {
  width: 6px;
}
.config-nav::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #dfe2e6;
}
.nav-search {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid #e3e6ea;
  border-radius: 8px;
  background: #fff;
}
.nav-search-icon {
  flex: 0 0 auto;
  color: #9aa0a6;
}
.nav-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  color: #24292f;
  font-size: 13px;
}
.nav-search-input:focus {
  outline: none;
}
.nav-search-input::placeholder {
  color: #a3a8af;
}
.nav-groups {
  padding-bottom: 12px;
}
.group-label {
  padding: 14px 8px 6px;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 500;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 32px;
  padding: 0 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #3f454c;
  text-align: left;
  cursor: pointer;
}
.nav-item-label {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 13px;
}
.nav-item-icon {
  flex: 0 0 auto;
  color: #6b7280;
}
.nav-item.is-active {
  background: #eceef1;
  color: #1f2328;
}
.nav-item.is-active .nav-item-label {
  font-weight: 500;
}
.nav-item.is-active .nav-item-icon {
  color: #3f454c;
}
@media (hover: hover) {
  .nav-item:hover {
    background: #eceef1;
  }
}
.config-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-left: 1px solid #e8eaed;
  background: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .config-nav,
  .config-main {
    scroll-behavior: auto;
  }
}
@media (any-pointer: coarse) {
  .nav-item {
    height: 38px;
  }
}
</style>
