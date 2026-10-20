<!--知识库与文档管理组件-->
<template>
  <div class="knowledge-shell">
    <div class="knowledge-page">
      <router-link class="back-link" to="/chat">
        <ArrowLeft :size="15" :stroke-width="1.8" /> 返回聊天
      </router-link>

      <header class="page-header">
        <div class="page-heading">
          <span class="heading-icon"><BookOpenCheck :size="21" :stroke-width="1.7" /></span>
          <div>
            <h1>知识库</h1>
            <p>管理对话中可以检索和引用的资料。</p>
          </div>
        </div>
        <button class="primary-button" type="button" @click="openCreateForm">
          <Plus :size="16" :stroke-width="2" /> 新建知识库
        </button>
      </header>

      <div class="workspace">
        <aside class="base-panel" aria-label="知识库列表">
          <div class="base-panel-header">
            <h2>我的知识库</h2>
            <span>{{ bases.length }}</span>
          </div>
          <form v-if="showCreateForm" class="create-form" @submit.prevent="createBase">
            <label for="knowledge-name">知识库名称</label>
            <input
              id="knowledge-name"
              ref="createInput"
              v-model="newName"
              type="text"
              maxlength="100"
              placeholder="输入名称"
            />
            <div class="create-actions">
              <button type="submit" :disabled="creating || !newName.trim()">创建</button>
              <button type="button" @click="cancelCreate">取消</button>
            </div>
          </form>
          <p v-if="basesLoading" class="sidebar-hint">正在加载…</p>
          <p v-else-if="!bases.length" class="sidebar-hint">还没有知识库</p>
          <nav v-else class="base-list" aria-label="选择知识库">
            <div
              v-for="base in bases"
              :key="base.id"
              class="base-swipe-item"
              :data-base-id="base.id"
            >
              <div class="base-actions" :aria-hidden="revealedBaseId !== base.id">
                <button
                  class="base-swipe-delete"
                  type="button"
                  :tabindex="revealedBaseId === base.id ? 0 : -1"
                  @click.stop="openDeleteDialog(base)"
                >
                  <Trash2 :size="16" aria-hidden="true" />
                  <span>删除</span>
                </button>
              </div>
              <button
                type="button"
                class="base-item"
                :class="{
                  selected: selectedId === base.id,
                  'is-dragging': swipingBaseId === base.id,
                }"
                :style="{ transform: `translateX(${rowOffset(base.id)}px)` }"
                :aria-current="selectedId === base.id ? 'true' : undefined"
                @click="selectBase(base.id)"
                @contextmenu.prevent="openContextMenu($event, base)"
                @pointerdown="onRowPointerDown($event, base.id)"
                @pointermove="onRowPointerMove($event, base.id)"
                @pointerup="onRowPointerUp($event, base.id)"
                @pointercancel="onRowPointerCancel($event, base.id)"
              >
                <FolderClosed :size="17" :stroke-width="1.8" />
                <span class="base-name">{{ base.name }}</span>
                <small>{{ base.document_count }}</small>
              </button>
            </div>
          </nav>
        </aside>

        <section class="document-panel" aria-label="知识库文档">
          <template v-if="selectedBase">
            <header class="document-header">
              <div class="document-heading">
                <span class="eyebrow">当前知识库</span>
                <h2>{{ selectedBase.name }}</h2>
                <p>上传资料后，对话会从这里查找相关内容。</p>
              </div>
              <div class="upload-actions">
                <input
                  ref="fileInput"
                  class="visually-hidden"
                  type="file"
                  tabindex="-1"
                  accept=".md,.markdown,.txt,.html,.htm,.pdf,.docx"
                  multiple
                  aria-hidden="true"
                  @change="uploadFiles"
                />
                <button
                  class="upload-button"
                  type="button"
                  :disabled="uploading"
                  @click="openFilePicker"
                >
                  <Upload :size="15" :stroke-width="1.9" /> {{ uploading ? '上传中…' : '上传文档' }}
                </button>
                <span>支持 Markdown、TXT、HTML、PDF、DOCX · 单个不超过 20 MB</span>
              </div>
            </header>

            <div class="section-heading">
              <h3>
                已上传文档 <span>{{ documents.length }}</span>
              </h3>
            </div>
            <div v-if="documentsLoading" class="document-state">正在读取文档…</div>
            <div v-else-if="!documents.length" class="document-state empty-state">
              <FileText :size="28" :stroke-width="1.5" />
              <strong>还没有文档</strong>
              <p>上传资料后会自动解析并建立索引。</p>
            </div>
            <div v-else class="document-list">
              <article v-for="item in documents" :key="item.id" class="document-item">
                <span class="file-icon"><FileText :size="18" :stroke-width="1.7" /></span>
                <div class="document-main">
                  <strong>{{ item.name }}</strong>
                  <span>{{ formatSize(item.size) }} · {{ item.chunk_count }} 个片段</span>
                  <p v-if="item.error" class="error-text">{{ item.error }}</p>
                </div>
                <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
                <div class="document-actions">
                  <button v-if="item.status === 'ready'" type="button" @click="previewChunks(item)">
                    <Eye :size="14" :stroke-width="1.8" /> 片段
                  </button>
                  <a
                    v-if="item.status === 'ready'"
                    :href="knowledgeDocumentUrl(item.id)"
                    target="_blank"
                    rel="noopener"
                  >
                    <ExternalLink :size="14" :stroke-width="1.8" /> 原文
                  </a>
                  <button v-if="item.status === 'failed'" type="button" @click="retry(item)">
                    <RotateCcw :size="14" :stroke-width="1.8" /> 重试
                  </button>
                  <button
                    class="delete-document"
                    type="button"
                    @click="openDocumentDeleteDialog(item)"
                  >
                    <Trash2 :size="14" :stroke-width="1.8" /> 删除
                  </button>
                </div>
              </article>
            </div>

            <section v-if="previewDocument" class="preview-panel" aria-label="文档片段预览">
              <div class="preview-head">
                <div>
                  <span class="eyebrow">片段预览</span>
                  <h3>{{ previewDocument.name }}</h3>
                </div>
                <button type="button" aria-label="关闭片段预览" @click="previewDocument = null">
                  <X :size="17" :stroke-width="1.8" />
                </button>
              </div>
              <p v-if="chunksLoading" class="preview-loading">正在读取片段…</p>
              <article v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
                <strong>{{ chunk.seq + 1 }}. {{ chunk.heading }}</strong>
                <p>{{ chunk.content }}</p>
              </article>
            </section>
          </template>
          <div v-else class="empty-workspace">
            <span class="empty-icon"><BookOpenCheck :size="28" :stroke-width="1.5" /></span>
            <h2>选择一个知识库</h2>
            <p>创建知识库后，便可以上传文档并用于对话检索。</p>
          </div>
        </section>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="contextMenu"
        ref="contextMenuRef"
        class="base-context-menu"
        :class="{ 'is-above': contextMenu.placement === 'above' }"
        role="menu"
        :aria-label="`${contextMenu.name} 的操作菜单`"
        :style="{
          left: `${contextMenu.x}px`,
          top: `${contextMenu.y}px`,
          '--arrow-x': `${contextMenu.arrowX}px`,
        }"
        @contextmenu.prevent
      >
        <button
          class="base-context-delete"
          role="menuitem"
          type="button"
          @click="openDeleteDialog(contextMenu.base)"
        >
          <Trash2 :size="15" aria-hidden="true" />
          <span>删除知识库</span>
        </button>
      </div>
    </Teleport>
    <ElDialog
      v-model="deleteDialogVisible"
      append-to-body
      align-center
      class="knowledge-delete-dialog"
      modal-class="knowledge-delete-overlay"
      width="420px"
      :lock-scroll="false"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="!deletingBaseId"
      @closed="deleteTarget = null"
    >
      <template #header="{ titleId, titleClass }">
        <div class="delete-dialog-heading">
          <span class="delete-warning-icon" aria-hidden="true">!</span>
          <span :id="titleId" :class="titleClass">确定删除知识库？</span>
        </div>
      </template>
      <p class="delete-dialog-description">
        删除“{{ deleteTarget?.name }}”后，其中的全部文档将不可恢复。
      </p>
      <template #footer>
        <button
          class="delete-dialog-cancel"
          type="button"
          :disabled="Boolean(deletingBaseId)"
          @click="deleteDialogVisible = false"
        >
          取消
        </button>
        <button
          class="delete-dialog-confirm"
          type="button"
          :disabled="Boolean(deletingBaseId)"
          @click="confirmDelete"
        >
          {{ deletingBaseId ? '删除中…' : '删除' }}
        </button>
      </template>
    </ElDialog>
    <ElDialog
      v-model="documentDeleteDialogVisible"
      append-to-body
      align-center
      class="knowledge-delete-dialog"
      modal-class="knowledge-delete-overlay"
      width="420px"
      :lock-scroll="false"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="!deletingDocumentId"
      @closed="documentDeleteTarget = null"
    >
      <template #header="{ titleId, titleClass }">
        <div class="delete-dialog-heading">
          <span class="delete-warning-icon" aria-hidden="true">!</span>
          <span :id="titleId" :class="titleClass">确定删除文档？</span>
        </div>
      </template>
      <p class="delete-dialog-description">
        删除“{{ documentDeleteTarget?.name }}”后，该文档及其检索片段将不可恢复。
      </p>
      <template #footer>
        <button
          class="delete-dialog-cancel"
          type="button"
          :disabled="Boolean(deletingDocumentId)"
          @click="documentDeleteDialogVisible = false"
        >
          取消
        </button>
        <button
          class="delete-dialog-confirm"
          type="button"
          :disabled="Boolean(deletingDocumentId)"
          @click="confirmDocumentDelete"
        >
          {{ deletingDocumentId ? '删除中…' : '删除' }}
        </button>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { ElDialog, ElMessage } from 'element-plus'
