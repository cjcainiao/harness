<!--MCP 服务器配置表单-->
<template>
  <div v-if="open" class="dialog-backdrop" @mousedown.self="close">
    <section
      ref="dialogElement"
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mcp-form-title"
    >
      <header class="dialog-header">
        <div>
          <h2 id="mcp-form-title">{{ server ? '编辑 MCP 服务' : '新增 MCP 服务' }}</h2>
          <p>填写连接信息，保存后在下一轮对话中生效。</p>
        </div>
        <button
          class="close-button"
          type="button"
          :disabled="saving"
          aria-label="关闭"
          @click="close"
        >
          <X :size="18" />
        </button>
      </header>

      <form class="dialog-form" @submit.prevent="submitForm">
        <div class="dialog-body">
          <section class="form-section">
            <div class="section-heading">
              <h3>基本信息</h3>
            </div>
            <div class="field-grid">
              <label class="field">
                <span>服务器名称</span>
                <input
                  ref="nameInput"
                  v-model.trim="form.name"
                  :disabled="Boolean(server) || saving"
                  placeholder="例如 enhancedSearch"
                />
              </label>
              <div class="field">
                <span>连接方式</span>
                <ElSelect
                  v-model="form.transport"
                  class="transport-select"
                  aria-label="连接方式"
                  popper-class="mcp-transport-popper"
                  :disabled="saving"
                >
                  <ElOption label="远程 HTTP" value="streamable_http" />
                  <ElOption label="本地 stdio" value="stdio" />
                </ElSelect>
              </div>
            </div>
            <label class="field description-field">
              <span>服务描述</span>
              <textarea
                v-model.trim="form.description"
                :disabled="saving"
                rows="2"
                maxlength="500"
                placeholder="简要说明这台服务能做什么"
              />
            </label>
          </section>

          <section class="form-section">
            <div class="section-heading">
              <h3>连接信息</h3>
            </div>
            <div class="section-content">
              <template v-if="form.transport === 'streamable_http'">
                <label class="field">
                  <span>服务器地址</span>
                  <input
                    v-model.trim="form.url"
                    :disabled="saving"
                    :placeholder="
                      server?.has_hidden_url
                        ? '地址含隐藏参数，留空则保留'
                        : 'https://example.com/mcp'
                    "
                    @input="urlDirty = true"
                  />
                  <small v-if="server?.has_hidden_url"
                    >当前地址：{{ server.url ?? '已隐藏' }}。输入新地址才会替换原值。</small
                  >
                </label>
                <div class="field">
                  <span>请求头</span>
                  <p class="field-hint">
                    例如 Authorization → Bearer ${DASHSCOPE_API_KEY}；已有值不会显示，留空即保留。
                  </p>
                  <div v-for="row in visibleHeaderRows" :key="row.id" class="pair-row">
                    <input
                      v-model.trim="row.name"
                      :disabled="saving"
                      aria-label="请求头名称"
                      placeholder="请求头名称"
                    />
                    <input
                      v-model.trim="row.value"
                      :disabled="saving"
                      aria-label="请求头值"
                      :placeholder="row.existingName ? '留空保留原值' : '请求头值'"
                      autocomplete="off"
                    />
                    <button
                      type="button"
                      class="pair-remove"
                      :disabled="saving"
                      aria-label="移除请求头"
                      @click="removeRow(headerRows, row)"
                    >
                      <X :size="15" />
                    </button>
                  </div>
                  <button
                    type="button"
                    class="text-button"
                    :disabled="saving"
                    @click="addRow(headerRows)"
                  >
                    + 添加请求头
                  </button>
                </div>
              </template>

              <template v-else>
                <label class="field">
                  <span>启动命令</span>
                  <input
                    v-model.trim="form.command"
                    :disabled="saving"
                    :placeholder="server?.command_configured ? '已配置，留空保留' : '例如 uvx'"
                    autocomplete="off"
                  />
                </label>
                <label
                  v-if="server?.command_configured && server.transport === 'stdio'"
                  class="small-check"
                >
                  <input v-model="form.clearCommand" type="checkbox" :disabled="saving" />
                  清除原启动命令
                </label>
                <label class="field">
                  <span>启动参数</span>
                  <textarea
                    v-model="form.argsText"
                    :disabled="saving || (Boolean(server) && !form.replaceArgs)"
                    rows="3"
                    placeholder="每行一个参数"
                  />
                  <small v-if="server"
                    >当前有 {{ server.args_count }} 个参数。勾选后才会替换。</small
                  >
                </label>
                <label v-if="server" class="small-check">
                  <input v-model="form.replaceArgs" type="checkbox" :disabled="saving" />
                  替换启动参数
                </label>
                <label class="field">
                  <span>工作目录</span>
                  <input
                    v-model.trim="form.cwd"
                    :disabled="saving"
                    :placeholder="server?.cwd_configured ? '已配置，留空保留' : '可选'"
                  />
                </label>
                <label
                  v-if="server?.cwd_configured && server.transport === 'stdio'"
                  class="small-check"
                >
                  <input v-model="form.clearCwd" type="checkbox" :disabled="saving" />
                  清除原工作目录
                </label>
                <div class="field">
                  <span>环境变量</span>
                  <p class="field-hint">密钥请使用 ${ENV_NAME}，已有值留空即保留。</p>
                  <div v-for="row in visibleEnvRows" :key="row.id" class="pair-row">
                    <input
                      v-model.trim="row.name"
                      :disabled="saving"
                      aria-label="环境变量名称"
                      placeholder="变量名称"
                    />
                    <input
                      v-model.trim="row.value"
                      :disabled="saving"
                      aria-label="环境变量值"
                      :placeholder="row.existingName ? '留空保留原值' : '变量值'"
                      autocomplete="off"
                    />
                    <button
                      type="button"
                      class="pair-remove"
                      :disabled="saving"
                      aria-label="移除环境变量"
                      @click="removeRow(envRows, row)"
                    >
                      <X :size="15" />
                    </button>
                  </div>
                  <button
                    type="button"
                    class="text-button"
                    :disabled="saving"
                    @click="addRow(envRows)"
                  >
                    + 添加环境变量
                  </button>
                </div>
              </template>
            </div>
          </section>

          <section class="form-section last-section">
            <div class="section-heading">
              <h3>运行设置</h3>
            </div>

            <div class="field-grid">
              <label class="field">
                <span>连接超时（秒）</span>
                <input
                  v-model.number="form.connectTimeout"
                  type="number"
                  min="0.1"
                  step="0.1"
                  :disabled="saving"
                />
              </label>
              <label class="field">
                <span>工具调用超时（秒）</span>
                <input
                  v-model.number="form.callTimeout"
                  type="number"
                  min="0.1"
                  step="0.1"
                  :disabled="saving"
                />
              </label>
            </div>
            <label class="small-check enable-check">
              <input v-model="form.enabled" type="checkbox" :disabled="saving" /> 保存后启用服务器
            </label>
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
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ElOption, ElSelect } from 'element-plus'
import { X } from 'lucide-vue-next'
import type { McpServerConfig, McpServerCreate, McpServerPatch, McpTransport } from '@/api/mcp'

