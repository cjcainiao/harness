<template>
  <div class="chat-input-box">
    <div
      class="input-card"
      :class="{ 'is-file-dragging': isFileDragging }"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onFileDrop"
    >
      <div v-if="isFileDragging" class="file-drop-hint" aria-hidden="true">松开以添加文件</div>
      <input
        ref="fileInputRef"
        class="file-input"
        type="file"
        multiple
        tabindex="-1"
        aria-hidden="true"
        @change="onFilesSelected"
      />
      <div v-if="selectedFiles.length" class="selected-files" role="list" aria-label="已选文件">
        <div
          v-for="(item, index) in selectedFiles"
          :key="fileKey(item.file)"
          class="file-chip"
          role="listitem"
        >
          <img
            v-if="item.previewUrl"
            class="file-thumbnail"
            :src="item.previewUrl"
            :alt="`${item.file.name} 的缩略图`"
          />
          <FileIcon
            v-else
            class="file-card-icon"
            :size="22"
            :stroke-width="1.7"
            aria-hidden="true"
          />
          <div class="file-chip-name">
            <component
              :is="fileIcons[fileKind(item.file)]"
              class="file-type-icon"
              :class="`is-${fileKind(item.file)}`"
              :size="14"
              :stroke-width="1.8"
              aria-hidden="true"
            />
            <span>{{ item.file.name }}</span>
          </div>
          <button
            class="file-remove-btn"
            type="button"
            :aria-label="`移除文件 ${item.file.name}`"
            @click="removeFile(index)"
          >
            <X :size="14" aria-hidden="true" />
          </button>
        </div>
      </div>
      <!-- 输入区 -->
      <textarea
        ref="textareaRef"
        v-model="text"
        class="input-textarea"
        rows="1"
        placeholder="规划与编程，@ 添加上下文，/ 使用命令"
        @input="autoResize"
        @keydown.enter="onEnter"
      />
      <!-- 底部工具行 -->
      <div class="input-toolbar">
        <div class="toolbar-left">
          <ElTooltip
            content="添加附件"
            placement="top"
            :show-after="300"
            :trigger="['hover', 'focus']"
          >
            <button
              class="tool-btn tool-icon-btn"
              type="button"
              aria-label="添加附件"
              @click="openFilePicker"
            >
              <Plus :size="15" :stroke-width="2.5" aria-hidden="true" />
            </button>
          </ElTooltip>
          <ElPopover
            v-model:visible="isAccessMenuOpen"
            placement="top-start"
            trigger="click"
            role="dialog"
            :width="360"
            :offset="10"
            :show-arrow="true"
            :hide-after="0"
            :persistent="false"
            :popper-style="{
              padding: '6px',
              borderRadius: '9px',
              maxWidth: 'calc(100vw - 16px)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
            }"
          >
            <template #reference>
              <button
                class="permission-trigger"
                :class="{ 'is-full': permissionMode === 'full' }"
                type="button"
                aria-haspopup="dialog"
                :aria-expanded="isAccessMenuOpen"
                :aria-label="`访问权限：${selectedPermission.title}`"
              >
                <component
                  :is="selectedPermission.icon"
                  :size="14"
                  :stroke-width="1.8"
                  aria-hidden="true"
                />
                <span>{{ selectedPermission.shortLabel }}</span>
              </button>
            </template>

            <div
              class="permission-menu"
              aria-label="访问权限设置"
              @keydown.esc.stop.prevent="isAccessMenuOpen = false"
            >
              <div class="permission-options" aria-label="访问权限">
                <button
                  v-for="option in permissionOptions"
                  :key="option.value"
                  class="permission-option"
                  :class="{ 'is-selected': permissionMode === option.value }"
                  type="button"
                  :aria-pressed="permissionMode === option.value"
                  @click="selectPermission(option.value)"
                >
                  <component
                    :is="option.icon"
                    class="permission-option-icon"
                    :size="15"
                    :stroke-width="1.7"
                    aria-hidden="true"
                  />
                  <span class="permission-option-copy">
                    <span class="permission-option-title-row">
                      <span class="permission-option-title">{{ option.title }}</span>
                      <Check
                        v-if="permissionMode === option.value"
                        class="permission-check"
                        :size="14"
                        :stroke-width="1.8"
                        aria-hidden="true"
                      />
                    </span>
                    <span class="permission-option-description">{{ option.description }}</span>
                  </span>
                </button>
              </div>
            </div>
          </ElPopover>
        </div>
        <div class="toolbar-right">
          <div class="model-picker" @keydown.esc.stop.prevent="closeModelMenu">
            <ElPopover
              v-model:visible="isModelMenuOpen"
              placement="top-end"
              trigger="click"
              role="dialog"
              :width="300"
              :offset="10"
              :show-arrow="true"
              :hide-after="0"
              :persistent="false"
              @before-enter="prepareModelMenu"
            >
              <template #reference>
                <button
                  ref="modelButtonRef"
                  class="tool-btn tool-model-btn"
                  type="button"
                  aria-haspopup="dialog"
                  :aria-expanded="isModelMenuOpen"
                  :aria-label="`模型 ${selectedModel}，推理强度 ${reasoningEffort}`"
                >
                  <span class="model-name">{{ selectedModel }}</span>
                  <span class="model-effort">{{ reasoningEffort }}</span>
                  <ChevronDown class="model-chevron" :size="14" />
                </button>
              </template>

              <div
                class="model-menu"
                aria-label="模型设置"
                @keydown.esc.stop.prevent="closeModelMenu"
              >
                <div
                  class="effort-panel is-energy"
                  :class="{ 'is-max': effortPreview >= 99 }"
                  :style="{
                    '--nrs-ratio': effortRatio,
                    '--nrs-canvas-opacity': effortRatio > 0 ? 1 : 0,
                    '--nrs-dots-opacity': 1 - effortIntensity * 0.72,
                  }"
                >
                  <div class="effort-panel-header">
                    <span>推理强度</span>
                    <strong>{{ previewEffort }}</strong>
                  </div>
                  <div class="effort-labels">
                    <button
                      v-for="effort in reasoningOptions"
                      :key="effort"
                      class="effort-label"
                      :class="{ 'is-active': previewEffort === effort }"
                      type="button"
                      @click="chooseEffort(effort)"
                    >
                      {{ effort }}
                    </button>
                  </div>
                  <div class="effort-track">
                    <div class="effort-track-dots" aria-hidden="true">
                      <i v-for="effort in reasoningOptions" :key="effort" />
                    </div>
                    <EnergyField
                      :active="effortEnergized"
                      :intensity="visibleEffortIntensity"
                      :ratio="effortRatio"
                    />
                    <div class="effort-track-thumb" aria-hidden="true" />
                    <input
                      class="effort-range"
                      type="range"
                      min="0"
                      max="100"
                      step="0.1"
                      :value="effortPreview"
                      :aria-valuetext="previewEffort"
                      aria-label="推理强度"
                      @input="previewOnly"
                      @pointerdown="beginDrag"
                      @pointerup="finishDrag"
                      @pointercancel="cancelDrag"
                      @lostpointercapture="finishDragIfDragging"
                      @keydown="onSliderKeyDown"
                      @blur="finishDragIfDragging"
                    />
                  </div>
                </div>
                <template v-if="showModelOptions">
                  <div class="menu-divider" />
                  <div class="menu-heading">模型</div>
                  <div class="model-options-scroll" role="group" aria-label="可选模型">
                    <button
                      v-for="model in modelOptions"
                      :key="model"
                      class="menu-option"
                      :class="{ 'is-selected': selectedModel === model }"
                      type="button"
                      role="menuitemradio"
                      :aria-checked="selectedModel === model"
                      @click="chooseModel(model)"
                    >
                      <span>{{ model }}</span>
                      <Check v-if="selectedModel === model" :size="15" />
                    </button>
                  </div>
                </template>
                <button
                  v-else
                  class="menu-option model-next"
                  type="button"
                  @click="showModelOptions = true"
                >
                  <span>选择模型</span>
                  <ChevronRight :size="14" />
                </button>
              </div>
            </ElPopover>
          </div>
          <button ref="sendButtonRef" class="send-btn" type="button" :disabled="!text.trim()">
            <ArrowUp :size="15" :stroke-width="2.25" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ArrowUp,
  Check,
  CirclePlay,
  ChevronDown,
  ChevronRight,
  File as FileIcon,
  FileImage,
  FileSpreadsheet,
  FileText,
  Plus,
  ShieldCheck,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import { ElPopover, ElTooltip } from 'element-plus'
