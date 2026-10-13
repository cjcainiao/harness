<!--设置导航-->
<template>
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
      <section v-for="group in filteredGroups" :key="group.label" class="nav-group">
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
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpenCheck, BrainCircuit, PlugZap, Search, User } from 'lucide-vue-next'

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

// 导航分组
const navGroups: NavGroup[] = [
  {
    label: '个人',
    items: [
      { id: 'profile', label: '个人资料', icon: User, routeName: 'config-index' },
      { id: 'model', label: '模型', icon: BrainCircuit, routeName: 'config-model' },
      { id: 'mcp', label: 'MCP 服务', icon: PlugZap, routeName: 'config-mcp' },
      { id: 'skills', label: 'Skill 技能包', icon: BookOpenCheck, routeName: 'config-skills' },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const keyword = ref('')
const filteredGroups = computed(() =>
  navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        item.label.toLowerCase().includes(keyword.value.trim().toLowerCase()),
      ),
    }))
    .filter((group) => group.items.length > 0),
)

// 设置页导航
function openSection(routeName: string): void {
  void router.push({ name: routeName })
}
</script>

<style scoped>
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
  background: #f8f8f8;
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
  border: 1px solid #dedede;
  border-radius: 5px;
  background: #fff;
}
.nav-search-icon {
  flex: 0 0 auto;
  color: #888;
}
.nav-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  color: #222;
  font-size: 13px;
}
.nav-search-input:focus {
  outline: none;
}
.nav-search-input::placeholder {
  color: #999;
}
.nav-groups {
  padding-bottom: 12px;
}
.group-label {
  padding: 14px 8px 6px;
  color: #888;
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
  border-radius: 5px;
  background: transparent;
  color: #444;
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
  color: #666;
}
.nav-item.is-active {
  background: #eaeaea;
  color: #171717;
}
.nav-item.is-active .nav-item-label {
  font-weight: 500;
}
.nav-item.is-active .nav-item-icon {
  color: #333;
}
@media (hover: hover) {
  .nav-item:hover {
    background: #eaeaea;
  }
}
@media (prefers-reduced-motion: reduce) {
  .config-nav {
    scroll-behavior: auto;
  }
}
@media (any-pointer: coarse) {
  .nav-item {
    height: 38px;
  }
}
@media (max-width: 720px) {
  .config-nav {
    width: 100%;
    padding: 8px 12px;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .nav-search,
  .group-label {
    display: none;
  }
  .nav-groups,
  .nav-group {
    display: flex;
    gap: 6px;
  }
  .nav-item {
    flex: 0 0 auto;
    width: auto;
    padding: 0 12px;
  }
}
</style>
