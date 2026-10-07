<!--消息输入组件-->
<template>
  <div ref="inputRootRef" class="chat-input-box">
    <SlashCommandMenu
      v-if="isCommandMenuOpen"
      ref="commandMenuRef"
      :query="commandQuery ?? ''"
      @select="selectCommand"
    />
    <div
      class="input-card"
      :class="{ 'is-file-dragging': isFileDragging }"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onFileDrop"
    >
      <div v-if="isFileDragging" class="file-drop-hint" aria-hidden="true">松开以添加文件</div>
      <!-- 顶边手柄：外层透明命中区跨边框居中，内层胶囊悬停/聚焦才显形，双击恢复自动高度 -->
      <div
        class="resize-handle"
        :class="{ 'is-resizing': isResizing }"
        role="separator"
        aria-label="拖动调整输入框高度"
        @pointerdown="onResizePointerDown"
        @pointermove="onResizePointerMove"
        @pointerup="onResizePointerUp"
        @pointercancel="onResizePointerUp"
        @dblclick="resetInputHeight"
      >
        <span class="resize-grip"></span>
      </div>
      <input
        ref="fileInputRef"
        class="file-input"
        type="file"
        multiple
        tabindex="-1"
        aria-hidden="true"
        @change="onFilesSelected"
      />
      <div
        v-if="selectedFiles.length"
        ref="filesScrollRef"
        class="selected-files"
        :class="{ 'is-dragging': filesDragging }"
        role="list"
        aria-label="已选文件"
        @pointerdown="onFilesPointerDown"
        @pointermove="onFilesPointerMove"
        @pointerup="onFilesPointerUp"
        @pointercancel="onFilesPointerUp"
        @click.capture="onFilesClickCapture"
      >
        <AttachmentCard
          v-for="(item, index) in selectedFiles"
          :key="fileKey(item.file)"
          :name="item.file.name"
          :preview-url="item.previewUrl"
          removable
          sweep
          @remove="removeFile(index)"
        />
      </div>
      <!-- 输入区 -->
      <textarea
        ref="textareaRef"
        v-model="text"
        class="input-textarea"
        :style="textareaStyle"
        rows="1"
        placeholder="规划与编程，@ 添加上下文，/ 使用命令"
        :aria-controls="isCommandMenuOpen ? 'slash-command-menu' : undefined"
        :aria-expanded="isCommandMenuOpen"
        aria-haspopup="listbox"
        @input="onTextInput"
        @keydown="onTextareaKeydown"
      />
      <!-- 底部工具行 -->
      <div class="input-toolbar">
        <div class="toolbar-left">
          <!-- 只按悬停触发，避免焦点回来自弹 -->
          <ElTooltip content="添加附件" placement="top" :show-after="300" :disabled="!canHover">
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
                  :aria-label="`模型 ${modelLabel}，推理强度 ${reasoningEffort}`"
                >
                  <span class="model-name">{{ modelLabel }}</span>
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
                  v-if="reasoningOptions.length > 1"
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
                  <div class="effort-track" :class="{ 'is-dragging': dragging }">
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
                    <p v-if="!models.length" class="menu-heading">
                      {{ modelsLoading ? '加载中' : '未配置模型' }}
                    </p>
                    <div v-for="model in models" :key="model.name" class="model-row">
                      <ElTooltip
                        placement="left"
                        effect="light"
                        :fallback-placements="['left', 'right']"
                        :offset="26"
                        :show-after="140"
                        :hide-after="0"
                        :disabled="!canHover"
                        :persistent="false"
                        :popper-style="{
                          padding: '0',
                          width: '184px',
                          border: '1px solid #e5e7eb',
                          borderRadius: '10px',
                          boxShadow: '0 6px 20px rgba(0, 0, 0, 0.1)',
                        }"
                      >
                        <template #content>
                          <ModelInfoTip :model="model" />
                        </template>
                        <button
                          class="menu-option"
                          :class="{ 'is-selected': selectedModelName === model.name }"
                          type="button"
                          role="menuitemradio"
                          :aria-checked="selectedModelName === model.name"
                          @click="chooseModel(model.name)"
                        >
                          <span>{{ model.display_name }}</span>
                          <Check v-if="selectedModelName === model.name" :size="15" />
                        </button>
                      </ElTooltip>
                      <button
                        v-if="!canHover"
                        class="model-info-toggle"
                        type="button"
                        :aria-label="`查看 ${model.display_name} 的配置`"
                        :aria-expanded="infoModelName === model.name"
                        @click="toggleModelInfo(model.name)"
                      >
                        <Info :size="15" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                  <!-- 触屏配置卡 -->
                  <div v-if="!canHover && infoModel" class="model-info-inline">
                    <ModelInfoTip :model="infoModel" />
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
          <button
            ref="sendButtonRef"
            class="send-btn"
            :class="{ 'is-responding': isResponding }"
            type="button"
            :aria-label="sendButtonLabel"
            :disabled="!isResponding && (!text.trim() || streamLimited)"
            @click="onPrimaryAction"
          >
            <Square v-if="isResponding" :size="12" fill="currentColor" :stroke-width="1.5" />
            <ArrowUp v-else :size="15" :stroke-width="2.25" />
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
  Info,
  Plus,
  ShieldCheck,
  Square,
  TriangleAlert,
} from 'lucide-vue-next'
import { ElMessage, ElPopover, ElTooltip } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/popover/style/css'
import 'element-plus/es/components/tooltip/style/css'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { ChatSendRequest } from '@/api/chat'
import { fetchModels, type ModelInfo } from '@/api/config'
import { useDragScroll } from '@/utils/dragScrollUtil'
import {
  describeRejectedUploadFiles,
  describeVisionRejectedFiles,
  isAllowedUploadFile,
  isImageUploadFile,
} from '@/utils/fileUploadUtil'
import AttachmentCard from '@/views/chat/components/attachment/AttachmentCard.vue'
import EnergyField from './EnergyField.vue'
import ModelInfoTip from './ModelInfoTip.vue'
import SlashCommandMenu from './SlashCommandMenu.vue'