import 'element-plus/es/components/popover/style/css'
import 'element-plus/es/components/tooltip/style/css'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import EnergyField from './EnergyField.vue'

const text = ref('')
type PermissionMode = 'ask' | 'auto' | 'full'
const permissionMode = ref<PermissionMode>('full')
const isAccessMenuOpen = ref(false)
const textareaRef = ref<HTMLTextAreaElement>()
const sendButtonRef = ref<HTMLButtonElement>()
const fileInputRef = ref<HTMLInputElement>()
type SelectedFile = { file: File; previewUrl: string | null }
type FileKind = 'image' | 'sheet' | 'pdf' | 'document' | 'other'
const selectedFiles = ref<SelectedFile[]>([])
const isFileDragging = ref(false)
const modelButtonRef = ref<HTMLButtonElement>()
const isModelMenuOpen = ref(false)
const showModelOptions = ref(false)
let dragDepth = 0
const fileIcons = {
  image: FileImage,
  sheet: FileSpreadsheet,
  pdf: FileText,
  document: FileText,
  other: FileIcon,
} as const

const permissionOptions = [
  {
    value: 'ask',
    title: '询问审批',
    shortLabel: '询问审批',
    description: '执行命令、修改 Workspace 外文件或访问网络前，始终询问',
    icon: ShieldCheck,
  },
  {
    value: 'auto',
    title: '自动审批',
    shortLabel: '自动审批',
    description: '仅在检测到潜在风险时询问',
    icon: CirclePlay,
  },
  {
    value: 'full',
    title: '完全访问',
    shortLabel: '完全访问',
    description: '不再询问，可自由访问你的文件、终端和网络',
    icon: TriangleAlert,
  },
] as const
const selectedPermission = computed(
  () =>
    permissionOptions.find((option) => option.value === permissionMode.value) ??
    permissionOptions[0],
)

