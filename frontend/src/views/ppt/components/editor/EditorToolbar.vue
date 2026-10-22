<!--PPT 画布基础编辑工具栏-->
<template>
  <div class="editor-toolbar" role="toolbar" aria-label="幻灯片编辑工具">
    <div class="tool-group">
      <button type="button" aria-label="新建幻灯片" title="新建幻灯片" @click="emit('addSlide')">
        <Plus :size="16" /> <span>新建页</span>
      </button>
      <button type="button" aria-label="添加文字" title="添加文字" @click="emit('addText')">
        <Type :size="16" /> <span>添加文字</span>
      </button>
    </div>
    <span class="divider" />
    <div class="tool-group">
      <button
        type="button"
        aria-label="编辑选中文字"
        title="编辑选中文字"
        :disabled="!hasSelection"
        @click="emit('editText')"
      >
        <Pencil :size="15" /> <span>编辑</span>
      </button>
      <button
        type="button"
        aria-label="删除选中文字"
        title="删除选中文字"
        :disabled="!hasSelection"
        @click="emit('deleteText')"
      >
        <Trash2 :size="15" /> <span>删除</span>
      </button>
    </div>
    <span class="divider" />
    <div class="tool-group">
      <button
        type="button"
        aria-label="撤销"
        title="撤销"
        :disabled="!canUndo"
        @click="emit('undo')"
      >
        <Undo2 :size="16" />
      </button>
      <button
        type="button"
        aria-label="重做"
        title="重做"
        :disabled="!canRedo"
        @click="emit('redo')"
      >
        <Redo2 :size="16" />
      </button>
    </div>
    <span class="page-count">{{ pageNumber }} / {{ totalPages }}</span>
  </div>
</template>

<script setup lang="ts">
import { Pencil, Plus, Redo2, Trash2, Type, Undo2 } from 'lucide-vue-next'

defineProps<{
  hasSelection: boolean
  canUndo: boolean
  canRedo: boolean
  pageNumber: number
  totalPages: number
}>()
const emit = defineEmits<{
  addSlide: []
  addText: []
  editText: []
  deleteText: []
  undo: []
  redo: []
}>()
</script>

<style scoped>
.editor-toolbar {
  display: flex;
  min-width: 0;
  height: 46px;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border-bottom: 1px solid #dedede;
  background: #fafafa;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

button {
  display: inline-flex;
  height: 32px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #3c3c3c;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

button:disabled {
  color: #b7b7b7;
  cursor: default;
}

.divider {
  width: 1px;
  height: 20px;
  background: #dedede;
}

.page-count {
  margin-left: auto;
  color: #858585;
  font-size: 12px;
  white-space: nowrap;
}

@media (hover: hover) {
  button:not(:disabled):hover {
    background: #ededed;
  }
}

@media (max-width: 700px) {
  .editor-toolbar {
    gap: 4px;
    overflow-x: auto;
    padding-right: 8px;
    padding-left: 8px;
    scrollbar-width: none;
  }

  .editor-toolbar::-webkit-scrollbar {
    display: none;
  }

  .tool-group,
  .divider,
  .page-count {
    flex-shrink: 0;
  }

  button {
    width: 32px;
    padding: 0;
  }

  button span {
    display: none;
  }

  .page-count {
    font-size: 11px;
  }
}

@media (any-pointer: coarse) {
  button {
    min-width: 40px;
    min-height: 40px;
  }
}
</style>
