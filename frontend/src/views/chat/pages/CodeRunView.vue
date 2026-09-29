<template>
  <div class="code-run-view">
    <!-- 代码编辑区 -->
    <section class="run-editor">
      <CodeEditor v-model="source" :language="language" @run="handleRun" />
    </section>
    <!-- 运行操作区 -->
    <section class="run-bar">
      <div class="bar-meta">
        <span class="bar-lang">{{ language }}</span>
        <span class="bar-status">{{ status }}</span>
      </div>
      <div class="bar-actions">
        <span class="bar-hint" aria-hidden="true">Ctrl+Enter</span>
        <button
          class="bar-run"
          type="button"
          :disabled="running"
          title="运行，快捷键 Ctrl+Enter"
          @click="handleRun"
        >
          <Loader2
            v-if="running"
            class="is-spinning"
            :size="12"
            :stroke-width="2"
            aria-hidden="true"
          />
          <Play v-else :size="11" :stroke-width="0" fill="currentColor" aria-hidden="true" />
          <span>{{ running ? '运行中' : '运行' }}</span>
        </button>
      </div>
    </section>
    <!-- 样例输入与运行结果区 -->
    <section class="run-panel">
      <div class="panel-tabs" role="tablist" aria-label="样例与结果">
        <button
          class="panel-tab"
          :class="{ 'is-active': panel === 'input' }"
          type="button"
          role="tab"
          aria-controls="run-panel-body"
          :aria-selected="panel === 'input'"
          @click="panel = 'input'"
        >
          测试样例
        </button>
        <button
          class="panel-tab"
          :class="{ 'is-active': panel === 'output' }"
          type="button"
          role="tab"
          aria-controls="run-panel-body"
          :aria-selected="panel === 'output'"
          @click="panel = 'output'"
        >
          运行结果
        </button>
      </div>
      <div id="run-panel-body" class="panel-field">
        <textarea
          v-if="panel === 'input'"
          v-model="sample"
          class="field-text"
          placeholder="运行时喂给程序的标准输入，一行一个样例"
          spellcheck="false"
        />
        <template v-else>
          <pre v-if="output" class="field-text is-console" aria-live="polite">{{ output }}</pre>
          <p v-else class="field-empty">
            <Loader2
              v-if="running"
              class="is-spinning"
              :size="14"
              :stroke-width="1.8"
              aria-hidden="true"
            />
            <SquareTerminal v-else :size="14" :stroke-width="1.7" aria-hidden="true" />
            <span>{{ running ? '运行中…' : '运行后在此显示输出' }}</span>
          </p>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Loader2, Play, SquareTerminal } from 'lucide-vue-next'
import { onBeforeUnmount, ref, watch } from 'vue'
import CodeEditor from '@/components/CodeEditor.vue'

const props = withDefaults(
  defineProps<{
    /** 待运行的代码 */
    code?: string
    /** 语言标识，决定高亮与缩进 */
    language?: string
  }>(),
  { code: '', language: 'python' },
)

// 编辑区内容，允许在运行前就地改代码
const source = ref(props.code)
// 用户自填的标准输入
const sample = ref('')
const output = ref('')
const status = ref('未运行')
const panel = ref<'input' | 'output'>('input')
const running = ref(false)
let runTimer = 0

// 抽屉换代码块时复用同一实例，按外部灌入重建编辑区
watch(
  () => props.code,
  (value) => {
    window.clearTimeout(runTimer)
    running.value = false
    source.value = value
    output.value = ''
    status.value = '未运行'
    panel.value = 'input'
  },
)

onBeforeUnmount(() => window.clearTimeout(runTimer))

// 演示输出，执行接口接入后换成真实 stdout
function mockOutput(): string {
  const cases = sample.value
    .split('\n')
    .filter((line) => line.trim() !== '')
    .map((line, index) => `  ${index + 1}. ${line} -> ${line.trim().length}`)
  const lines = source.value.split('\n').length
  return [
    `$ ${props.language} main.py`,
    `提交 ${lines} 行 / ${source.value.length} 字符`,
    cases.length ? '样例：' : '样例：（输入为空）',
    ...(cases.length ? cases : []),
    '',
    'exit code 0',
  ].join('\n')
}

