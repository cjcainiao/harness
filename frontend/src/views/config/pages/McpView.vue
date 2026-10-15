<!--MCP 服务器设置页-->
<template>
  <div class="mcp-shell" :class="{ 'is-empty': showEmptyState }">
    <div class="mcp-page">
      <header class="page-header">
        <div class="page-heading">
          <StackIllustration :icon="PlugZap" compact />
          <div>
            <h1>MCP 服务器</h1>
            <p class="page-intro">管理对话中可用的外部工具和连接。</p>
          </div>
        </div>
        <button class="add-button" type="button" :disabled="isBusy" @click="openCreate">
          <Plus :size="16" :stroke-width="2" /> 添加服务器
        </button>
      </header>

      <section v-if="showEmptyState" class="empty-state">
        <StackIllustration :icon="PlugZap" />
        <h2>暂无 MCP 服务器，点击<span>添加服务器</span>开始使用</h2>
      </section>

      <section v-if="configs.length" class="summary" aria-label="MCP 服务概况">
        <div class="summary-text">
          <span class="summary-stat">
            <strong>{{ connectedCount }} / {{ configs.length }}</strong>
            <span>已连接</span>
          </span>
          <span class="summary-stat">
            <strong>{{ toolCount }}</strong>
            <span>个工具</span>
          </span>
          <span class="summary-check">上次检查 {{ lastChecked }}</span>
        </div>
        <button
          class="refresh-button"
          type="button"
          :disabled="isBusy || loading || !configs.length"
          @click="refresh"
        >
          <RefreshCw :size="14" :class="{ spinning: refreshing }" />
          {{ refreshing ? '检查中…' : '刷新连接' }}
        </button>
      </section>

      <section v-if="loading || loadError || configs.length" class="server-section">
        <div class="section-heading">
          <div>
            <h2>
              服务器 <span>{{ configs.length }}</span>
            </h2>
          </div>
          <p>配置变更将在下一轮对话中生效</p>
        </div>
        <div v-if="loading" class="state-panel">正在读取 MCP 服务…</div>
        <div v-else-if="loadError && !configs.length" class="state-panel error-panel">
          <p>{{ loadError }}</p>
          <button type="button" @click="reload">重试</button>
        </div>
        <div v-else class="server-list">
          <p v-if="loadError" class="inline-error" role="alert">{{ loadError }}</p>
          <McpServerCard
            v-for="config in configs"
            :key="config.name"
            :config="config"
            :status="statusByName.get(config.name)"
            :busy="isBusy"
            @edit="openEdit(config)"
            @toggle="toggleServer(config)"
            @remove="removeServer(config)"
          />
        </div>
      </section>

      <McpServerForm
        :open="formOpen"
        :server="editingServer"
        :saving="busyAction === 'save'"
        @close="formOpen = false"
        @submit="saveServer"
      />
      <DeleteConfirmDialog
        :open="pendingDelete !== null"
        :title="`删除 ${pendingDelete?.name ?? ''}？`"
        description="删除后将无法在对话中使用这台服务器的工具。"
        confirm-text="删除服务器"
        :busy="isBusy"
        @close="pendingDelete = null"
        @confirm="confirmRemoveServer"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { PlugZap, Plus, RefreshCw } from 'lucide-vue-next'
import {
  createMcpServer,
  deleteMcpServer,
  fetchMcpConfigs,
  fetchMcpStatus,
  patchMcpServer,
  refreshMcpStatus,
  setMcpServerEnabled,
  type McpServerConfig,
  type McpServerCreate,
  type McpServerPatch,
  type McpStatusSnapshot,
} from '@/api/mcp'
import McpServerCard from '../components/McpServerCard.vue'
import McpServerForm from '../components/McpServerForm.vue'
import DeleteConfirmDialog from '../components/DeleteConfirmDialog.vue'
import StackIllustration from '../components/StackIllustration.vue'

const configs = ref<McpServerConfig[]>([])
const snapshot = ref<McpStatusSnapshot | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const busyAction = ref<string | null>(null)
const loadError = ref('')
const formOpen = ref(false)
const editingServer = ref<McpServerConfig | null>(null)
const pendingDelete = ref<McpServerConfig | null>(null)