import {
  ArrowLeft,
  BookOpenCheck,
  ExternalLink,
  Eye,
  FileText,
  FolderClosed,
  Plus,
  RotateCcw,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteKnowledgeDocument,
  knowledgeDocumentUrl,
  listKnowledgeBases,
  listKnowledgeChunks,
  listKnowledgeDocuments,
  retryKnowledgeDocument,
  uploadKnowledgeDocument,
  type KnowledgeBase,
  type KnowledgeChunk,
  type KnowledgeDocument,
} from '@/api/knowledge'
import { setPageTitle } from '@/utils/pageTitleUtil'

const bases = ref<KnowledgeBase[]>([])
const documents = ref<KnowledgeDocument[]>([])
const selectedId = ref('')
const selectedBase = computed(() => bases.value.find((base) => base.id === selectedId.value))
const newName = ref('')
const showCreateForm = ref(false)
const createInput = ref<HTMLInputElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const basesLoading = ref(false)
const documentsLoading = ref(false)
const chunksLoading = ref(false)
const creating = ref(false)
const uploading = ref(false)
const previewDocument = ref<KnowledgeDocument | null>(null)
const chunks = ref<KnowledgeChunk[]>([])
const contextMenuRef = ref<HTMLElement | null>(null)
const contextMenu = ref<ContextMenuState | null>(null)
const revealedBaseId = ref<string | null>(null)
const swipingBaseId = ref<string | null>(null)
const swipeOffset = ref(0)
const deleteDialogVisible = ref(false)
const deleteTarget = ref<KnowledgeBase | null>(null)
const deletingBaseId = ref<string | null>(null)
const documentDeleteDialogVisible = ref(false)
const documentDeleteTarget = ref<KnowledgeDocument | null>(null)
const deletingDocumentId = ref<string | null>(null)
let poller: number | undefined
let requestId = 0
let swipeGesture: SwipeGesture | null = null
let suppressedClickId: string | null = null
let suppressClickTimer: ReturnType<typeof setTimeout> | undefined