const props = withDefaults(
  defineProps<{
    isResponding?: boolean
    streamLimited?: boolean
    // 当前会话已有的对话轮数，换模型时要不要先提示
    historyTurns?: number
  }>(),
  {
    isResponding: false,
    streamLimited: false,
    historyTurns: 0,
  },
)
const emit = defineEmits<{
  send: [message: { content: string; files: File[]; request: ChatSendRequest }]
  stop: []
}>()
const sendButtonLabel = computed(() => {
  if (props.isResponding) return '停止回复'
  return props.streamLimited ? '同时进行的回复已达上限' : '发送消息'
})
// 悬停能力探测
const canHover = window.matchMedia('(hover: hover)').matches
const text = ref('')
const inputRootRef = ref<HTMLElement>()
const commandMenuRef = ref<InstanceType<typeof SlashCommandMenu>>()
const commandMenuDismissed = ref(false)
// 仅输入斜杠命令时显示候选菜单
const commandQuery = computed(() => text.value.match(/^\/([^\s]*)$/)?.[1] ?? null)
const isCommandMenuOpen = computed(() => commandQuery.value !== null && !commandMenuDismissed.value)
type PermissionMode = 'ask' | 'auto' | 'full'
const permissionMode = ref<PermissionMode>('full')
const isAccessMenuOpen = ref(false)
const textareaRef = ref<HTMLTextAreaElement>()
const sendButtonRef = ref<HTMLButtonElement>()
const fileInputRef = ref<HTMLInputElement>()
type SelectedFile = { file: File; previewUrl: string | null }
const selectedFiles = ref<SelectedFile[]>([])
const isFileDragging = ref(false)
const modelButtonRef = ref<HTMLButtonElement>()
const isModelMenuOpen = ref(false)
const showModelOptions = ref(false)
let dragDepth = 0

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

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`
}

function openFilePicker() {
  fileInputRef.value?.click()
}

// 附件去重，图片单独生成预览地址
function addFiles(files: File[]) {
  // 先过类型白名单，不合格的只提示、不进附件条
  const accepted: File[] = []
  const rejected: string[] = []
  let visionRejected = false
  for (const file of files) {
    if (!isAllowedUploadFile(file)) {
      rejected.push(file.name)
      continue
    }
    // 没有视觉能力的模型不收图片，同样只提示、不进附件条
    if (isImageUploadFile(file) && !selectedModel.value?.supports_vision) {
      visionRejected = true
      continue
    }
    accepted.push(file)
  }
  if (rejected.length > 0)
    ElMessage.warning({ message: describeRejectedUploadFiles(rejected), plain: true })
  if (visionRejected)
    ElMessage.warning({ message: describeVisionRejectedFiles(modelLabel.value), plain: true })

  const existing = new Set(selectedFiles.value.map((item) => fileKey(item.file)))
  for (const file of accepted) {
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

// 用进入层级计数避免跨子元素时误判拖拽结束
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

// 附件条只占一排，超出用横向拖动滚动，触屏交给原生滑动
const {
  scrollRef: filesScrollRef,
  isDragging: filesDragging,
  onPointerDown: onFilesPointerDown,
  onPointerMove: onFilesPointerMove,
  onPointerUp: onFilesPointerUp,
  onClickCapture: onFilesClickCapture,
} = useDragScroll()

const EFFORT_OFF = '关闭'
// 支持推理但未配档位时的开关值
const EFFORT_ON = '开启'
// 四档基准动画曲线
const EFFORT_CURVE = [0, 0.24, 0.58, 1]

/** 在等距分段曲线上按 ratio 插值 */
function interpolateCurve(stops: number[], ratio: number): number {
  if (stops.length < 2) return stops[0] ?? 0
  const scaled = Math.max(0, Math.min(1, ratio)) * (stops.length - 1)
  const left = Math.min(stops.length - 2, Math.floor(scaled))
  return stops[left]! + (stops[left + 1]! - stops[left]!) * (scaled - left)
}

const models = ref<ModelInfo[]>([])
const modelsLoading = ref(true)
const selectedModelName = ref('')
const infoModelName = ref('')
const selectedModel = computed(
  () => models.value.find((model) => model.name === selectedModelName.value) ?? null,
)
const modelLabel = computed(() => selectedModel.value?.display_name ?? '未选择模型')
const infoModel = computed(
  () => models.value.find((model) => model.name === infoModelName.value) ?? null,
)
// 关闭固定存在，其余档位跟随所选模型
const reasoningOptions = computed(() => {
  const model = selectedModel.value
  if (!model?.supports_thinking) return [EFFORT_OFF]
  return model.reasoning_levels.length
    ? [EFFORT_OFF, ...model.reasoning_levels]
    : [EFFORT_OFF, EFFORT_ON]
})
const reasoningEffort = ref(EFFORT_OFF)
const effortLastIndex = computed(() => reasoningOptions.value.length - 1)

/** 档位下标换算滑块位置 */
function positionOf(index: number): number {
  return effortLastIndex.value > 0 ? (index / effortLastIndex.value) * 100 : 0
}

const committed = computed(() => positionOf(reasoningOptions.value.indexOf(reasoningEffort.value)))
const effortPreview = ref(committed.value)
const dragging = ref(false)
const settling = ref(false)
const effortRatio = computed(() => effortPreview.value / 100)
const previewIndex = computed(() =>
  Math.min(
    effortLastIndex.value,
    Math.max(0, Math.round(effortRatio.value * effortLastIndex.value)),
  ),
)
const previewEffort = computed(() => reasoningOptions.value[previewIndex.value] ?? EFFORT_OFF)
const effortEnergized = computed(
  () => effortRatio.value > 0 && (dragging.value || settling.value || effortPreview.value >= 99.95),
)
// 按当前档位数重采样曲线
const effortStops = computed(() =>
  Array.from({ length: reasoningOptions.value.length }, (_, index) =>
    interpolateCurve(EFFORT_CURVE, effortLastIndex.value > 0 ? index / effortLastIndex.value : 0),
  ),
)
const effortIntensity = computed(() =>
  effortStops.value.length < 2 ? 0 : interpolateCurve(effortStops.value, effortRatio.value),
)
const visibleEffortIntensity = computed(() =>
  effortRatio.value > 0 ? Math.min(1, effortIntensity.value * 1.4 + 0.15) : 0,
)
let dragTimer = 0
let settleTimer = 0
let draggingNow = false

watch(committed, (value) => {
  if (!draggingNow) effortPreview.value = value
})

// 当前选择对应的对话请求参数
const chatOptions = computed<ChatSendRequest>(() => {
  const effort = reasoningEffort.value
  const levels = selectedModel.value?.reasoning_levels ?? []
  return {
    model_name: selectedModel.value?.model || undefined,
    thinking_enabled: effort !== EFFORT_OFF,
    reasoning_effort: levels.includes(effort) ? effort : undefined,
  }
})

function prepareModelMenu() {
  showModelOptions.value = false
  infoModelName.value = ''
  effortPreview.value = committed.value
}

// 换模型：带历史的会话提示影响，档位不受支持要降档
function chooseModel(name: string) {
  isModelMenuOpen.value = false
  const target = models.value.find((model) => model.name === name)
  if (!target || name === selectedModelName.value) return

  selectedModelName.value = name
  // 空会话没有历史要带，不用提示
  if (props.historyTurns > 0) {
    ElMessage.warning({
      message: `已切到 ${target.display_name}：${props.historyTurns} 轮旧对话会带进新模型，提示词缓存作废`,
      plain: true,
      duration: 5000,
    })
  }
  if (reasoningOptions.value.includes(reasoningEffort.value)) return
  const dropped = reasoningEffort.value
  reasoningEffort.value = EFFORT_OFF
  ElMessage.warning({
    message: `${modelLabel.value} 不支持 ${dropped} 推理强度，已切到${EFFORT_OFF}`,
    plain: true,
  })
}

// 展开或收起配置卡
function toggleModelInfo(name: string) {
  infoModelName.value = infoModelName.value === name ? '' : name
  if (!infoModelName.value) return
  nextTick(() => {
    document.querySelector('.model-info-inline')?.scrollIntoView({ block: 'nearest' })
  })
}

async function closeModelMenu() {
  isModelMenuOpen.value = false
  await nextTick()
  modelButtonRef.value?.focus()
}

// 将滑块位置吸附到推理档位并播放收尾动画
function commitAt(position: number) {
  draggingNow = false
  window.clearTimeout(dragTimer)
  dragging.value = false
  const index = Math.min(
    effortLastIndex.value,
    Math.max(0, Math.round((position / 100) * effortLastIndex.value)),
  )
  const effort = reasoningOptions.value[index] ?? EFFORT_OFF
  effortPreview.value = positionOf(index)
  window.clearTimeout(settleTimer)
  settling.value = true
  settleTimer = window.setTimeout(
    () => {
      settling.value = false
    },
    index === effortLastIndex.value ? 1840 : 620,
  )
  reasoningEffort.value = effort
}

function armDragTimer() {
  window.clearTimeout(dragTimer)
  dragTimer = window.setTimeout(() => {
    commitAt(effortPreview.value)
  }, 450)
}

// 更新预览位置并延时提交
function previewOnly(event: Event) {
  effortPreview.value = Number((event.currentTarget as HTMLInputElement).value)
  armDragTimer()
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

function chooseEffort(effort: string) {
  const index = reasoningOptions.value.indexOf(effort)
  if (index < 0) return
  const position = positionOf(index)
  effortPreview.value = position
  commitAt(position)
}

function onSliderKeyDown(event: KeyboardEvent) {
  let targetIndex: number
  if (['ArrowRight', 'ArrowUp', 'PageUp'].includes(event.key))
    targetIndex = Math.min(effortLastIndex.value, previewIndex.value + 1)
  else if (['ArrowLeft', 'ArrowDown', 'PageDown'].includes(event.key))
    targetIndex = Math.max(0, previewIndex.value - 1)
  else if (event.key === 'Home') targetIndex = 0
  else if (event.key === 'End') targetIndex = effortLastIndex.value
  else return
  event.preventDefault()
  chooseEffort(reasoningOptions.value[targetIndex] ?? EFFORT_OFF)
}

onUnmounted(() => {
  document.removeEventListener('pointerdown', dismissCommandMenuOutside)
  window.clearTimeout(dragTimer)
  window.clearTimeout(settleTimer)
  for (const item of selectedFiles.value) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  }
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
})

onMounted(() => document.addEventListener('pointerdown', dismissCommandMenuOutside))

// 拉取模型列表，第一项作为默认选中
async function loadModels() {
  try {
    models.value = await fetchModels()
    selectedModelName.value = models.value[0]?.name ?? ''
  } catch (error) {
    ElMessage.error({
      message: error instanceof Error ? error.message : '获取模型列表失败',
      plain: true,
    })
  } finally {
    modelsLoading.value = false
  }
}

onMounted(loadModels)

function dismissCommandMenuOutside(event: PointerEvent): void {
  if (inputRootRef.value?.contains(event.target as Node)) return
  commandMenuDismissed.value = true
}

function onTextInput(): void {
  commandMenuDismissed.value = false
  autoResize()
}

function selectCommand(name: string): void {
  text.value = `/${name} `
  commandMenuDismissed.value = true
  void nextTick(() => {
    autoResize()
    const textarea = textareaRef.value
    textarea?.focus()
    textarea?.setSelectionRange(text.value.length, text.value.length)
  })
}

// 从消息操作栏重新编辑已发送的文字
function setDraft(content: string): void {
  text.value = content
  commandMenuDismissed.value = true
  void nextTick(() => {
    autoResize()
    textareaRef.value?.focus()
    textareaRef.value?.setSelectionRange(text.value.length, text.value.length)
  })
}

defineExpose({ setDraft, chatOptions })

/** 输入框随内容增高，超过上限后内部滚动 */
function autoResize() {
  const el = textareaRef.value
  // 手动拖高期间不再跟随内容
  if (!el || manualHeight.value !== null) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`
}