interface PairRow {
  id: number
  name: string
  value: string
  existingName: string | null
  removed: boolean
}

const props = defineProps<{ open: boolean; server: McpServerConfig | null; saving: boolean }>()
const emit = defineEmits<{ close: []; submit: [payload: McpServerCreate | McpServerPatch] }>()
const nameInput = ref<HTMLInputElement | null>(null)
const dialogElement = ref<HTMLElement | null>(null)
const error = ref('')
const urlDirty = ref(false)
const headerRows = ref<PairRow[]>([])
const envRows = ref<PairRow[]>([])
let rowId = 0
let previousFocus: HTMLElement | null = null

const form = reactive({
  name: '',
  description: '',
  enabled: false,
  transport: 'streamable_http' as McpTransport,
  url: '',
  command: '',
  argsText: '',
  cwd: '',
  connectTimeout: 10,
  callTimeout: 60,
  replaceArgs: false,
  clearCommand: false,
  clearCwd: false,
})

const visibleHeaderRows = computed(() => headerRows.value.filter((row) => !row.removed))
const visibleEnvRows = computed(() => envRows.value.filter((row) => !row.removed))

function makeRow(name = '', existingName: string | null = null): PairRow {
  return { id: ++rowId, name, value: '', existingName, removed: false }
}

// MCP 表单初始化
watch(
  () => [props.open, props.server] as const,
  ([open, server]) => {
    if (!open) return
    form.name = server?.name ?? ''
    form.description = server?.description ?? ''
    form.enabled = server?.enabled ?? false
    form.transport = server?.transport ?? 'streamable_http'
    form.url = server?.has_hidden_url ? '' : (server?.url ?? '')
    form.command = ''
    form.argsText = ''
    form.cwd = ''
    form.connectTimeout = server?.connect_timeout_seconds ?? 10
    form.callTimeout = server?.call_timeout_seconds ?? 60
    form.replaceArgs = false
    form.clearCommand = false
    form.clearCwd = false
    // 已有敏感字段脱敏
    headerRows.value = (server?.header_names ?? []).map((name) => makeRow(name, name))
    envRows.value = (server?.env_names ?? []).map((name) => makeRow(name, name))
    urlDirty.value = false
    error.value = ''
    void nextTick(() => {
      if (window.matchMedia('(pointer: coarse)').matches) {
        dialogElement.value?.querySelector<HTMLElement>('button:not(:disabled)')?.focus()
        return
      }
      const firstInput = dialogElement.value?.querySelector<HTMLElement>('input:not(:disabled)')
      const target = firstInput ?? nameInput.value
      target?.focus()
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
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)',
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

function addRow(rows: PairRow[]): void {
  rows.push(makeRow())
}

// 已有字段删除标记
function removeRow(rows: PairRow[], row: PairRow): void {
  if (row.existingName) row.removed = true
  else rows.splice(rows.indexOf(row), 1)
}

// 请求头与环境变量变更
function pairsToChanges(rows: PairRow[], label: string): Record<string, string | null> {
  const changes: Record<string, string | null> = {}
  const names = new Set<string>()
  for (const row of rows) {
    // 旧字段移除
    if (row.existingName && (row.removed || row.name !== row.existingName)) {
      changes[row.existingName] = null
    }
    if (row.removed) continue
    if (!row.name || (!row.existingName && !row.value)) throw new Error(`${label}名称和值都要填写`)
    const key = label === '请求头' ? row.name.toLowerCase() : row.name
    if (names.has(key)) throw new Error(`${label}名称不能重复：${row.name}`)
    names.add(key)
    if (row.value) changes[row.name] = row.value
    else if (row.name !== row.existingName) throw new Error(`${label}改名后需要填写新值`)
  }
  return changes
}

// MCP 配置校验与提交
function submitForm(): void {
  error.value = ''
  try {
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(form.name))
      throw new Error('名称须以英文字母开头，只能含英文字母、数字、- 和 _')
    if (!(form.connectTimeout > 0) || !(form.callTimeout > 0)) throw new Error('超时时间必须大于 0')
    const changingTransport = Boolean(props.server && props.server.transport !== form.transport)
    if (
      form.transport === 'streamable_http' &&
      form.enabled &&
      !form.url &&
      (!props.server?.has_hidden_url || changingTransport)
    ) {
      throw new Error('启用远程服务前请填写服务器地址')
    }
    if (
      form.transport === 'stdio' &&
      form.enabled &&
      !form.command &&
      (!props.server?.command_configured || changingTransport || form.clearCommand)
    ) {
      throw new Error('启用本地服务前请填写启动命令')
    }

    const values: McpServerPatch = {
      description: form.description || null,
      enabled: form.enabled,
      transport: form.transport,
      connect_timeout_seconds: form.connectTimeout,
      call_timeout_seconds: form.callTimeout,
    }
    if (form.transport === 'streamable_http') {
      const headers = pairsToChanges(headerRows.value, '请求头')
      if (Object.keys(headers).length) values.headers = headers
      if (!props.server || changingTransport || urlDirty.value) values.url = form.url || null
      if (changingTransport) {
        // 旧连接方式字段清理
        values.command = null
        values.args = []
        values.env = null
        values.cwd = null
      }
    } else {
      const env = pairsToChanges(envRows.value, '环境变量')
      if (Object.keys(env).length) values.env = env
      if (form.command || form.clearCommand)
        values.command = form.clearCommand ? null : form.command
      if (!props.server || form.replaceArgs || changingTransport) {
        values.args = form.argsText
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean)
      }
      if (form.cwd || form.clearCwd) values.cwd = form.clearCwd ? null : form.cwd
      if (changingTransport) {
        // 旧连接方式字段清理
        values.url = null
        values.headers = null
      }
    }

    if (props.server) {
      emit('submit', values)
    } else {
      const headers = values.headers ?? undefined
      const env = values.env ?? undefined
      emit('submit', {
        ...values,
        name: form.name,
        headers: headers as Record<string, string> | undefined,
        env: env as Record<string, string> | undefined,
      } as McpServerCreate)
    }
  } catch (cause: unknown) {
    error.value = cause instanceof Error ? cause.message : '请检查配置内容'
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
  width: min(650px, 100%);
  max-height: min(800px, calc(100dvh - 40px));
  overflow: hidden;
  border: 1px solid #d8d8d8;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.16);
}
.dialog-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex: 0 0 auto;
  border-bottom: 1px solid #e7e7e7;
  padding: 23px 28px 21px;
  background: #fafafa;
}
.dialog-header > div {
  flex: 1;
  min-width: 0;
}
.dialog-header h2 {
  color: #171717;
  font-size: 19px;
  font-weight: 680;
  letter-spacing: -0.02em;
}
.dialog-header p {
  margin-top: 7px;
  color: #777;
  font-size: 12px;
  line-height: 1.5;
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
}
.dialog-form {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.dialog-body {
  overflow-y: auto;
  padding: 0 28px;
  overscroll-behavior: contain;
  scrollbar-width: none;
}
.dialog-body::-webkit-scrollbar {
  display: none;
}
.form-section {
  border-bottom: 1px solid #e9e9e9;
  padding: 23px 0 27px;
}
.form-section.last-section {
  border-bottom: 0;
}
.section-heading {
  margin-bottom: 18px;
}
.section-heading h3 {
  color: #222;
  font-size: 13px;
  font-weight: 680;
}
.section-content {
  display: grid;
  gap: 18px;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.description-field {
  margin-top: 16px;
}
.field {
  display: grid;
  gap: 8px;
  min-width: 0;
  color: #3e3e3e;
  font-size: 12px;
  font-weight: 600;
}
.field input,
.field textarea,
.pair-row input {
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
  min-height: 75px;
  resize: vertical;
}
.field input::placeholder,
.pair-row input::placeholder {
  color: #aaa;
}
.field input:focus,
.field textarea:focus,
.pair-row input:focus {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.field input:disabled,
.field textarea:disabled {
  background: #f5f5f5;
  color: #888;
}
.transport-select {
  width: 100%;
  --el-color-primary: #333;
}
.transport-select :deep(.el-select__wrapper) {
  min-height: 39px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  box-shadow: none;
  background: #fff;
}
.transport-select :deep(.el-select__wrapper.is-focused) {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.transport-select :deep(.el-select__selected-item) {
  color: #222;
  font-size: 12px;
  font-weight: 450;
}
.transport-select :deep(.el-select__caret) {
  color: #858585;
}
:global(.mcp-transport-popper.el-popper) {
  border-color: #e2e2e2;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
:global(.mcp-transport-popper .el-select-dropdown__item) {
  height: 34px;
  color: #444;
  font-size: 12px;
  line-height: 34px;
}
:global(.mcp-transport-popper .el-select-dropdown__item.is-hovering) {
  background: #f4f4f4;
}
:global(.mcp-transport-popper .el-select-dropdown__item.is-selected) {
  background: #ededed;
  color: #222;
  font-weight: 600;
}
.field small,
.field-hint {
  color: #818181;
  font-size: 11px;
  font-weight: 450;
  line-height: 1.55;
}
.pair-row {
  display: grid;
  grid-template-columns: minmax(0, 0.88fr) minmax(0, 1.3fr) 44px;
  gap: 8px;
}
.pair-remove {
  display: grid;
  min-height: 39px;
  place-items: center;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  background: #fff;
  color: #666;
  cursor: pointer;
  touch-action: manipulation;
}
.text-button {
  display: inline-flex;
  align-items: center;
  justify-self: start;
  min-height: 30px;
  border: 0;
  padding: 0;
  background: transparent;
  color: #333;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.small-check {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #555;
  font-size: 12px;
  cursor: pointer;
}
.small-check input {
  accent-color: #222;
}
.enable-check {
  margin-top: 20px;
  color: #333;
  font-weight: 600;
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
.close-button:focus-visible,
.pair-remove:focus-visible,
.text-button:focus-visible,
.secondary-button:focus-visible,
.primary-button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (hover: hover) {
  .transport-select :deep(.el-select__wrapper:not(.is-focused):hover) {
    border-color: #aaa;
  }
  .close-button:hover,
  .pair-remove:hover {
    background: #f4f4f4;
  }
  .text-button:hover {
    color: #111;
    text-decoration: underline;
  }
  .secondary-button:hover {
    border-color: #777;
  }
  .primary-button:hover {
    background: #333;
  }
}
@media (max-width: 560px), (any-pointer: coarse) {
  .field input,
  .field textarea,
  .pair-row input {
    min-height: 44px;
    font-size: 16px;
  }
  .transport-select :deep(.el-select__wrapper) {
    min-height: 44px;
  }
  .transport-select :deep(.el-select__selected-item) {
    font-size: 16px;
  }
}
@media (max-width: 560px) {
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
  .field-grid {
    grid-template-columns: 1fr;
  }
  .pair-row {
    grid-template-columns: minmax(0, 1fr) 44px;
  }
  .pair-row input:nth-child(2) {
    grid-column: 1;
  }
  .pair-remove {
    grid-column: 2;
    grid-row: 1 / 3;
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
@media (any-pointer: coarse) {
  .close-button,
  .pair-remove {
    min-width: 44px;
    min-height: 44px;
  }
  .text-button,
  .small-check {
    min-height: 44px;
  }
  .secondary-button,
  .primary-button {
    min-height: 44px;
  }
}
</style>
