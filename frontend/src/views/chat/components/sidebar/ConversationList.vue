<template>
  <div class="conversation-list">
    <!-- 按时间分组的历史 -->
    <section v-for="group in groups" :key="group.label" class="history-group">
      <h4 class="group-label">{{ group.label }}</h4>
      <button v-for="item in group.items" :key="item.id" class="history-item" type="button">
        <MessageSquare :size="14" />
        <span class="item-title">{{ item.title }}</span>
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { MessageSquare } from 'lucide-vue-next'

/** 历史会话项 */
interface HistoryItem {
  id: string
  title: string
}

/** 时间分组 */
interface HistoryGroup {
  label: string
  items: HistoryItem[]
}

// 假数据，后续接 api/chat
const groups: HistoryGroup[] = [
  {
    label: '今天',
    items: [
      { id: '1', title: '帮我梳理 agent 框架的中间件设计' },
      { id: '2', title: 'ruamel.yaml 和 pyyaml 的区别' },
      { id: '3', title: '左侧导航栏三段式布局' },
    ],
  },
  {
    label: '最近 7 天',
    items: [
      { id: '4', title: '模型配置 CRUD 接口实现' },
      { id: '5', title: '前端路由模块化拆分方案' },
      { id: '6', title: '桌面端打包选 Electron 还是 Tauri' },
      { id: '7', title: 'vite 代理与 api_prefix 的冲突' },
      { id: '8', title: 'SSE 流式输出的通道设计' },
    ],
  },
  {
    label: '更早',
    items: [
      { id: '9', title: 'config.yaml 热加载机制' },
      { id: '10', title: 'FastAPI 统一响应结构 Result' },
      { id: '11', title: 'structlog 日志方案调研' },
      { id: '12', title: '多用户隔离的可行性讨论' },
    ],
  },
]
</script>

<style scoped>
.history-group {
  padding: 4px 0;
}
.group-label {
  padding: 6px 20px;
  font-size: 12px;
  font-weight: 500;
  color: #909399;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
}
.history-item:active {
  background: #eceff3;
}
@media (hover: hover) {
  .history-item:hover {
    background: #eceff3;
  }
}
@media (any-pointer: coarse) {
  .history-item {
    min-height: 42px;
  }
}
.item-title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