interface ContextMenuState {
  base: KnowledgeBase
  name: string
  x: number
  y: number
  arrowX: number
  placement: 'above' | 'below'
}

interface SwipeGesture {
  id: string
  pointerId: number
  startX: number
  startY: number
  startOffset: number
  horizontal: boolean
}

const SWIPE_ACTION_WIDTH = 64
const SWIPE_START_PX = 10

function reportError(error: unknown): void {
  ElMessage({
    message: error instanceof Error ? error.message : '操作失败',
    type: 'error',
    plain: true,
  })
}

function statusText(status: KnowledgeDocument['status']): string {
  return {
    pending: '等待处理',
    parsing: '解析中',
    indexing: '建立索引中',
    ready: '可用',
    failed: '失败',
  }[status]
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

async function openCreateForm(): Promise<void> {
  showCreateForm.value = true
  await nextTick()
  createInput.value?.focus()
}

function cancelCreate(): void {
  showCreateForm.value = false
  newName.value = ''
}

function openFilePicker(): void {
  fileInput.value?.click()
}

async function refreshBases(): Promise<void> {
  basesLoading.value = true
  try {
    bases.value = await listKnowledgeBases()
    if (!bases.value.some((base) => base.id === selectedId.value))
      selectedId.value = bases.value[0]?.id ?? ''
  } catch (error) {
    reportError(error)
  } finally {
    basesLoading.value = false
  }
}

async function refreshDocuments(showLoading = false): Promise<void> {
  const id = selectedId.value
  const currentRequest = ++requestId
  if (!id) {
    documents.value = []
    return
  }
  if (showLoading) documentsLoading.value = true
  try {
    const items = await listKnowledgeDocuments(id)
    if (currentRequest === requestId && id === selectedId.value) documents.value = items
  } catch (error) {
    if (showLoading) reportError(error)
  } finally {
    if (currentRequest === requestId) documentsLoading.value = false
  }
}

async function createBase(): Promise<void> {
  if (!newName.value.trim() || creating.value) return
  creating.value = true
  try {
    const base = await createKnowledgeBase(newName.value.trim())
    newName.value = ''
    showCreateForm.value = false
    await refreshBases()
    selectedId.value = base.id
  } catch (error) {
    reportError(error)
  } finally {
    creating.value = false
  }
}

function rowOffset(id: string): number {
  if (swipingBaseId.value === id) return swipeOffset.value
  return revealedBaseId.value === id ? -SWIPE_ACTION_WIDTH : 0
}

function closeSwipeActions(): void {
  revealedBaseId.value = null
}

function selectBase(id: string): void {
  if (suppressedClickId === id) {
    suppressedClickId = null
    return
  }
  if (revealedBaseId.value === id) {
    closeSwipeActions()
    return
  }
  closeSwipeActions()
  closeContextMenu()
  selectedId.value = id
}

function onRowPointerDown(event: PointerEvent, id: string): void {
  if (event.pointerType === 'mouse' || !event.isPrimary) return
  if (suppressedClickId === id) suppressedClickId = null
  swipeGesture = {
    id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startOffset: revealedBaseId.value === id ? -SWIPE_ACTION_WIDTH : 0,
    horizontal: false,
  }
}

function onRowPointerMove(event: PointerEvent, id: string): void {
  const gesture = swipeGesture
  if (!gesture || gesture.id !== id || gesture.pointerId !== event.pointerId) return
  const dx = event.clientX - gesture.startX
  const dy = event.clientY - gesture.startY
  if (!gesture.horizontal) {
    if (Math.abs(dy) > SWIPE_START_PX && Math.abs(dy) > Math.abs(dx)) {
      swipeGesture = null
      return
    }
    if (Math.abs(dx) < SWIPE_START_PX || Math.abs(dx) <= Math.abs(dy)) return
    gesture.horizontal = true
    if (revealedBaseId.value !== id) closeSwipeActions()
    swipingBaseId.value = id
  }
  swipeOffset.value = Math.max(-SWIPE_ACTION_WIDTH, Math.min(0, gesture.startOffset + dx))
}

function onRowPointerUp(event: PointerEvent, id: string): void {
  const gesture = swipeGesture
  if (!gesture || gesture.id !== id || gesture.pointerId !== event.pointerId) return
  if (gesture.horizontal) {
    revealedBaseId.value = swipeOffset.value < -SWIPE_ACTION_WIDTH / 2 ? id : null
    suppressedClickId = id
    if (suppressClickTimer) clearTimeout(suppressClickTimer)
    suppressClickTimer = setTimeout(() => {
      suppressedClickId = null
      suppressClickTimer = undefined
    }, 400)
  }
  swipeGesture = null
  swipingBaseId.value = null
  swipeOffset.value = 0
}

function onRowPointerCancel(event: PointerEvent, id: string): void {
  if (swipeGesture?.id !== id || swipeGesture.pointerId !== event.pointerId) return
  swipeGesture = null
  swipingBaseId.value = null
  swipeOffset.value = 0
}

function closeContextMenu(): void {
  contextMenu.value = null
}

async function openContextMenu(event: MouseEvent, base: KnowledgeBase): Promise<void> {
  if (window.matchMedia('(hover: none)').matches) return
  closeSwipeActions()
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const keyboardTriggered = event.clientX === 0 && event.clientY === 0
  const pointerX = keyboardTriggered ? rect.left + 24 : event.clientX
  const pointerY = keyboardTriggered ? rect.bottom : event.clientY
  contextMenu.value = {
    base,
    name: base.name,
    x: pointerX,
    y: pointerY,
    arrowX: 16,
    placement: 'below',
  }
  await nextTick()
  const menu = contextMenuRef.value
  if (!menu || contextMenu.value?.base.id !== base.id) return
  const gap = 9
  const placement = pointerY + gap + menu.offsetHeight + 8 <= window.innerHeight ? 'below' : 'above'
  const x = Math.max(8, Math.min(pointerX - 16, window.innerWidth - menu.offsetWidth - 8))
  const desiredY = placement === 'below' ? pointerY + gap : pointerY - menu.offsetHeight - gap
  contextMenu.value = {
    ...contextMenu.value,
    x,
    y: Math.max(8, Math.min(desiredY, window.innerHeight - menu.offsetHeight - 8)),
    arrowX: Math.max(14, Math.min(pointerX - x, menu.offsetWidth - 14)),
    placement,
  }
}

function onDocumentPointerDown(event: PointerEvent): void {
  if (contextMenuRef.value?.contains(event.target as Node)) return
  closeContextMenu()
  if (!revealedBaseId.value) return
  const row = event.target instanceof Element ? event.target.closest('.base-swipe-item') : null
  if (row?.getAttribute('data-base-id') !== revealedBaseId.value) closeSwipeActions()
}

function onDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closeContextMenu()
    closeSwipeActions()
  }
}