// 手动拖出的高度，null 表示仍随内容自动伸缩
const manualHeight = ref<number | null>(null)
const isResizing = ref(false)
let resizeStartY = 0
let resizeStartHeight = 0

// 触屏不会触发 dblclick，用「300ms 内连续两次点按」来识别双击复位
let lastTapAt = 0
let tapMoved = false
// 本次手势的 pointerId，别的指针（如误触的鼠标）不参与拖动判定
let activePointerId = -1

// 自动高度的最小值，与 .input-textarea 的 min-height 一致
const MIN_INPUT_HEIGHT = 56

// 手动高度上限取视口一半，再高就把会话区顶没了
function maxInputHeight(): number {
  return Math.round(window.innerHeight * 0.5)
}

const textareaStyle = computed(() =>
  manualHeight.value === null
    ? undefined
    : { height: `${manualHeight.value}px`, maxHeight: 'none' },
)

// 双击手柄回到随内容伸缩
function resetInputHeight(): void {
  manualHeight.value = null
  void nextTick(autoResize)
}

function onResizePointerDown(event: PointerEvent): void {
  const el = textareaRef.value
  if (!el) return
  // 触屏没有 dblclick，300ms 内的第二次点按视为双击复位
  if (event.pointerType !== 'mouse' && Date.now() - lastTapAt < 300) {
    lastTapAt = 0
    resetInputHeight()
    event.preventDefault()
    return
  }
  tapMoved = false
  activePointerId = event.pointerId
  const height = Math.round(el.getBoundingClientRect().height)
  manualHeight.value = height
  resizeStartY = event.clientY
  resizeStartHeight = height
  isResizing.value = true
  const handle = event.currentTarget
  if (handle instanceof HTMLElement) handle.setPointerCapture(event.pointerId)
  // 拖动中指针会滑到 textarea 上，锁住整页光标避免跳成文本箭头
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
  event.preventDefault()
}