function selectPermission(value: PermissionMode) {
  permissionMode.value = value
  isAccessMenuOpen.value = false
}

function fileKind(file: File): FileKind {
  if (file.type.startsWith('image/')) return 'image'
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (extension && ['xls', 'xlsx', 'csv', 'ods'].includes(extension)) return 'sheet'
  if (extension === 'pdf') return 'pdf'
  if (extension && ['doc', 'docx', 'txt', 'md', 'rtf'].includes(extension)) return 'document'
  return 'other'
}

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function addFiles(files: File[]) {
  const existing = new Set(selectedFiles.value.map((item) => fileKey(item.file)))
  for (const file of files) {
    const key = fileKey(file)
    if (!existing.has(key)) {
      selectedFiles.value.push({
        file,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
      })
      existing.add(key)
    }
  }
}

function onFilesSelected(event: Event) {
  const input = event.currentTarget as HTMLInputElement
  addFiles(Array.from(input.files ?? []))
  input.value = ''
}

function hasDraggedFiles(event: DragEvent) {
  return Array.from(event.dataTransfer?.types ?? []).includes('Files')
}

function onDragEnter(event: DragEvent) {
  if (!hasDraggedFiles(event)) return
  dragDepth += 1
  isFileDragging.value = true
}

function onDragOver(event: DragEvent) {
  if (!hasDraggedFiles(event)) return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
}