function openDeleteDialog(base: KnowledgeBase): void {
  if (deletingBaseId.value) return
  closeContextMenu()
  closeSwipeActions()
  deleteTarget.value = base
  deleteDialogVisible.value = true
}

async function confirmDelete(): Promise<void> {
  const base = deleteTarget.value
  if (!base || deletingBaseId.value) return
  deletingBaseId.value = base.id
  try {
    await deleteKnowledgeBase(base.id)
    if (selectedId.value === base.id) previewDocument.value = null
    deleteDialogVisible.value = false
    await refreshBases()
  } catch (error) {
    reportError(error)
  } finally {
    deletingBaseId.value = null
  }
}

async function uploadFiles(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  input.value = ''
  const baseId = selectedId.value
  if (!baseId || !files.length) return
  uploading.value = true
  try {
    for (const file of files) {
      try {
        await uploadKnowledgeDocument(baseId, file)
      } catch (error) {
        reportError(error)
      }
    }
    await Promise.all([refreshBases(), refreshDocuments()])
  } finally {
    uploading.value = false
  }
}

async function retry(item: KnowledgeDocument): Promise<void> {
  try {
    await retryKnowledgeDocument(item.id)
    await refreshDocuments()
  } catch (error) {
    reportError(error)
  }
}

function openDocumentDeleteDialog(item: KnowledgeDocument): void {
  if (deletingDocumentId.value) return
  documentDeleteTarget.value = item
  documentDeleteDialogVisible.value = true
}