function onResizePointerMove(event: PointerEvent): void {
  if (!isResizing.value || event.pointerId !== activePointerId) return
  if (Math.abs(event.clientY - resizeStartY) > 8) tapMoved = true
  const delta = resizeStartY - event.clientY
  const next = Math.min(Math.max(resizeStartHeight + delta, MIN_INPUT_HEIGHT), maxInputHeight())
  manualHeight.value = next
}

function onResizePointerUp(event: PointerEvent): void {
  if (!isResizing.value || event.pointerId !== activePointerId) return
  isResizing.value = false
  activePointerId = -1
  // 没拖动过的点按才算一次 tap，供「快速两下」判定
  if (event.pointerType !== 'mouse' && !tapMoved) lastTapAt = Date.now()
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  const target = event.currentTarget
  if (target instanceof HTMLElement && target.hasPointerCapture(event.pointerId)) {
    target.releasePointerCapture(event.pointerId)
  }
}

// 发出原始 File 后清理输入框和预览地址
function sendMessage() {
  if (props.isResponding) return
  if (isCommandMenuOpen.value) {
    commandMenuRef.value?.selectActive()
    return
  }
  const content = text.value.trim()
  const files = selectedFiles.value.map((item) => item.file)
  // 必须有文字才发，只有附件不算一次提问
  if (!content) return
  // 并发满了不发，草稿留着
  if (props.streamLimited) return
  emit('send', { content, files, request: chatOptions.value })
  text.value = ''
  commandMenuDismissed.value = false
  for (const item of selectedFiles.value) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  }
  selectedFiles.value = []
  void nextTick(() => {
    autoResize()
    textareaRef.value?.focus()
  })
}

