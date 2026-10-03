<!--会话搜索弹层-->
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
        aria-label="搜索会话"
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
            placeholder="搜索任务标题、内容或会话 ID..."
            aria-label="搜索关键词"
          />
        </div>
        <div class="search-toolbar">
          <span class="search-scope">所有任务</span>
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
            <span class="result-time">{{ row.time }}</span>
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
  time: string
}

// 静态示例行，接后端后替换
const rows: SearchRow[] = [
  {
    id: '1',
    title: '你好',
    meta: 'harness · Local · C:\\workspace\\project\\harness',
    time: '09:45',
  },
  {
    id: '2',
    title: '项目解析',
    meta: 'harness · Local · C:\\workspace\\project\\harness',
    time: '9月29日',
  },
  {
    id: '3',
    title: '项目整体解析',
    meta: 'harness · Local · C:\\workspace\\project\\harness',
    time: '9月29日',
  },
  {
    id: '4',
    title: '解析整个项目',
    meta: 'harness · Local · C:\\workspace\\project\\harness',
    time: '9月28日',
  },
  {
    id: '5',
    title: '项目解析',
    meta: 'harness · Local · C:\\workspace\\project\\harness',
    time: '9月24日',
  },
  {
    id: '6',
    title: '瘦长的浅棕与米白短毛沙漠小型哺乳动物，深色眼睛与短耳',
    meta: '无 Workspace · Local · C:\\Users\\laizh\\Documents',
    time: '9月24日',
  },
  {
    id: '7',
    title: '你好',
    meta: '无 Workspace · Local · C:\\Users\\laizh\\Documents',
    time: '9月24日',
  },
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

// 键盘选择循环移动，并保持选中项可见
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
  /* 预留空白不越过面板可用高度，避免矮视口下被 max-height 裁切 */
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
.result-time {
  min-width: 0;
  overflow: hidden;
  color: #9ca3af;
  font-size: 12.5px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.result-time {
  justify-self: end;
}
/* 弹窗淡入，面板自上方落位 */
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
