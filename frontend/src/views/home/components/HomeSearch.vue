<!--首页搜索弹层-->
<template>
  <Teleport to="body">
    <!-- 遮罩 -->
    <Transition name="search-fade">
      <button
        v-if="visible"
        class="search-mask"
        type="button"
        aria-label="关闭搜索"
        @click="close"
      />
    </Transition>
    <!-- 搜索弹窗 -->
    <Transition name="search-pop">
      <section
        v-if="visible"
        class="search-palette"
        role="dialog"
        aria-modal="true"
        aria-label="搜索"
        @keydown.esc="close"
        @keydown.up.prevent="moveSelection(-1)"
        @keydown.down.prevent="moveSelection(1)"
      >
        <div class="search-field">
          <Search class="search-field-icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
          <input
            ref="keywordInputRef"
            v-model="keyword"
            class="search-input"
            type="text"
            placeholder="搜索功能、设置或文档..."
            aria-label="搜索关键词"
          />
        </div>
        <div class="search-toolbar">
          <span class="search-scope">全部条目</span>
          <span class="search-hints">
            <kbd class="key-cap">↑</kbd>
            <kbd class="key-cap">↓</kbd>
            <span class="hint-label">选择</span>
            <kbd class="key-cap">Enter</kbd>
            <span class="hint-label">打开</span>
            <span class="hint-count">{{ rows.length }} 个</span>
          </span>
        </div>
        <div class="search-results" role="listbox" aria-label="搜索结果">
          <button
            v-for="(row, index) in rows"
            :key="row.id"
            :ref="(element) => setRowRef(element, index)"
            class="result-row"
            :class="{ 'is-active': index === activeIndex }"
            type="button"
            role="option"
            :aria-selected="index === activeIndex"
            @mouseenter="activeIndex = index"
            @mousedown.prevent
          >
            <span class="result-title">{{ row.title }}</span>
            <span class="result-meta">{{ row.meta }}</span>
            <span class="result-kind">{{ row.kind }}</span>
          </button>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { nextTick, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean] }>()

interface SearchRow {
  id: string
  title: string
  meta: string
  kind: string
}

// 静态条目
const rows: SearchRow[] = [
  { id: '1', title: '开始对话', meta: '进入会话页新建一轮提问', kind: '页面' },
  { id: '2', title: '会话历史', meta: '查看并续写历史会话', kind: '页面' },
  { id: '3', title: '模型', meta: '选择模型与推理强度', kind: '设置' },
  { id: '4', title: '个人资料', meta: '查看账号与偏好信息', kind: '设置' },
  { id: '5', title: '文档', meta: '使用说明与接口说明', kind: '资源' },
  { id: '6', title: 'GitHub 仓库', meta: '源码、issue 与发布记录', kind: '资源' },
  { id: '7', title: '深色主题', meta: '切换界面配色', kind: '偏好' },
]

const keyword = ref('')
const activeIndex = ref(0)
const rowRefs = ref<Array<HTMLElement | null>>([])
const keywordInputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    activeIndex.value = 0
    rowRefs.value = []
    void nextTick(() => keywordInputRef.value?.focus())
  },
)

function setRowRef(element: Element | ComponentPublicInstance | null, index: number): void {
  rowRefs.value[index] = element instanceof HTMLElement ? element : null
}

// 键盘选择循环移动
function moveSelection(direction: number): void {
  const count = rows.length
  if (!count) return
  activeIndex.value = (activeIndex.value + direction + count) % count
  void nextTick(() => rowRefs.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' }))
}

function close(): void {
  emit('update:visible', false)
}
</script>

<style scoped>
.search-mask {
  position: fixed;
  z-index: 40;
  inset: 0;
  padding: 0;
  border: 0;
  background: rgba(18, 22, 28, 0.3);
  backdrop-filter: blur(2px);
  cursor: pointer;
}
.search-palette {
  position: fixed;
  z-index: 41;
  top: 18vh;
  left: 50%;
  display: flex;
  flex-direction: column;
  width: min(690px, calc(100vw - 48px));
  max-height: min(64vh, 620px);
  overflow: hidden;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(20, 24, 29, 0.18);
  transform: translateX(-50%);
}
.search-field {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 12px;
  height: 54px;
  padding: 0 22px;
  border-bottom: 1px solid #eceef0;
}
.search-field-icon {
  flex: 0 0 auto;
  color: #8b9098;
}
.search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  color: #24292f;
  font-size: 14.5px;
  line-height: 22px;
}
.search-input:focus {
  outline: none;
}
.search-input::placeholder {
  color: #a3a8af;
}
.search-toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 40px;
  padding: 0 22px;
}
.search-scope {
  color: #6b7280;
  font-size: 13px;
}
.search-hints {
  display: flex;
  align-items: center;
  gap: 5px;
}
.key-cap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 21px;
  padding: 0 5px;
  border: 1px solid #d9dce0;
  border-radius: 5px;
  background: #fff;
  color: #6b7280;
  font-family: inherit;
  font-size: 11.5px;
  line-height: 1;
}
.hint-label,
.hint-count {
  color: #9ca3af;
  font-size: 12px;
}
.hint-label {
  margin-right: 8px;
}
.search-results {
  flex: 1;
  /* 预留空白不越过面板可用高度 */
  min-height: min(300px, calc(64vh - 104px));
  padding: 0 10px 10px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: #e2e2e2 transparent;
  scrollbar-width: thin;
}
.search-results::-webkit-scrollbar {
  width: 6px;
}
.search-results::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #e2e2e2;
}
.result-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  width: 100%;
  height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.result-row.is-active {
  background: #f0f1f3;
}
@media (hover: hover) {
  .result-row:hover {
    background: #f0f1f3;
  }
}
.result-title {
  min-width: 0;
  overflow: hidden;
  color: #24292f;
  font-size: 13.5px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.result-meta,
.result-kind {
  min-width: 0;
  overflow: hidden;
  color: #9ca3af;
  font-size: 12.5px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.result-kind {
  justify-self: end;
}
/* 弹窗动效 */
.search-fade-enter-active,
.search-fade-leave-active {
  transition: opacity 0.16s ease;
}
.search-fade-enter-from,
.search-fade-leave-to {
  opacity: 0;
}
.search-pop-enter-active,
.search-pop-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}
.search-pop-enter-from,
.search-pop-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-6px);
}
@media (prefers-reduced-motion: reduce) {
  .search-fade-enter-active,
  .search-fade-leave-active,
  .search-pop-enter-active,
  .search-pop-leave-active {
    transition: none;
  }
}
@media (any-pointer: coarse) {
  .result-row {
    height: 42px;
  }
}
</style>