// 回复期间主按钮用于停止当前回复
function onPrimaryAction(): void {
  if (props.isResponding) emit('stop')
  else sendMessage()
}

function onTextareaKeydown(event: KeyboardEvent): void {
  if (event.isComposing || event.keyCode === 229) return
  if (isCommandMenuOpen.value) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      commandMenuRef.value?.moveSelection(event.key === 'ArrowDown' ? 1 : -1)
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      commandMenuDismissed.value = true
      return
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      commandMenuRef.value?.selectActive()
      return
    }
  }
  if (event.key !== 'Enter' || event.shiftKey) return
  // 触屏回车算换行，发送交给按钮
  if (!canHover) return
  event.preventDefault()
  if (props.isResponding) return
  sendButtonRef.value?.click()
}
</script>

<style scoped>
.chat-input-box {
  position: relative;
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
/* 命中区 112×16，居中压在卡片上边框，上下各露 8px */
.resize-handle {
  position: absolute;
  z-index: 2;
  top: 0;
  left: 50%;
  display: flex;
  width: 112px;
  height: 16px;
  cursor: row-resize;
  touch-action: none;
  transform: translate(-50%, -50%);
}
/* 可见胶囊：平时透明，悬停手柄或输入卡片、聚焦输入框、拖动中淡入 */
.resize-grip {
  box-sizing: border-box;
  width: 96px;
  height: 6px;
  margin: auto;
  border: 1px solid #d6dae1;
  border-radius: 999px;
  background: #fff;
  opacity: 0;
  transition:
    opacity 0.15s,
    border-color 0.15s,
    background-color 0.15s;
}
.input-card:focus-within .resize-grip,
.resize-handle.is-resizing .resize-grip {
  opacity: 1;
}
@media (hover: hover) {
  .input-card:hover .resize-grip,
  .resize-handle:hover .resize-grip {
    opacity: 1;
  }
  .resize-handle:hover .resize-grip {
    border-color: #b9c0ca;
  }
}
/* 触屏没有悬停态，胶囊常驻显示 */
@media (hover: none) {
  .resize-grip {
    opacity: 1;
  }
}
.resize-handle.is-resizing .resize-grip {
  border-color: #8fa8d4;
  background: #eaf0fa;
}
/* 命中区放大到 160×32 */
@media (any-pointer: coarse) {
  .resize-handle {
    width: 160px;
    height: 32px;
  }
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
  flex-wrap: nowrap;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px 6px;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-x: contain;
  scrollbar-width: none;
  cursor: grab;
}

.selected-files::-webkit-scrollbar {
  display: none;
}

.selected-files.is-dragging {
  cursor: grabbing;
  user-select: none;
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
.model-row {
  display: flex;
  align-items: stretch;
}
.model-row .menu-option {
  flex: 1;
  min-width: 0;
}
.model-info-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #8b9098;
  cursor: pointer;
}
.model-info-toggle[aria-expanded='true'] {
  background: #eef1f5;
  color: #303133;
}
.model-info-inline {
  margin: 2px 0 6px;
  border: 1px solid #e9ebef;
  border-radius: 9px;
  overflow: hidden;
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
  /* 松手后滑行到档位，拖动中由 is-dragging 关掉 */
  transition: left 0.24s cubic-bezier(0.22, 1, 0.36, 1);
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
.effort-track.is-dragging .effort-track-thumb {
  transition: none;
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
.send-btn:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
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
  .tool-btn {
    min-height: 36px;
  }
  .menu-option {
    min-height: 42px;
  }
  .model-info-toggle {
    width: 40px;
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
  /* 去掉 300ms 双击缩放延迟和点击灰块 */
  .tool-btn,
  .permission-trigger,
  .send-btn,
  .menu-option,
  .model-info-toggle,
  .effort-label {
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
}
/* iOS 聚焦时字号不足 16px 会整页放大 */
@media (hover: none) {
  .input-textarea {
    font-size: 16px;
  }
}
/* 窄屏放不下整名模型，让模型名先省略 */
@media (max-width: 640px) {
  .chat-input-box {
    padding: 0 10px;
  }
  .input-toolbar {
    padding: 4px 6px 6px;
  }
  .toolbar-left,
  .toolbar-right {
    gap: 2px;
  }
  .tool-model-btn {
    min-width: 0;
    max-width: min(40vw, 200px);
  }
  .permission-trigger {
    padding: 0 6px;
  }
}
.tool-btn:active,
.menu-option:active,
.model-info-toggle:active {
  background: #e9ecf1;
}
.effort-label:active {
  color: #303133;
  font-weight: 600;
}
.send-btn:not(:disabled):active {
  background: #333;
}
</style>
