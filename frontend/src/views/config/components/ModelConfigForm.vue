<!--模型配置表单-->
<template>
  <div v-if="open" class="dialog-backdrop" @click.self="close">
    <section
      ref="dialogElement"
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="model-form-title"
    >
      <header class="dialog-header">
        <div>
          <h2 id="model-form-title">{{ model ? '编辑模型' : '添加模型' }}</h2>
          <p>填写模型信息和连接参数。</p>
        </div>
        <button
          class="close-button"
          type="button"
          aria-label="关闭"
          :disabled="saving"
          @click="close"
        >
          <X :size="18" />
        </button>
      </header>

      <form class="dialog-form" @submit.prevent="submitForm">
        <div class="dialog-body">
          <section class="form-section">
            <h3>基本信息</h3>
            <div class="field-grid">
              <label class="field">
                <span>接口模型名 <em>*</em></span>
                <input
                  ref="nameInput"
                  v-model.trim="form.modelName"
                  :disabled="Boolean(model) || saving"
                  placeholder="例如 deepseek-chat"
                />
                <small>传给模型服务的实际名称，添加后不可修改。</small>
              </label>
              <label class="field">
                <span>显示名称 <em>*</em></span>
                <input
                  v-model.trim="form.displayName"
                  :disabled="saving"
                  placeholder="例如 DeepSeek Chat"
                />
              </label>
              <label class="field">
                <span>模型厂商 <em>*</em></span>
                <input
                  v-model.trim="form.provider"
                  :disabled="saving"
                  placeholder="例如 deepseek"
                />
              </label>
              <label class="field">
                <span>模型实现 <em>*</em></span>
                <input
                  v-model.trim="form.implementation"
                  :disabled="saving"
                  placeholder="模块路径:类名"
                />
              </label>
            </div>
            <label class="field description-field">
              <span>模型描述</span>
              <textarea
                v-model.trim="form.description"
                :disabled="saving"
                rows="2"
                placeholder="这个模型适合做什么"
              />
            </label>
          </section>

          <section class="form-section">
            <h3>连接设置</h3>
            <div class="field-grid">
              <label class="field">
                <span>服务地址</span>
                <input
                  v-model.trim="form.baseUrl"
                  :disabled="saving"
                  type="url"
                  :placeholder="
                    model?.base_url_configured ? '已配置，留空保持' : 'https://api.example.com/v1'
                  "
                />
                <small v-if="model?.base_url_configured">原地址不会回显，留空保持已有配置。</small>
              </label>
              <label class="field">
                <span>密钥环境变量</span>
                <input
                  v-model.trim="form.apiKey"
                  :disabled="saving"
                  :placeholder="model?.api_key_configured ? '已配置，留空保持' : '$MODEL_API_KEY'"
                  autocomplete="off"
                />
                <small>只填 $ENV_NAME 或 ${ENV_NAME}，页面不会回显已有值。</small>
              </label>
            </div>
            <div class="field-grid numeric-grid">
              <label class="field">
                <span>请求超时（秒）</span>
                <input
                  v-model="form.timeout"
                  :disabled="saving"
                  type="number"
                  min="0.1"
                  step="0.1"
                  inputmode="decimal"
                />
              </label>
              <label class="field">
                <span>最大重试次数</span>
                <input
                  v-model="form.maxRetries"
                  :disabled="saving"
                  type="number"
                  min="0"
                  step="1"
                  inputmode="numeric"
                />
              </label>
            </div>
          </section>

          <section class="form-section">
            <h3>模型能力</h3>
            <div class="check-grid">
              <label class="check-row">
                <input v-model="form.supportsThinking" :disabled="saving" type="checkbox" />
                <span><strong>支持推理</strong><small>对话中可以选择推理强度</small></span>
              </label>
              <label class="check-row">
                <input v-model="form.supportsVision" :disabled="saving" type="checkbox" />
                <span><strong>支持视觉</strong><small>允许在对话中上传图片</small></span>
              </label>
            </div>
            <label v-if="form.supportsThinking" class="field thinking-levels">
              <span>推理强度</span>
              <input
                v-model="form.reasoningLevels"
                :disabled="saving"
                placeholder="low, high, max"
              />
              <small>用英文逗号分隔，顺序将用于对话中的选项。</small>
            </label>
            <div class="field-grid numeric-grid">
              <label class="field">
                <span>上下文长度</span>
                <input
                  v-model="form.contextWindow"
                  :disabled="saving"
                  type="number"
                  min="1"
                  step="1"
                  inputmode="numeric"
                  placeholder="可选"
                />
              </label>
              <label class="field">
                <span>最大输出令牌数</span>
                <input
                  v-model="form.maxTokens"
                  :disabled="saving"
                  type="number"
                  min="1"
                  step="1"
                  inputmode="numeric"
                  placeholder="可选"
                />
              </label>
            </div>
          </section>

          <section class="form-section last-section">
            <details class="advanced-details">
              <summary>高级推理参数 <ChevronDown :size="15" /></summary>
              <p>部分模型需要额外参数来开启或关闭推理。填写 JSON 对象即可。</p>
              <div class="field-grid">
                <label class="field">
                  <span>开启推理时</span>
                  <textarea
                    v-model.trim="form.thinkingEnabledJson"
                    :disabled="saving || !form.supportsThinking"
                    rows="4"
                    spellcheck="false"
                    placeholder='{"enable_thinking": true}'
                  />
                </label>
                <label class="field">
                  <span>关闭推理时</span>
                  <textarea
                    v-model.trim="form.thinkingDisabledJson"
                    :disabled="saving || !form.supportsThinking"
                    rows="4"
                    spellcheck="false"
                    placeholder='{"enable_thinking": false}'
                  />
                </label>
              </div>
            </details>
          </section>
        </div>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <footer class="dialog-footer">
          <button class="secondary-button" type="button" :disabled="saving" @click="close">
            取消
          </button>
          <button class="primary-button" type="submit" :disabled="saving">
            {{ saving ? '保存中…' : '保存配置' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { ChevronDown, X } from 'lucide-vue-next'
import type { ModelConfigInput, ModelConfigItem } from '@/api/modelConfig'

const props = defineProps<{ open: boolean; model: ModelConfigItem | null; saving: boolean }>()
const emit = defineEmits<{ close: []; submit: [input: ModelConfigInput] }>()
const dialogElement = ref<HTMLElement | null>(null)
const nameInput = ref<HTMLInputElement | null>(null)
const error = ref('')
let previousFocus: HTMLElement | null = null

const form = reactive({
  modelName: '',
  displayName: '',
  description: '',
  provider: '',
  implementation: '',
  baseUrl: '',
  apiKey: '',
  timeout: '60',
  maxRetries: '2',
  maxTokens: '',
  contextWindow: '',
  supportsThinking: false,
  supportsVision: false,
  reasoningLevels: '',
  thinkingEnabledJson: '',
  thinkingDisabledJson: '',
})

// 模型表单初始化
watch(
  () => [props.open, props.model] as const,
  ([open, model]) => {
    if (!open) return
    form.modelName = model?.model_name ?? ''
    form.displayName = model?.display_name ?? ''
    form.description = model?.description ?? ''
    form.provider = model?.provider ?? ''
    form.implementation = model?.use ?? ''
    form.baseUrl = ''
    form.apiKey = ''
    form.timeout = String(model?.timeout ?? 60)
    form.maxRetries = String(model?.max_retries ?? 2)
    form.maxTokens = model?.max_tokens == null ? '' : String(model.max_tokens)
    form.contextWindow = model?.context_window == null ? '' : String(model.context_window)
    form.supportsThinking = model?.supports_thinking ?? false
    form.supportsVision = model?.supports_vision ?? false
    form.reasoningLevels = model?.reasoning_levels.join(', ') ?? ''
    form.thinkingEnabledJson = model?.when_thinking_enabled
      ? JSON.stringify(model.when_thinking_enabled, null, 2)
      : ''
    form.thinkingDisabledJson = model?.when_thinking_disabled
      ? JSON.stringify(model.when_thinking_disabled, null, 2)
      : ''
    error.value = ''
    void nextTick(() => {
      if (window.matchMedia('(any-pointer: coarse), (max-width: 560px)').matches) {
        dialogElement.value?.querySelector<HTMLElement>('button:not(:disabled)')?.focus()
      } else {
        const firstInput = dialogElement.value?.querySelector<HTMLElement>('input:not(:disabled)')
        const target = firstInput ?? nameInput.value
        target?.focus()
      }
    })
  },
)

// 弹窗焦点管理
watch(
  () => props.open,
  (open, _old, onCleanup) => {
    if (!open) {
      previousFocus?.focus()
      previousFocus = null
      return
    }
    previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
      if (event.key !== 'Tab') return
      const controls = dialogElement.value?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), summary',
      )
      if (!controls?.length) return
      const first = controls[0]!
      const last = controls[controls.length - 1]!
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKeydown)
    onCleanup(() => window.removeEventListener('keydown', onKeydown))
  },
)

