<!--斜杠命令菜单-->
<template>
  <div id="slash-command-menu" class="slash-command-menu" role="listbox" aria-label="可用命令">
    <div class="command-list">
      <button
        v-for="(command, index) in commands"
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
        <component
          :is="commandIcons[command.icon_key] ?? Command"
          class="command-icon"
          :size="14"
          :stroke-width="1.7"
        />
        <span class="command-name">{{ command.label }}</span>
        <span class="command-description">{{ command.description }}</span>
      </button>
      <div v-if="loading" class="command-empty">加载中…</div>
      <div v-else-if="loadError" class="command-empty">{{ loadError }}</div>
      <div v-else-if="!commands.length" class="command-empty">
        <Inbox class="command-empty-icon" :size="24" :stroke-width="1.5" aria-hidden="true" />
        <span>{{ query ? '没有匹配的命令' : '暂无命令' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Archive,
  CircleDashed,
  CircleGauge,
  Command,
  FilePlus2,
  Folder,
  GitBranch,
  Inbox,
  MessageCirclePlus,
  MessageSquare,
  Paperclip,
  Upload,
  Zap,
} from 'lucide-vue-next'
import { nextTick, ref, watch } from 'vue'
import type { Component, ComponentPublicInstance } from 'vue'
import { fetchSlashMenu, type SlashCommandItem } from '@/api/slash'

const props = defineProps<{ command: string | null; query: string }>()
const emit = defineEmits<{ select: [name: string] }>()
const QUERY_DEBOUNCE_MS = 300

const commandIcons: Record<string, Component> = {
  archive: Archive,
  'circle-dashed': CircleDashed,
  'circle-gauge': CircleGauge,
  command: Command,
  'file-plus-2': FilePlus2,
  folder: Folder,
  'git-branch': GitBranch,
  'message-circle-plus': MessageCirclePlus,
  'message-square': MessageSquare,
  paperclip: Paperclip,
  upload: Upload,
  zap: Zap,
}

const commands = ref<SlashCommandItem[]>([])
const loading = ref(false)
const loadError = ref('')
const activeIndex = ref(0)
const rowRefs = ref<Array<HTMLElement | null>>([])

watch(
  () => [props.command, props.query] as const,
  ([command, query], _previous, onCleanup) => {
    activeIndex.value = 0
    rowRefs.value = []
    commands.value = []
    loadError.value = ''
    loading.value = true

    const controller = new AbortController()
    const timer = window.setTimeout(
      () => {
        void fetchSlashMenu(command, query, controller.signal)
          .then((items) => {
            if (!controller.signal.aborted) commands.value = items
          })
          .catch((error: unknown) => {
            if (!controller.signal.aborted) {
              loadError.value = error instanceof Error ? error.message : '获取斜杠命令失败'
            }
          })
          .finally(() => {
            if (!controller.signal.aborted) loading.value = false
          })
      },
      query ? QUERY_DEBOUNCE_MS : 0,
    )

    onCleanup(() => {
      window.clearTimeout(timer)
      controller.abort()
    })
  },
  { immediate: true },
)

function setRowRef(element: Element | ComponentPublicInstance | null, index: number): void {
  rowRefs.value[index] = element instanceof HTMLElement ? element : null
}

// 键盘选择循环移动，并保持选中项可见
function moveSelection(direction: number): void {
  const count = commands.value.length
  if (!count) return
  activeIndex.value = (activeIndex.value + direction + count) % count
  void nextTick(() => rowRefs.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' }))
}

function select(name: string): void {
  emit('select', name)
}

function selectActive(): void {
  const command = commands.value[activeIndex.value]
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
  height: min(200px, calc(100dvh - 160px));
  padding: 5px;
  overflow: hidden;
  border: 1px solid #e9e9e8;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 28px #0000000b;
}
.command-list {
  height: 100%;
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 100%;
  padding: 12px;
  color: #999;
  font-size: 12px;
  text-align: center;
}
.command-empty-icon {
  color: #b7bec8;
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