async function confirmDocumentDelete(): Promise<void> {
  const item = documentDeleteTarget.value
  if (!item || deletingDocumentId.value) return
  deletingDocumentId.value = item.id
  try {
    await deleteKnowledgeDocument(item.id)
    if (previewDocument.value?.id === item.id) previewDocument.value = null
    documentDeleteDialogVisible.value = false
    await Promise.all([refreshBases(), refreshDocuments()])
  } catch (error) {
    reportError(error)
  } finally {
    deletingDocumentId.value = null
  }
}

async function previewChunks(item: KnowledgeDocument): Promise<void> {
  previewDocument.value = item
  chunksLoading.value = true
  chunks.value = []
  try {
    chunks.value = await listKnowledgeChunks(item.id)
  } catch (error) {
    reportError(error)
  } finally {
    chunksLoading.value = false
  }
}

watch(selectedId, () => {
  previewDocument.value = null
  void refreshDocuments(true)
})

onMounted(() => {
  setPageTitle('知识库')
  void refreshBases()
  window.addEventListener('resize', closeContextMenu)
  window.addEventListener('scroll', closeContextMenu, true)
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeydown)
  poller = window.setInterval(() => {
    if (documents.value.some((item) => ['pending', 'parsing', 'indexing'].includes(item.status))) {
      void refreshDocuments()
    }
  }, 2000)
})
onUnmounted(() => {
  window.clearInterval(poller)
  if (suppressClickTimer) clearTimeout(suppressClickTimer)
  window.removeEventListener('resize', closeContextMenu)
  window.removeEventListener('scroll', closeContextMenu, true)
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})
</script>