function close(): void {
  if (!props.saving) emit('close')
}

// 正整数参数解析
function optionalPositive(value: string, label: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed) || parsed <= 0) throw new Error(`${label}必须是正整数`)
  return parsed
}

// JSON 参数校验
function jsonObject(value: string, label: string): Record<string, unknown> | null {
  if (!value.trim()) return null
  try {
    const parsed: unknown = JSON.parse(value)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
  } catch {
    // 字段错误统一提示
  }
  throw new Error(`${label}必须是 JSON 对象`)
}

// 模型配置校验与提交
function submitForm(): void {
  error.value = ''
  try {
    if (!form.modelName || !form.displayName || !form.provider || !form.implementation) {
      throw new Error('请填写接口模型名、显示名称、模型厂商和模型实现')
    }
    if (
      form.apiKey &&
      !/^\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})$/.test(form.apiKey)
    ) {
      throw new Error('密钥请填写 $ENV_NAME 或 ${ENV_NAME}')
    }
    const timeout = Number(form.timeout)
    const maxRetries = Number(form.maxRetries)
    if (!Number.isFinite(timeout) || timeout <= 0) throw new Error('请求超时必须大于 0')
    if (!Number.isSafeInteger(maxRetries) || maxRetries < 0) {
      throw new Error('最大重试次数必须是非负整数')
    }
    const reasoningLevels = form.supportsThinking
      ? form.reasoningLevels
          .split(',')
          .map((level) => level.trim())
          .filter(Boolean)
      : []
    if (new Set(reasoningLevels).size !== reasoningLevels.length)
      throw new Error('推理强度不能重复')
    emit('submit', {
      model_name: form.modelName,
      display_name: form.displayName,
      description: form.description || null,
      provider: form.provider,
      use: form.implementation,
      base_url: form.baseUrl || null,
      api_key: form.apiKey || undefined,
      timeout,
      max_retries: maxRetries,
      max_tokens: optionalPositive(form.maxTokens, '最大输出令牌数'),
      context_window: optionalPositive(form.contextWindow, '上下文长度'),
      supports_thinking: form.supportsThinking,
      reasoning_levels: reasoningLevels,
      when_thinking_enabled: form.supportsThinking
        ? jsonObject(form.thinkingEnabledJson, '开启推理时参数')
        : null,
      when_thinking_disabled: form.supportsThinking
        ? jsonObject(form.thinkingDisabledJson, '关闭推理时参数')
        : null,
      supports_vision: form.supportsVision,
    })
  } catch (cause: unknown) {
    error.value = cause instanceof Error ? cause.message : '请检查模型配置'
  }
}
</script>