const statusByName = computed(
  () => new Map((snapshot.value?.servers ?? []).map((server) => [server.name, server])),
)
const connectedCount = computed(
  () => snapshot.value?.servers.filter((server) => server.state === 'connected').length ?? 0,
)
const toolCount = computed(
  () => snapshot.value?.servers.reduce((count, server) => count + server.tool_count, 0) ?? 0,
)
const isBusy = computed(() => busyAction.value !== null || refreshing.value)
const showEmptyState = computed(
  () => !loading.value && !loadError.value && configs.value.length === 0,
)
const lastChecked = computed(() => {
  if (!snapshot.value?.checked_at) return '尚未检查'
  return new Date(snapshot.value.checked_at).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function notify(type: 'success' | 'error', message: string): void {
  ElMessage({ type, message, plain: true })
}

// MCP 配置与状态加载
async function loadAll(silent = false): Promise<boolean> {
  if (!silent) loading.value = true
  loadError.value = ''
  try {
    const [nextConfigs, nextStatus] = await Promise.all([fetchMcpConfigs(), fetchMcpStatus()])
    configs.value = nextConfigs
    snapshot.value = nextStatus
    return true
  } catch (error: unknown) {
    loadError.value = messageOf(error, '读取 MCP 服务失败')
    if (!silent) notify('error', loadError.value)
    return false
  } finally {
    loading.value = false
  }
}

function reload(): void {
  void loadAll()
}

function openCreate(): void {
  editingServer.value = null
  formOpen.value = true
}

function openEdit(config: McpServerConfig): void {
  editingServer.value = config
  formOpen.value = true
}

// MCP 连接刷新
async function refresh(): Promise<void> {
  if (isBusy.value) return
  refreshing.value = true
  try {
    snapshot.value = await refreshMcpStatus()
    notify('success', 'MCP 服务检查完成')
  } catch (error: unknown) {
    notify('error', messageOf(error, '刷新 MCP 服务失败'))
  } finally {
    refreshing.value = false
  }
}

// MCP 配置保存
async function saveServer(payload: McpServerCreate | McpServerPatch): Promise<void> {
  if (isBusy.value) return
  busyAction.value = 'save'
  try {
    if (editingServer.value) {
      await patchMcpServer(editingServer.value.name, payload as McpServerPatch)
    } else {
      await createMcpServer(payload as McpServerCreate)
    }
    formOpen.value = false
    if (await loadAll(true)) {
      notify('success', 'MCP 配置已保存')
    } else {
      notify('error', `MCP 配置已保存，但重新读取失败：${loadError.value}`)
    }
  } catch (error: unknown) {
    notify('error', messageOf(error, '保存 MCP 配置失败'))
  } finally {
    busyAction.value = null
  }
}

// 服务启停与连接刷新
async function toggleServer(config: McpServerConfig): Promise<void> {
  if (isBusy.value) return
  busyAction.value = config.name
  try {
    const enabled = !config.enabled
    const updated = await setMcpServerEnabled(config.name, enabled)
    configs.value = configs.value.map((server) => (server.name === updated.name ? updated : server))
    snapshot.value = null
    refreshing.value = true
    try {
      snapshot.value = await refreshMcpStatus()
      notify('success', enabled ? '服务已启用，连接检查完成' : '服务已停用，连接检查完成')
    } catch (error: unknown) {
      notify(
        'error',
        `服务已${enabled ? '启用' : '停用'}，但刷新连接失败：${messageOf(error, '请稍后重试')}`,
      )
    }
  } catch (error: unknown) {
    notify('error', messageOf(error, '切换 MCP 服务失败'))
  } finally {
    refreshing.value = false
    busyAction.value = null
  }
}

// MCP 服务器删除
function removeServer(config: McpServerConfig): void {
  if (isBusy.value) return
  pendingDelete.value = config
}

async function confirmRemoveServer(): Promise<void> {
  const config = pendingDelete.value
  if (!config || isBusy.value) return
  pendingDelete.value = null
  busyAction.value = config.name
  try {
    await deleteMcpServer(config.name)
    if (await loadAll(true)) {
      notify('success', '服务已删除')
    } else {
      notify('error', `服务已删除，但重新读取失败：${loadError.value}`)
    }
  } catch (error: unknown) {
    notify('error', messageOf(error, '删除 MCP 服务失败'))
  } finally {
    busyAction.value = null
  }
}

onMounted(() => void loadAll())
</script>

<style scoped>
.mcp-shell {
  min-height: 100%;
  background: #fafafa;
}
.mcp-shell.is-empty {
  background: #fff;
}
.mcp-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 56px 96px;
  color: #171717;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.page-heading {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 680;
  letter-spacing: -0.035em;
  line-height: 1.25;
}
.page-intro {
  margin-top: 10px;
  color: #737373;
  font-size: 13px;
  line-height: 1.6;
}
.add-button,
.refresh-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 0 0 auto;
  min-height: 38px;
  border: 1px solid #171717;
  border-radius: 7px;
  padding: 0 13px;
  background: #171717;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.refresh-button {
  border-color: #d8d8d8;
  background: #fff;
  color: #333;
}
.add-button:disabled,
.refresh-button:disabled {
  cursor: wait;
  opacity: 0.5;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  min-height: clamp(280px, calc(100vh - 220px), 540px);
  text-align: center;
}
.empty-state h2 {
  color: #444;
  font-size: 16px;
  font-weight: 650;
  line-height: 1.6;
}
.empty-state h2 span {
  color: #171717;
  font-weight: 700;
}
.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 68px;
  margin-top: 38px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 0 18px;
  background: #fff;
}
.summary-text {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  color: #777;
  font-size: 12px;
  line-height: 1.5;
}
.summary-stat {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  white-space: nowrap;
}
.summary-stat + .summary-stat {
  border-left: 1px solid #e1e1e1;
  padding-left: 18px;
}
.summary-text strong {
  color: #222;
  font-size: 15px;
  font-weight: 700;
}
.summary-check {
  color: #888;
  white-space: nowrap;
}
.spinning {
  animation: spin 1.2s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.server-section {
  margin-top: 43px;
}
.section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 17px;
}
.section-heading h2 {
  font-size: 16px;
  font-weight: 680;
  letter-spacing: -0.015em;
}
.section-heading h2 span {
  margin-left: 6px;
  color: #888;
  font-size: 13px;
  font-weight: 500;
}
.section-heading > p {
  color: #888;
  font-size: 12px;
}
.server-list {
  display: grid;
  gap: 10px;
}
.state-panel {
  display: grid;
  min-height: 230px;
  place-content: center;
  gap: 10px;
  border: 1px solid #e5e5e5;
  background: #fff;
  color: #666;
  text-align: center;
  font-size: 13px;
}
.error-panel button {
  justify-self: center;
  border: 0;
  background: none;
  color: #171717;
  text-decoration: underline;
  cursor: pointer;
}
.inline-error {
  border: 1px solid #e3c9c3;
  padding: 10px 14px;
  background: #fbf4f1;
  color: #89594e;
  font-size: 12px;
}
@media (hover: hover) {
  .add-button:hover {
    background: #333;
  }
  .refresh-button:hover {
    border-color: #aaa;
    background: #f3f3f3;
  }
}
.add-button:focus-visible,
.refresh-button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 3px;
}
.is-empty .add-button:focus-visible {
  outline-color: #171717;
}
@media (max-width: 720px) {
  .mcp-page {
    padding: 30px 20px 64px;
  }
  .page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 22px;
  }
  .page-header h1 {
    font-size: 25px;
  }
  .add-button {
    align-self: flex-start;
  }
  .summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
    padding: 15px;
  }
  .summary-text {
    gap: 8px 16px;
  }
  .summary-stat + .summary-stat {
    padding-left: 16px;
  }
  .summary-check {
    flex-basis: 100%;
  }
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }
  .server-section {
    margin-top: 36px;
  }
  .empty-state {
    min-height: clamp(300px, calc(100dvh - 230px), 520px);
    padding: 0 8px;
  }
}
@media (max-width: 380px) {
  .summary-stat + .summary-stat {
    padding-left: 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .spinning {
    animation: none;
  }
}
@media (any-pointer: coarse) {
  .add-button,
  .refresh-button {
    min-height: 42px;
  }
}
</style>