<style scoped>
.knowledge-shell {
  height: 100vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  background: #fafafa;
}
.knowledge-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 36px 56px 96px;
  color: #171717;
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #777;
  font-size: 12px;
  text-decoration: none;
}
.page-header,
.page-heading,
.primary-button,
.upload-button,
.base-panel-header,
.section-heading,
.document-actions,
.preview-head {
  display: flex;
  align-items: center;
}
.page-header {
  justify-content: space-between;
  gap: 24px;
  margin-top: 24px;
}
.page-heading {
  min-width: 0;
  gap: 14px;
}
.heading-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid #e2e2e2;
  border-radius: 7px;
  background: #fff;
  color: #666;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 680;
  letter-spacing: -0.035em;
  line-height: 1.25;
}
.page-header p {
  margin-top: 8px;
  color: #737373;
  font-size: 13px;
  line-height: 1.6;
}
.primary-button,
.upload-button,
.create-actions button:first-child {
  justify-content: center;
  gap: 8px;
  flex: 0 0 auto;
  min-height: 38px;
  padding: 0 13px;
  border: 1px solid #171717;
  border-radius: 7px;
  background: #171717;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.workspace {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  min-height: 500px;
  margin-top: 38px;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}
.base-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 20px 12px 18px;
  border-right: 1px solid #e8e8e8;
  background: #f8f8f8;
}
.base-panel-header {
  justify-content: space-between;
  gap: 10px;
  margin: 0 8px 14px;
}
.base-panel-header h2 {
  font-size: 13px;
  font-weight: 650;
}
.base-panel-header span {
  color: #888;
  font-size: 12px;
}
.create-form {
  display: grid;
  gap: 10px;
  margin: 0 4px 15px;
  padding: 13px;
  border: 1px solid #e4e4e4;
  border-radius: 7px;
  background: #fff;
}
.create-form label {
  color: #555;
  font-size: 12px;
  font-weight: 600;
}
.create-form input {
  width: 100%;
  min-width: 0;
  height: 36px;
  padding: 0 10px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  background: #fff;
  color: #222;
  font-size: 13px;
}
.create-form input::placeholder {
  color: #aaa;
}
.create-form input:focus {
  border-color: #555;
  outline: 0;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.create-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.create-actions button:first-child {
  min-height: 32px;
  padding: 0 13px;
}
.create-actions button:last-child {
  border: 0;
  background: none;
  color: #777;
  font-size: 12px;
  cursor: pointer;
}
.sidebar-hint {
  padding: 12px 8px;
  color: #999;
  font-size: 12px;
}
.base-list {
  display: grid;
  gap: 3px;
}
.base-swipe-item {
  position: relative;
  overflow: hidden;
  border-radius: 5px;
}
.base-actions {
  position: absolute;
  inset: 0 0 0 auto;
  display: flex;
  width: 64px;
}
.base-swipe-delete {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 0;
  border: 0;
  background: #e56565;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.base-item {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 38px;
  padding: 7px 9px;
  border: 0;
  border-radius: 5px;
  background: #f8f8f8;
  color: #444;
  text-align: left;
  cursor: pointer;
  touch-action: pan-y;
  -webkit-tap-highlight-color: transparent;
  transition: transform 200ms cubic-bezier(0.2, 0.75, 0.25, 1);
}
.base-item.is-dragging {
  transition: none;
}
.base-item svg {
  flex: 0 0 auto;
  color: #777;
}
.base-item.selected {
  background: #eaeaea;
  color: #171717;
  font-weight: 600;
}
.base-item.selected svg {
  color: #333;
}
.base-name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
.base-item small {
  color: #888;
  font-size: 11px;
  font-weight: 400;
}
.document-panel {
  min-width: 0;
  padding: 28px 30px 36px;
}
.document-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 26px;
  border-bottom: 1px solid #ececec;
}
.document-heading {
  min-width: 0;
}
.eyebrow {
  display: block;
  margin-bottom: 8px;
  color: #999;
  font-size: 11px;
}
.document-heading h2 {
  overflow-wrap: anywhere;
  color: #222;
  font-size: 21px;
  font-weight: 680;
  letter-spacing: -0.025em;
}
.document-heading p {
  margin-top: 8px;
  color: #888;
  font-size: 12px;
  line-height: 1.5;
}
.upload-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
.upload-button {
  display: inline-flex;
}
.upload-actions span {
  color: #999;
  font-size: 11px;
  white-space: nowrap;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.section-heading {
  justify-content: space-between;
  margin: 28px 0 15px;
}
.section-heading h3 {
  color: #222;
  font-size: 15px;
  font-weight: 680;
}
.section-heading span {
  margin-left: 5px;
  color: #888;
  font-size: 12px;
  font-weight: 500;
}
.document-state {
  display: grid;
  min-height: 240px;
  justify-items: center;
  align-content: center;
  gap: 10px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  color: #777;
  text-align: center;
  font-size: 13px;
}
.empty-state svg {
  color: #aaa;
}
.empty-state strong {
  color: #444;
  font-size: 15px;
  font-weight: 650;
}
.empty-state p {
  color: #888;
  font-size: 12px;
}
.document-list {
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}
.document-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 15px 16px;
}
.document-item + .document-item {
  border-top: 1px solid #ededed;
}
.file-icon {
  display: grid;
  width: 34px;
  height: 38px;
  place-items: center;
  border: 1px solid #e7e7e7;
  border-radius: 6px;
  background: #fafafa;
  color: #777;
}
.document-main {
  display: grid;
  min-width: 0;
  gap: 5px;
}
.document-main strong {
  overflow: hidden;
  color: #222;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.document-main span {
  color: #999;
  font-size: 11px;
}
.error-text {
  overflow-wrap: anywhere;
  color: #ad5757;
  font-size: 11px;
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 5px;
  background: #f5f5f5;
  color: #777;
  font-size: 11px;
  white-space: nowrap;
}
.status::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #aaa;
  content: '';
}
.status.ready {
  background: #edf5ee;
  color: #4c7454;
}
.status.ready::before {
  background: #6a9a71;
}
.status.failed {
  background: #fbefed;
  color: #a45b51;
}
.status.failed::before {
  background: #be766a;
}
.document-actions {
  justify-content: flex-end;
  gap: 10px;
}
.document-actions button,
.document-actions a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  border: 0;
  background: none;
  color: #666;
  font-size: 11px;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
}
.document-actions .delete-document {
  color: #dc2626;
}
.preview-panel {
  max-height: 430px;
  margin-top: 24px;
  overflow-y: auto;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}