function onDragLeave() {
  if (!isFileDragging.value) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) isFileDragging.value = false
}

function onFileDrop(event: DragEvent) {
  const files = Array.from(event.dataTransfer?.files ?? [])
  dragDepth = 0
  isFileDragging.value = false
  if (!hasDraggedFiles(event) && files.length === 0) return
  event.preventDefault()
  addFiles(files)
}

function removeFile(index: number) {
  const [removed] = selectedFiles.value.splice(index, 1)
  if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl)
}

// 前端模拟选项
const modelOptions = ['DeepSeek Flash', 'GPT-4o', 'Claude Sonnet'] as const
const reasoningOptions = ['关闭', '低', '中等', '高'] as const
type ReasoningEffort = (typeof reasoningOptions)[number]

const selectedModel = ref<(typeof modelOptions)[number]>('DeepSeek Flash')
const reasoningEffort = ref<ReasoningEffort>('中等')
const reasoningIndex = computed(() => reasoningOptions.indexOf(reasoningEffort.value))
const committed = computed(() => (reasoningIndex.value / (reasoningOptions.length - 1)) * 100)
const effortPreview = ref(committed.value)
const dragging = ref(false)
const settling = ref(false)
const effortRatio = computed(() => effortPreview.value / 100)
const previewIndex = computed(() =>
  Math.min(
    reasoningOptions.length - 1,
    Math.max(0, Math.round(effortRatio.value * (reasoningOptions.length - 1))),
  ),
)
const previewEffort = computed(() => reasoningOptions[previewIndex.value]!)
const effortEnergized = computed(
  () => effortRatio.value > 0 && (dragging.value || settling.value || effortPreview.value >= 99.95),
)
const effortIntensity = computed(() => {
  const bounded = Math.max(
    0,
    Math.min(1, Number.isFinite(effortRatio.value) ? effortRatio.value : 0),
  )
  const stops = [0, 0.24, 0.58, 1]
  const scaled = bounded * (stops.length - 1)
  const left = Math.min(stops.length - 2, Math.floor(scaled))
  const progress = scaled - left
  return stops[left]! + (stops[left + 1]! - stops[left]!) * progress
})
const visibleEffortIntensity = computed(() =>
  effortRatio.value > 0 ? Math.min(1, effortIntensity.value * 1.4 + 0.15) : 0,
)
let dragTimer = 0
let settleTimer = 0
let draggingNow = false

watch(committed, (value) => {
  if (!draggingNow) effortPreview.value = value
})

function prepareModelMenu() {
  showModelOptions.value = false
  effortPreview.value = committed.value
}

function chooseModel(model: (typeof modelOptions)[number]) {
  selectedModel.value = model
  isModelMenuOpen.value = false
}

async function closeModelMenu() {
  isModelMenuOpen.value = false
  await nextTick()
  modelButtonRef.value?.focus()
}

function commitAt(position: number) {
  draggingNow = false
  window.clearTimeout(dragTimer)
  dragging.value = false
  const index = Math.min(
    reasoningOptions.length - 1,
    Math.max(0, Math.round((position / 100) * (reasoningOptions.length - 1))),
  )
  const effort = reasoningOptions[index]!
  effortPreview.value = (index / (reasoningOptions.length - 1)) * 100
  window.clearTimeout(settleTimer)
  settling.value = true
  settleTimer = window.setTimeout(
    () => {
      settling.value = false
    },
    index === reasoningOptions.length - 1 ? 1840 : 620,
  )
  reasoningEffort.value = effort
}

function armDragTimer() {
  window.clearTimeout(dragTimer)
  dragTimer = window.setTimeout(() => {
    if (draggingNow) commitAt(effortPreview.value)
  }, 450)
}

