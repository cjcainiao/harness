<!--斜杠命令菜单-->
<template>
  <div id="slash-command-menu" class="slash-command-menu" role="listbox" aria-label="可用命令">
    <div class="command-list">
      <button
        v-for="(command, index) in filteredCommands"
        :key="command.name"
        :ref="(element) => setRowRef(element, index)"
        class="command-row"
        :class="{ 'is-active': index === activeIndex }"
        type="button"
        role="option"
        :aria-selected="index === activeIndex"
        @mouseenter="activeIndex = index"
        @mousedown.prevent
        @click="select(command.name)"
      >
        <component :is="command.icon" class="command-icon" :size="14" :stroke-width="1.7" />
        <span class="command-name">{{ command.label }}</span>
        <span class="command-description">{{ command.description }}</span>
      </button>
      <div v-if="!filteredCommands.length" class="command-empty">没有匹配的命令</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Archive,
  CircleDashed,
  CircleGauge,
  FilePlus2,
  Folder,
  GitBranch,
  MessageCirclePlus,
  MessageSquare,
  Paperclip,
  Upload,
  Zap,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'

const props = defineProps<{ query: string }>()
const emit = defineEmits<{ select: [name: string] }>()

const commands = [
  { name: 'mcp', label: 'MCP', description: '显示 MCP 服务器状态', icon: Paperclip },
  { name: 'usage', label: '使用情况和计费', description: '打开用量和账单设置', icon: CircleGauge },
  { name: 'side', label: '侧边', description: '发起临时侧边聊天', icon: MessageCirclePlus },
  { name: 'share', label: '分享聊天', description: '创建此聊天快照的链接', icon: Upload },
  {
    name: 'fork',
    label: '创建聊天分支',
    description: '在当前工作空间或新工作树中创建此聊天的分支',
    icon: GitBranch,
  },
  {
    name: 'init',
    label: '初始化',
    description: '创建包含 Codex 说明的 AGENTS.md 文件',
    icon: FilePlus2,
  },
  { name: 'compact', label: '压缩', description: '压缩此聊天的上下文', icon: CircleDashed },
  { name: 'feedback', label: '反馈', description: '发送有关此聊天的反馈', icon: MessageSquare },
  { name: 'project', label: '在项目中工作', description: '在项目中开始聊天', icon: Folder },
  { name: 'archive', label: '归档', description: '归档当前聊天', icon: Archive },
  { name: 'fast', label: '快速', description: '关闭快速并返回标准速度', icon: Zap },
] as const

const activeIndex = ref(0)
const rowRefs = ref<Array<HTMLElement | null>>([])
const filteredCommands = computed(() => {
  const query = props.query.trim().toLocaleLowerCase()
  if (!query) return commands
  return commands.filter((command) =>
    `${command.name} ${command.label} ${command.description}`.toLocaleLowerCase().includes(query),
  )
})

watch(
  () => props.query,
  () => {
    activeIndex.value = 0
    rowRefs.value = []
  },
)

function setRowRef(element: Element | ComponentPublicInstance | null, index: number): void {
  rowRefs.value[index] = element instanceof HTMLElement ? element : null
}

// 键盘选择循环移动，并保持选中项可见
function moveSelection(direction: number): void {
  const count = filteredCommands.value.length
  if (!count) return
  activeIndex.value = (activeIndex.value + direction + count) % count
  void nextTick(() => rowRefs.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' }))
}

function select(name: string): void {
  emit('select', name)
}

function selectActive(): void {
  const command = filteredCommands.value[activeIndex.value]
  if (command) select(command.name)
}

defineExpose({ moveSelection, selectActive })
</script>

<style scoped>
.slash-command-menu {
  position: absolute;
  z-index: 20;
  right: 16px;
  bottom: calc(100% + 8px);
  left: 16px;
  max-height: min(320px, calc(100dvh - 160px));
  padding: 5px;
  overflow: hidden;
  border: 1px solid #e9e9e8;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 28px #0000000b;
}
.command-list {
  max-height: min(308px, calc(100dvh - 172px));
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: #e2e2e2 transparent;
  scrollbar-width: thin;
}
.command-list::-webkit-scrollbar {
  width: 6px;
}
.command-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #e2e2e2;
}
.command-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 28px;
  padding: 0 9px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #383b3e;
  cursor: pointer;
  font-size: 12px;
  text-align: left;
  white-space: nowrap;
}
.command-row.is-active {
  background: #f2f2f2;
}
.command-row:focus-visible {
  outline: 2px solid #a8b5c8;
  outline-offset: -2px;
}
.command-icon {
  flex: 0 0 auto;
  color: #555b60;
}
.command-name {
  flex: 0 0 auto;
  font-weight: 500;
}
.command-description {
  min-width: 0;
  overflow: hidden;
  color: #a6a8aa;
  text-overflow: ellipsis;
}
.command-empty {
  padding: 12px;
  color: #999;
  font-size: 12px;
  text-align: center;
}
@media (hover: hover) {
  .command-row:hover {
    background: #f2f2f2;
  }
}
@media (any-pointer: coarse) {
  .command-row {
    height: 36px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
}
/* 与输入卡片左右留白对齐 */
@media (max-width: 640px) {
  .slash-command-menu {
    left: 10px;
    right: 10px;
  }
}
</style>