<style scoped>
.dialog-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.42);
}
.dialog {
  display: flex;
  flex-direction: column;
  width: min(720px, 100%);
  max-height: min(820px, calc(100dvh - 40px));
  overflow: hidden;
  border: 1px solid #d8d8d8;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.16);
}
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  flex: 0 0 auto;
  border-bottom: 1px solid #e7e7e7;
  padding: 22px 28px 20px;
  background: #fafafa;
}
.dialog-header h2 {
  color: #171717;
  font-size: 19px;
  font-weight: 680;
}
.dialog-header p {
  margin-top: 7px;
  color: #777;
  font-size: 12px;
}
.close-button {
  display: grid;
  flex: 0 0 32px;
  height: 32px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #666;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.dialog-form {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.dialog-body {
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
  padding: 0 28px;
}
.dialog-body::-webkit-scrollbar {
  display: none;
}
.form-section {
  border-bottom: 1px solid #e9e9e9;
  padding: 23px 0 26px;
}
.form-section.last-section {
  border-bottom: 0;
}
.form-section h3 {
  margin-bottom: 18px;
  color: #222;
  font-size: 13px;
  font-weight: 680;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.description-field,
.numeric-grid,
.thinking-levels {
  margin-top: 17px;
}
.field {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
  color: #3e3e3e;
  font-size: 12px;
  font-weight: 600;
}
.field em {
  color: #555;
  font-style: normal;
}
.field input,
.field textarea {
  width: 100%;
  min-width: 0;
  min-height: 39px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 8px 10px;
  background: #fff;
  color: #222;
  font-size: 12px;
  font-weight: 450;
  outline: none;
}
.field textarea {
  min-height: 70px;
  resize: vertical;
}
.field input::placeholder,
.field textarea::placeholder {
  color: #aaa;
}
.field input:focus,
.field textarea:focus {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.field input:disabled,
.field textarea:disabled {
  background: #f5f5f5;
  color: #888;
}
.field small {
  color: #818181;
  font-size: 11px;
  font-weight: 450;
  line-height: 1.5;
}
.check-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  border: 1px solid #e2e2e2;
  border-radius: 7px;
  padding: 12px;
  cursor: pointer;
}
.check-row input {
  flex: 0 0 auto;
  margin-top: 2px;
  accent-color: #668a70;
}
.check-row span {
  display: grid;
  gap: 4px;
}
.check-row strong {
  color: #333;
  font-size: 12px;
  font-weight: 600;
}
.check-row small {
  color: #898989;
  font-size: 11px;
}
.advanced-details summary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #333;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  list-style: none;
  touch-action: manipulation;
}
.advanced-details summary::-webkit-details-marker {
  display: none;
}
.advanced-details summary svg {
  transition: transform 0.18s ease;
}
.advanced-details[open] summary svg {
  transform: rotate(180deg);
}
.advanced-details > p {
  margin: 15px 0 16px;
  color: #888;
  font-size: 11px;
}
.advanced-details textarea {
  font-family: Consolas, 'SFMono-Regular', monospace;
  line-height: 1.45;
}
.form-error {
  flex: 0 0 auto;
  margin: 0 28px 12px;
  border: 1px solid #e3c9c3;
  padding: 10px 12px;
  background: #fbf4f1;
  color: #89594e;
  font-size: 12px;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 0 auto;
  border-top: 1px solid #e7e7e7;
  padding: 15px 28px;
  background: #fff;
}
.secondary-button,
.primary-button {
  min-width: 86px;
  min-height: 36px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 14px;
  background: #fff;
  color: #333;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.primary-button {
  border-color: #171717;
  background: #171717;
  color: #fff;
}
.secondary-button:disabled,
.primary-button:disabled {
  cursor: wait;
  opacity: 0.55;
}
@media (hover: hover) {
  .close-button:hover {
    background: #f4f4f4;
  }
  .secondary-button:hover {
    border-color: #777;
  }
  .primary-button:hover {
    background: #333;
  }
}
.close-button:focus-visible,
.secondary-button:focus-visible,
.primary-button:focus-visible,
.advanced-details summary:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .dialog-backdrop {
    padding: 8px;
  }
  .dialog {
    max-height: calc(100dvh - 16px);
  }
  .dialog-header {
    padding: 19px 18px;
  }
  .dialog-header h2 {
    font-size: 17px;
  }
  .dialog-body {
    padding: 0 18px;
    -webkit-overflow-scrolling: touch;
  }
  .field-grid,
  .check-grid {
    grid-template-columns: 1fr;
  }
  .form-error {
    margin-right: 18px;
    margin-left: 18px;
  }
  .dialog-footer {
    padding: 13px 18px;
  }
  .dialog-footer button {
    flex: 1;
  }
}
@media (max-width: 600px), (any-pointer: coarse) {
  .field input,
  .field textarea {
    min-height: 44px;
    font-size: 16px;
  }
}
@media (any-pointer: coarse) {
  .close-button {
    min-width: 44px;
    min-height: 44px;
  }
  .check-row {
    min-height: 44px;
  }
  .advanced-details summary,
  .secondary-button,
  .primary-button {
    min-height: 44px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .advanced-details summary svg {
    transition: none;
  }
}
</style>