// 运行：切到结果页走一遍加载态，结果暂由本地演示数据给出
function handleRun(): void {
  window.clearTimeout(runTimer)
  panel.value = 'output'
  output.value = ''
  running.value = true
  status.value = '运行中…'
  const started = performance.now()
  runTimer = window.setTimeout(() => {
    running.value = false
    output.value = mockOutput()
    status.value = `退出码 0 · ${Math.round(performance.now() - started)} ms`
  }, 900)
}
</script>

<style scoped>
.code-run-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}
.run-editor {
  flex: 1;
  min-height: 120px;
  overflow: hidden;
}
/* 运行操作条 */
.run-bar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-top: 1px solid #e6e8eb;
  border-bottom: 1px solid #eef1f4;
}
.bar-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.bar-lang {
  flex-shrink: 0;
  padding: 1px 6px;
  border: 1px solid #e3e7ec;
  border-radius: 4px;
  background: #f2f4f7;
  color: #5d646c;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, 'Liberation Mono', monospace;
  font-size: 11px;
  line-height: 16px;
}
.bar-status {
  min-width: 0;
  overflow: hidden;
  color: #8a9097;
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 9px;
}
.bar-hint {
  flex-shrink: 0;
  color: #a5abb1;
  font-size: 11px;
  line-height: 16px;
}
.bar-run {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px 5px 10px;
  border: 1px solid #3369aa;
  border-radius: 6px;
  background: #3369aa;
  box-shadow: 0 1px 2px rgba(24, 44, 70, 0.16);
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.2px;
  line-height: 16px;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}
@media (hover: hover) {
  .bar-run:hover {
    border-color: #2c5f9b;
    background: #2c5f9b;
    box-shadow: 0 2px 5px rgba(24, 44, 70, 0.2);
  }
}
.bar-run:active {
  transform: translateY(1px);
  box-shadow: none;
}
.bar-run:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 2px;
}
.bar-run:disabled {
  border-color: #7f9dc0;
  background: #7f9dc0;
  box-shadow: none;
  cursor: default;
}
/* 运行中的转圈 */
.is-spinning {
  animation: field-spin 0.9s linear infinite;
}
@keyframes field-spin {
  to {
    transform: rotate(360deg);
  }
}
/* 样例输入与运行结果区 */
.run-panel {
  display: flex;
  flex: 0 0 34%;
  flex-direction: column;
  min-height: 148px;
  padding: 0 12px 12px;
  overflow: hidden;
  background: #fdfdfe;
}
.panel-tabs {
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  padding: 2px 0 0 2px;
}
.panel-tab {
  padding: 7px 0 6px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: #7d858d;
  cursor: pointer;
  font-size: 12px;
  line-height: 16px;
  transition:
    border-color 0.15s ease,
    color 0.15s ease;
}
.panel-tab.is-active {
  border-bottom-color: #3369aa;
  color: #202327;
  font-weight: 600;
}
@media (hover: hover) {
  .panel-tab:hover {
    color: #202327;
  }
}
.panel-tab:focus-visible {
  outline: 2px solid #8b9fc7;
  outline-offset: 1px;
}
/* 输入与输出的共用外框 */
.panel-field {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e6e8eb;
  background: #fff;
  transition: border-color 0.15s ease;
}
.panel-field:focus-within {
  border-color: #a9bcd9;
}
.field-text {
  flex: 1;
  min-height: 0;
  padding: 9px 11px;
  border: 0;
  background: none;
  color: #292d32;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, 'Liberation Mono', monospace;
  font-size: 12.5px;
  line-height: 1.65;
  outline: none;
  resize: none;
  scrollbar-color: #d6dbe1 transparent;
  scrollbar-width: thin;
  white-space: pre-wrap;
}
.field-text.is-console {
  background: #f7f8fa;
  overflow: auto;
}
.field-text::placeholder {
  color: #a5abb1;
}
.field-empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 0;
  color: #a5abb1;
  font-size: 12px;
  line-height: 18px;
}
@media (prefers-reduced-motion: reduce) {
  .bar-run,
  .panel-tab,
  .panel-field {
    transition: none;
  }
  .bar-run:active {
    transform: none;
  }
  .is-spinning {
    animation: none;
  }
}
</style>