function previewOnly(event: Event) {
  effortPreview.value = Number((event.currentTarget as HTMLInputElement).value)
  if (draggingNow) armDragTimer()
}

function beginDrag(event: PointerEvent) {
  const slider = event.currentTarget as HTMLInputElement
  slider.setPointerCapture?.(event.pointerId)
  draggingNow = true
  dragging.value = true
  armDragTimer()
}

function finishDrag(event: Event) {
  const slider = event.currentTarget as HTMLInputElement
  commitAt(Number(slider.value))
  if (event instanceof PointerEvent && slider.hasPointerCapture?.(event.pointerId)) {
    slider.releasePointerCapture(event.pointerId)
  }
}

function finishDragIfDragging(event: Event) {
  if (draggingNow) finishDrag(event)
}

function cancelDrag() {
  draggingNow = false
  window.clearTimeout(dragTimer)
  dragging.value = false
  effortPreview.value = committed.value
}

function chooseEffort(effort: ReasoningEffort) {
  const index = reasoningOptions.indexOf(effort)
  const position = (index / (reasoningOptions.length - 1)) * 100
  effortPreview.value = position
  commitAt(position)
}

function onSliderKeyDown(event: KeyboardEvent) {
  let targetIndex: number
  if (['ArrowRight', 'ArrowUp', 'PageUp'].includes(event.key))
    targetIndex = Math.min(reasoningOptions.length - 1, previewIndex.value + 1)
  else if (['ArrowLeft', 'ArrowDown', 'PageDown'].includes(event.key))
    targetIndex = Math.max(0, previewIndex.value - 1)
  else if (event.key === 'Home') targetIndex = 0
  else if (event.key === 'End') targetIndex = reasoningOptions.length - 1
  else return
  event.preventDefault()
  chooseEffort(reasoningOptions[targetIndex]!)
}

onUnmounted(() => {
  window.clearTimeout(dragTimer)
  window.clearTimeout(settleTimer)
  for (const item of selectedFiles.value) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  }
})