.preview-head {
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px;
  border-bottom: 1px solid #ededed;
}
.preview-head h3 {
  overflow-wrap: anywhere;
  color: #222;
  font-size: 14px;
  font-weight: 650;
}
.preview-head button {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 5px;
  background: none;
  color: #777;
  cursor: pointer;
}
.preview-loading {
  padding: 20px;
  color: #888;
  font-size: 12px;
}
.chunk-item {
  padding: 17px 20px;
}
.chunk-item + .chunk-item {
  border-top: 1px solid #ededed;
}
.chunk-item strong {
  color: #333;
  font-size: 12px;
}
.chunk-item p {
  margin-top: 9px;
  color: #666;
  font-size: 12px;
  line-height: 1.7;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.empty-workspace {
  display: flex;
  min-height: 450px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
}
.empty-icon {
  display: grid;
  width: 58px;
  height: 58px;
  margin-bottom: 6px;
  place-items: center;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  color: #888;
}
.empty-workspace h2 {
  color: #333;
  font-size: 16px;
  font-weight: 650;
}
.empty-workspace p {
  max-width: 260px;
  color: #888;
  font-size: 12px;
  line-height: 1.6;
}
.base-context-menu {
  position: fixed;
  z-index: 2000;
  width: 164px;
  padding: 5px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 30px rgb(25 35 50 / 14%);
  transform-origin: var(--arrow-x) top;
  animation: context-menu-appear 160ms cubic-bezier(0.2, 1, 0.3, 1) both;
}
.base-context-menu::before {
  position: absolute;
  top: -5px;
  left: calc(var(--arrow-x) - 5px);
  width: 8px;
  height: 8px;
  border-top: 1px solid #e5e7eb;
  border-left: 1px solid #e5e7eb;
  background: #fff;
  transform: rotate(45deg);
  content: '';
}
.base-context-menu.is-above {
  transform-origin: var(--arrow-x) bottom;
}
.base-context-menu.is-above::before {
  top: auto;
  bottom: -5px;
  border: 0;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}
.base-context-delete {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  height: 38px;
  padding: 0 11px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #d35b5b;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.base-context-delete:focus-visible {
  outline: 2px solid #909399;
  outline-offset: -2px;
}
:global(.knowledge-delete-overlay) {
  background: rgb(0 0 0 / 22%);
  backdrop-filter: blur(3px);
}
:global(.knowledge-delete-dialog.el-dialog) {
  --el-dialog-padding-primary: 0px;
  width: min(420px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgb(0 0 0 / 16%);
}
.delete-dialog-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 24px 0;
  color: #202020;
  font-size: 15px;
  font-weight: 500;
  line-height: 20px;
}
.delete-warning-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f99a00;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}
.delete-dialog-description {
  margin: 10px 0 0;
  padding: 0 24px 0 54px;
  color: #383838;
  font-size: 14px;
  line-height: 20px;
  overflow-wrap: anywhere;
}
:global(.knowledge-delete-dialog .el-dialog__footer) {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 24px 24px 22px;
}
.delete-dialog-cancel,
.delete-dialog-confirm {
  min-width: 80px;
  height: 38px;
  padding: 0 15px;
  border-radius: 9px;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.delete-dialog-cancel {
  border: 1px solid #e2e2e2;
  background: #fff;
  color: #242424;
}
.delete-dialog-confirm {
  border: 1px solid #ff3b38;
  background: #ff3b38;
  color: #fff;
}
.delete-dialog-cancel:disabled,
.delete-dialog-confirm:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.delete-dialog-cancel:focus-visible,
.delete-dialog-confirm:focus-visible {
  outline: 2px solid #303030;
  outline-offset: 2px;
}
@keyframes context-menu-appear {
  from {
    opacity: 0;
    transform: scale(0.94) translateY(-3px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .base-context-menu {
    animation: none;
  }
}
button:disabled {
  cursor: wait;
  opacity: 0.5;
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid #444;
  outline-offset: 3px;
}
@supports (height: 100dvh) {
  .knowledge-shell {
    height: 100dvh;
  }
}
@media (hover: hover) {
  .back-link:hover,
  .document-actions button:hover,
  .document-actions a:hover,
  .create-actions button:last-child:hover {
    color: #171717;
  }
  .document-actions .delete-document:hover {
    color: #b91c1c;
  }
  .primary-button:hover,
  .upload-button:hover,
  .create-actions button:first-child:hover {
    background: #333;
  }
  .base-item:hover {
    background: #eaeaea;
  }
  .base-context-delete:hover {
    background: #fff2f2;
  }
  .delete-dialog-cancel:not(:disabled):hover {
    background: #f7f7f7;
  }
  .delete-dialog-confirm:not(:disabled):hover {
    border-color: #e83330;
    background: #e83330;
  }
  .preview-head button:hover {
    background: #f3f3f3;
  }
}
@media (max-width: 900px) {
  .knowledge-page {
    padding: 32px 28px 72px;
  }
  .workspace {
    grid-template-columns: 215px minmax(0, 1fr);
  }
  .document-header {
    flex-direction: column;
  }
  .upload-actions {
    align-items: flex-start;
  }
  .document-item {
    grid-template-columns: 34px minmax(0, 1fr) auto;
  }
  .document-actions {
    grid-column: 2 / -1;
    justify-content: flex-start;
  }
}
@media (max-width: 700px) {
  :global(.knowledge-delete-overlay) {
    backdrop-filter: none;
  }
  .knowledge-page {
    padding: 24px 18px 60px;
  }
  .page-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .workspace {
    grid-template-columns: minmax(0, 1fr);
    margin-top: 30px;
  }
  .base-panel {
    border-right: 0;
    border-bottom: 1px solid #e8e8e8;
  }
  .base-list {
    max-height: 220px;
    overflow-y: auto;
  }
  .document-panel {
    padding: 22px 20px 30px;
  }
  .empty-workspace {
    min-height: 280px;
  }
}
@media (max-width: 480px) {
  .knowledge-page {
    padding: 20px 16px 48px;
  }
  .page-header {
    gap: 18px;
  }
  .page-header h1 {
    font-size: 26px;
  }
  .primary-button {
    align-self: flex-start;
  }
  .upload-actions span {
    max-width: 100%;
    white-space: normal;
    line-height: 1.5;
  }
  .document-panel {
    padding: 20px 16px 28px;
  }
  .document-item {
    gap: 10px;
    padding: 14px 12px;
  }
  .document-actions {
    flex-wrap: wrap;
  }
}
@media (any-pointer: coarse) {
  .primary-button,
  .upload-button,
  .base-item,
  .base-swipe-delete,
  .base-context-delete,
  .delete-dialog-cancel,
  .delete-dialog-confirm,
  .document-actions button,
  .document-actions a,
  .preview-head button {
    min-height: 40px;
  }
  .create-form input {
    height: 44px;
    font-size: 16px;
  }
}
</style>
