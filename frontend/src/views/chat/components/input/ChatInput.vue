<template>
  <div class="chat-input-box">
    <div class="input-card">
      <!-- 输入区 -->
      <textarea
        ref="textareaRef"
        v-model="text"
        class="input-textarea"
        rows="1"
        placeholder="规划与编程，@ 添加上下文，/ 使用命令"
        @input="autoResize"
      />
      <!-- 底部工具行 -->
      <div class="input-toolbar">
        <div class="toolbar-left">
          <button class="tool-btn tool-icon-btn" type="button">
            <Plus :size="15" :stroke-width="2.5" />
          </button>
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
          <button class="send-btn" type="button" :disabled="!text.trim()">
            <ArrowUp :size="15" :stroke-width="2.25" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowUp, Check, ChevronDown, ChevronRight, Plus } from 'lucide-vue-next'
import { ElPopover } from 'element-plus'
import 'element-plus/es/components/popover/style/css'
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import EnergyField from './EnergyField.vue'

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const modelButtonRef = ref<HTMLButtonElement>()
const isModelMenuOpen = ref(false)
const showModelOptions = ref(false)

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
})

/** 输入框随内容增高，超过上限后内部滚动 */
function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`
}
</script>

<style scoped>
.chat-input-box {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 16px;
}
.input-card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.input-card:focus-within {
  border-color: #c7ccd4;
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.08);
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
.effort-label:active {
  color: #303133;
  font-weight: 600;
}
.send-btn:not(:disabled):active {
  background: #333;
}
</style>