/** 输入框随内容增高，超过上限后内部滚动 */
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`
}

function onEnter(event: KeyboardEvent) {
  if (event.shiftKey || event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendButtonRef.value?.click()
}
</script>

<style scoped>
.chat-input-box {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 16px;
}
.input-card {
  position: relative;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.input-card:focus-within {
  border-color: #c7ccd4;
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.08);
}
.input-card.is-file-dragging {
  border-color: #8fa8d4;
}
.file-drop-hint {
  position: absolute;
  z-index: 10;
  inset: 0;
  display: grid;
  place-items: center;
  border: 1px dashed #8fa8d4;
  border-radius: 13px;
  background: rgba(248, 250, 255, 0.94);
  color: #526a98;
  font-size: 13px;
  font-weight: 500;
  pointer-events: none;
}
.input-textarea {
  display: block;
  width: 100%;
  min-height: 56px;
  max-height: 200px;
  padding: 12px 14px 4px;
  border: none;
  outline: none;
  background: transparent;
  resize: none;
  line-height: 22px;
}
.input-textarea::placeholder {
  color: #9ca3af;
}
.file-input {
  display: none;
}
.selected-files {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
  max-height: 264px;
  overflow-y: auto;
  padding: 10px 14px 6px;
}
.file-chip {
  box-sizing: border-box;
  position: relative;
  flex: 0 0 160px;
  width: 160px;
  height: 120px;
  max-width: 100%;
  border: 1px solid #d6d9de;
  border-radius: 9px;
  background: #f5f6f8;
  color: #454a50;
  font-size: 12px;
}
.file-chip svg {
  flex-shrink: 0;
}
.file-card-icon {
  position: absolute;
  top: 34px;
  left: 50%;
  color: #737a82;
  transform: translateX(-50%);
}
.file-thumbnail {
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  width: 100%;
  height: calc(100% - 26px);
  border-radius: 8px 8px 0 0;
  background: #e9ebef;
  object-fit: cover;
}
.file-chip-name {
  position: absolute;
  right: 8px;
  bottom: 6px;
  left: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  line-height: 16px;
}
.file-chip-name span {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.file-type-icon.is-sheet {
  color: #10a452;
}
.file-type-icon.is-image {
  color: #6784b2;
}
.file-type-icon.is-pdf {
  color: #d95555;
}
.file-type-icon.is-document {
  color: #5681c9;
}
.file-type-icon.is-other {
  color: #737a82;
}
.file-remove-btn {
  position: absolute;
  top: -9px;
  right: -8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #fff;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.file-remove-btn::before {
  position: absolute;
  inset: 5px;
  border-radius: 50%;
  background: rgba(20, 24, 30, 0.78);
  content: '';
}
.file-remove-btn svg {
  position: relative;
  width: 11px;
  height: 11px;
}
.file-remove-btn:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 1px;
}
.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 8px;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tool-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #4b5563;
  font-size: 13px;
  cursor: pointer;
}
.tool-icon-btn {
  border-color: transparent;
}
.tool-model-btn {
  gap: 8px;
  max-width: min(50vw, 260px);
  padding: 0 6px;
  border-color: transparent;
  font-weight: 500;
  color: #1f2328;
}
.model-picker {
  position: relative;
}
.model-name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.model-effort,
.model-chevron {
  flex-shrink: 0;
  color: #8b9098;
  font-weight: 400;
}
.model-menu {
  max-height: min(420px, 60vh);
  overflow-y: auto;
  overscroll-behavior: contain;
  touch-action: pan-y;
  -webkit-overflow-scrolling: touch;
}
.menu-heading {
  padding: 7px 10px 5px;
  color: #8b9098;
  font-size: 11px;
  font-weight: 600;
}
.model-options-scroll {
  max-height: min(176px, calc(60vh - 150px));
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  touch-action: pan-y;
  -webkit-overflow-scrolling: touch;
}
.menu-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 34px;
  padding: 6px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #303133;
  cursor: pointer;
  text-align: left;
}
.menu-option.is-selected {
  background: #f2f4f7;
}
.menu-option svg {
  flex-shrink: 0;
}
.model-next {
  margin-top: 6px;
  color: #4b5563;
}
.menu-divider {
  height: 1px;
  margin: 6px 4px;
  background: #e9ebef;
}
.effort-panel {
  margin: 4px;
  padding: 10px 12px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  color: #303133;
}
.effort-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #8b9098;
  font-size: 11px;
}
.effort-panel-header strong {
  color: #303133;
  font-size: 12px;
  font-weight: 600;
}
.effort-labels {
  position: relative;
  z-index: 5;
  display: flex;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 4px;
  padding: 0 2px;
}
.effort-label {
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #8b9098;
  cursor: pointer;
  font-size: 10px;
  font-weight: 500;
  line-height: 16px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.effort-label.is-active {
  color: #303133;
  font-weight: 600;
}
.effort-track {
  --nrs-thumb-center: calc(14px + (100% - 28px) * var(--nrs-ratio));
  box-sizing: border-box;
  position: relative;
  z-index: 2;
  height: 28px;
  overflow: hidden;
  border: 1px solid #d8d6dc;
  border-radius: 9px;
  background: #fff;
  isolation: isolate;
}
.effort-track-dots {
  position: absolute;
  z-index: 2;
  inset: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}
.effort-track-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #8c8592;
  opacity: var(--nrs-dots-opacity);
}
.effort-panel.is-max .effort-track-dots i {
  opacity: 0;
}
.effort-panel.is-energy :deep(.nrs-energy) {
  opacity: var(--nrs-canvas-opacity);
}
.effort-track-thumb {
  box-sizing: border-box;
  position: absolute;
  left: var(--nrs-thumb-center);
  top: 50%;
  z-index: 6;
  width: 27px;
  height: 27px;
  border: 0.5px solid #00000014;
  border-radius: 9px;
  background: linear-gradient(170deg, #fff 0%, #f1f1f2 42%, #dedee1 100%);
  box-shadow:
    0 0.5px 1px #0000002e,
    0 2px 6px #00000040,
    0 5px 12px #00000020,
    inset 0 0.5px #ffffffd9;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.effort-range {
  appearance: none;
  position: absolute;
  inset: 0;
  z-index: 8;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  cursor: grab;
  opacity: 0;
  touch-action: none;
}
.effort-range:active {
  cursor: grabbing;
}
.effort-range::-webkit-slider-thumb {
  appearance: none;
  width: 28px;
  height: 28px;
}
.effort-range::-moz-range-thumb {
  width: 28px;
  height: 28px;
}
.effort-track:has(.effort-range:focus-visible) {
  outline: 2px solid #be91f5;
  outline-offset: 2px;
}
.effort-track:has(.effort-range:active) .effort-track-thumb {
  transform: translate(-50%, -50%) scale(0.95);
}
.permission-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: #f7f7f8;
  color: #555b63;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.permission-trigger.is-full {
  color: #ef4444;
}
.permission-trigger:focus-visible,
.permission-option:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
}
.permission-trigger:active {
  background: #e9eaed;
}
.permission-menu {
  padding: 0;
}
.permission-options {
  display: grid;
  gap: 0;
}
.permission-option {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  min-height: 49px;
  padding: 7px 7px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #303030;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}
.permission-option-icon {
  flex-shrink: 0;
  margin-top: 2px;
}
.permission-option-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 17px;
}
.permission-option-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.permission-option-title {
  font-size: 13px;
  font-weight: 500;
}
.permission-option-description {
  color: #888;
  font-size: 11.5px;
}
.permission-option.is-selected {
  color: #ef4444;
}
.permission-option.is-selected .permission-option-description {
  color: #ef4444;
}
.permission-check {
  flex-shrink: 0;
  margin-left: auto;
}
.permission-option:active {
  background: #eceef1;
}
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #0d0d0d;
  color: #fff;
  cursor: pointer;
  transition:
    background 0.15s,
    transform 0.1s;
}
.send-btn:active {
  transform: scale(0.94);
}
.send-btn:disabled {
  background: #e8e8e8;
  color: #b0b0b0;
  cursor: default;
}
@media (hover: hover) {
  .permission-trigger:hover {
    background: #eeeef0;
  }
  .permission-option:hover {
    background: #f3f4f6;
  }
  .file-chip .file-remove-btn {
    opacity: 0;
    pointer-events: none;
  }
  .file-chip:hover .file-remove-btn,
  .file-chip .file-remove-btn:focus-visible {
    opacity: 1;
    pointer-events: auto;
  }
  .file-remove-btn:hover::before {
    background: #111;
  }
  .tool-btn:hover {
    background: #f3f4f6;
  }
  .menu-option:hover {
    background: #f2f4f7;
  }
  .effort-label:hover {
    color: #303133;
    font-weight: 600;
  }
  .send-btn:not(:disabled):hover {
    background: #333;
  }
}
@media (any-pointer: coarse) {
  .permission-trigger {
    min-height: 36px;
  }
  .permission-option {
    min-height: 48px;
  }
  .file-chip .file-remove-btn {
    opacity: 1;
    pointer-events: auto;
  }
  .tool-btn {
    min-height: 36px;
  }
  .menu-option {
    min-height: 42px;
  }
  .effort-label {
    min-height: 28px;
    font-size: 12px;
  }
  .effort-track {
    height: 36px;
  }
  .send-btn {
    width: 40px;
    height: 40px;
  }
}
.tool-btn:active,
.menu-option:active {
  background: #e9ecf1;
}
.file-remove-btn:active::before {
  background: #111;
}
.effort-label:active {
  color: #303133;
  font-weight: 600;
}
.send-btn:not(:disabled):active {
  background: #333;
}
</style>
