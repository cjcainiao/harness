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
        @keydown.enter.prevent="openActive"
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
            <span class="hint-count">{{ loading ? '检索中' : `${rows.length} 个` }}</span>
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
            @click="open(row)"
          >
            <span class="result-title">{{ row.title }}</span>
            <span class="result-meta">{{ row.meta }}</span>
            <span class="result-time">{{ row.time }}</span>
          </button>
          <p v-if="stateText" class="result-state">{{ stateText }}</p>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { searchThreads } from '@/api/history'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  'update:visible': [visible: boolean]
  select: [threadId: string]
}>()

interface SearchRow {
  id: string
  title: string
  meta: string
  time: string
}

// 输入停顿多久才发检索请求
const SEARCH_DEBOUNCE_MS = 180

const keyword = ref('')
const hits = ref<Array<{ threadId: string; title: string; workspace: string; updatedAt: string }>>(
  [],
)
const loading = ref(false)
const failed = ref(false)
const activeIndex = ref(0)
const rowRefs = ref<Array<HTMLElement | null>>([])
const keywordInputRef = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
// 后到的响应不能覆盖新关键词的结果
let requestSeq = 0

const rows = computed<SearchRow[]>(() =>
  hits.value.map((hit) => ({
    id: hit.threadId,
    title: hit.title,
    meta: hit.workspace ? `Local · ${hit.workspace}` : '无 Workspace',
    time: formatHitTime(hit.updatedAt),
  })),
)

// 结果为空时的说明文案，有结果时不显示
const stateText = computed(() => {
  if (failed.value) return '检索失败，请重试'
  if (!keyword.value.trim()) return '输入关键词检索任务标题、内容或会话 ID'
  if (loading.value) return '检索中…'
  if (!hits.value.length) return '没有匹配的任务'
  return ''
})

function formatHitTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  if (sameDay) return `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function pad(value: number): string {
  return value < 10 ? `0${value}` : `${value}`
}

function cancelTimer(): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = null
}

function resetResults(): void {
  cancelTimer()
  requestSeq += 1
  hits.value = []
  loading.value = false
  failed.value = false
  activeIndex.value = 0
  rowRefs.value = []
}

// 关键词变化后延迟触发检索，空关键词直接清空结果
function scheduleSearch(): void {
  cancelTimer()
  const value = keyword.value.trim()
  if (!value) {
    hits.value = []
    loading.value = false
    failed.value = false
    activeIndex.value = 0
    return
  }
  loading.value = true
  failed.value = false
  debounceTimer = setTimeout(() => void runSearch(value), SEARCH_DEBOUNCE_MS)
}

async function runSearch(value: string): Promise<void> {
  const current = ++requestSeq
  try {
    const items = await searchThreads(value)
    if (current !== requestSeq) return
    hits.value = items.map((item) => ({
      threadId: item.thread_id,
      title: item.title,
      workspace: item.workspace ?? '',
      updatedAt: item.updated_at,
    }))
    activeIndex.value = 0
    failed.value = false
  } catch {
    if (current !== requestSeq) return
    hits.value = []
    failed.value = true
  } finally {
    if (current === requestSeq) loading.value = false
  }
}

watch(keyword, scheduleSearch)

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      cancelTimer()
      return
    }
    keyword.value = ''
    resetResults()
    void nextTick(() => keywordInputRef.value?.focus())
  },
)

onUnmounted(cancelTimer)

function setRowRef(element: Element | ComponentPublicInstance | null, index: number): void {
  rowRefs.value[index] = element instanceof HTMLElement ? element : null
}

// 键盘选择循环移动，并保持选中项可见
function moveSelection(direction: number): void {
  const count = rows.value.length
  if (!count) return
  activeIndex.value = (activeIndex.value + direction + count) % count
  void nextTick(() => rowRefs.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' }))
}

function open(row: SearchRow): void {
  emit('select', row.id)
  close()
}

// 回车打开当前选中项
function openActive(): void {
  const row = rows.value[activeIndex.value]
  if (row) open(row)
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
.result-state {
  padding: 22px 14px;
  color: #9ca3af;
  font-size: 12.5px;
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
