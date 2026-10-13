<!--MCP 服务器状态卡片-->
<template>
  <article class="server-card" :class="`server-${currentState}`">
    <div class="card-main">
      <div class="server-identity">
        <div class="title-line">
          <h3>{{ config.name }}</h3>
          <span class="state" :class="`state-${currentState}`"><i />{{ stateText }}</span>
        </div>
        <p v-if="config.description" class="server-description" :title="config.description">
          {{ config.description }}
        </p>
        <div class="server-meta">
          <span class="transport">{{
            config.transport === 'stdio' ? '本地 stdio' : '远程 HTTP'
          }}</span>
          <span v-if="config.url" class="server-url" :title="config.url">{{ config.url }}</span>
          <span v-else-if="config.has_hidden_url" class="server-url">地址含隐藏信息</span>
        </div>
      </div>
      <button
        class="enable-switch"
        :class="{ 'is-on': config.enabled }"
        type="button"
        role="switch"
        :disabled="busy"
        :aria-label="`${config.enabled ? '停用' : '启用'} ${config.name}`"
        :aria-checked="config.enabled"
        @click="$emit('toggle')"
      >
        <span class="switch-track"><span class="switch-thumb" /></span>
        <span>{{ config.enabled ? '已启用' : '已停用' }}</span>
      </button>
    </div>

    <div v-if="status?.message" class="status-note error-note">
      <CircleAlert :size="15" />{{ status.message }}
    </div>
    <div v-else-if="currentState === 'unchecked'" class="status-note">
      <CircleHelp :size="15" />刷新连接后会显示可用工具
    </div>

    <div class="card-footer">
      <button
        class="tools-toggle"
        type="button"
        :disabled="!status?.tool_count"
        :aria-expanded="toolsOpen"
        @click="toolsOpen = !toolsOpen"
      >
        <strong>{{ status?.tool_count ?? 0 }}</strong> 个工具
        <ChevronDown v-if="status?.tool_count" :size="15" :class="{ rotated: toolsOpen }" />
      </button>
      <div class="card-actions">
        <button
          type="button"
          :disabled="busy"
          :aria-label="`编辑 ${config.name}`"
          @click="$emit('edit')"
        >
          编辑
        </button>
        <span class="action-divider" aria-hidden="true" />
        <button
          class="delete-button"
          type="button"
          :disabled="busy"
          :aria-label="`删除 ${config.name}`"
          @click="$emit('remove')"
        >
          删除
        </button>
      </div>
    </div>

    <div v-if="toolsOpen && status?.tool_names.length" class="tools-panel" aria-label="工具列表">
      <div class="tools-heading">
        <div>
          <h4>
            可用工具 <span>{{ status.tool_count }}</span>
          </h4>
        </div>
        <label class="tool-search">
          <Search :size="15" aria-hidden="true" />
          <input
            v-model.trim="toolQuery"
            type="search"
            placeholder="搜索工具"
            aria-label="搜索工具"
          />
        </label>
      </div>
      <div v-if="filteredTools.length" class="tool-grid">
        <div v-for="name in filteredTools" :key="name" class="tool-item" :title="name">
          <div class="tool-text">
            <strong>{{ shortToolName(name) }}</strong>
            <span>{{ name }}</span>
          </div>
        </div>
      </div>
      <p v-else class="no-tools">没有匹配的工具</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDown, CircleAlert, CircleHelp, Search } from 'lucide-vue-next'
import type { McpServerConfig, McpServerStatus, McpState } from '@/api/mcp'

const props = defineProps<{
  config: McpServerConfig
  status?: McpServerStatus
  busy: boolean
}>()

defineEmits<{ edit: []; toggle: []; remove: [] }>()

const toolsOpen = ref(false)
const toolQuery = ref('')
const filteredTools = computed(() =>
  (props.status?.tool_names ?? []).filter((name) =>
    name.toLowerCase().includes(toolQuery.value.toLowerCase()),
  ),
)

// 工具名称简写
function shortToolName(name: string): string {
  const prefix = `${props.config.name.toLowerCase().replaceAll('-', '_')}_`
  return name.startsWith(prefix) ? name.slice(prefix.length) : name
}
// 服务状态映射
const currentState = computed<McpState>(() =>
  props.config.enabled ? (props.status?.state ?? 'unchecked') : 'disabled',
)
const stateText = computed(() => {
  const labels: Record<McpState, string> = {
    unchecked: '未检查',
    connected: '已连接',
    failed: '连接失败',
    disabled: '已停用',
  }
  return labels[currentState.value]
})
</script>

<style scoped>
.server-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.card-main {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
  padding: 23px 24px 22px;
}
.server-identity {
  flex: 1;
  min-width: 0;
}
.title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.title-line h3 {
  overflow-wrap: anywhere;
  color: #171717;
  font-size: 15px;
  font-weight: 680;
  letter-spacing: -0.01em;
}
.server-description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 8px;
  color: #686868;
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 999px;
  padding: 3px 8px;
  background: #f4f4f4;
  color: #777;
  font-size: 11px;
  font-weight: 550;
  white-space: nowrap;
}
.state i {
  width: 7px;
  height: 7px;
  border: 1px solid #8a8a8a;
  border-radius: 50%;
  background: #fff;
}
.state-connected {
  background: #edf4ed;
  color: #4e7559;
}
.state-connected i {
  border-color: #668a70;
  background: #668a70;
}
.state-failed {
  background: #fbefeb;
  color: #a36558;
  font-weight: 680;
}
.state-failed i {
  border-color: #a36558;
  background: #a36558;
  box-shadow: 0 0 0 2px #fff inset;
}
.state-disabled {
  background: #f3f3f3;
  color: #959595;
}
.server-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  margin-top: 9px;
  color: #858585;
  font-size: 12px;
}
.transport {
  flex: 0 0 auto;
}
.transport::after {
  content: '·';
  margin-left: 10px;
  color: #aaa;
}
.server-url {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.enable-switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  border: 0;
  padding: 6px 0 6px 8px;
  background: transparent;
  color: #777;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.enable-switch.is-on {
  color: #4e7559;
}
.switch-track {
  position: relative;
  width: 32px;
  height: 19px;
  border-radius: 999px;
  background: #c7c7c7;
}
.switch-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s ease;
}
.is-on .switch-track {
  background: #678a70;
}
.is-on .switch-thumb {
  transform: translateX(13px);
}
.enable-switch:disabled,
.card-actions button:disabled {
  cursor: wait;
  opacity: 0.5;
}
.status-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 24px 20px;
  color: #777;
  font-size: 12px;
  line-height: 1.5;
}
.status-note svg {
  flex: 0 0 auto;
}
.error-note {
  color: #a36558;
  font-weight: 550;
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  border-top: 1px solid #ebebeb;
  padding: 0 17px 0 24px;
  background: #fafafa;
}
.tools-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  border: 0;
  background: transparent;
  color: #444;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
}
.tools-toggle strong {
  color: #222;
  font-weight: 680;
}
.tools-toggle:disabled {
  color: #aaa;
  cursor: default;
}
.tools-toggle:disabled strong {
  color: inherit;
}
.tools-toggle svg {
  margin-left: 2px;
  transition: transform 0.18s ease;
}
.tools-toggle svg.rotated {
  transform: rotate(180deg);
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
}
.card-actions button {
  min-height: 32px;
  border: 0;
  border-radius: 5px;
  padding: 0 9px;
  background: transparent;
  color: #626262;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
}
.action-divider {
  width: 1px;
  height: 14px;
  margin: 0 2px;
  background: #dedede;
}
.card-actions .delete-button {
  color: #c62828;
}
.tools-panel {
  border-top: 1px solid #e5e5e5;
  padding: 24px;
  background: #fafafa;
}
.tools-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 15px;
}
.tools-heading h4 {
  color: #222;
  font-size: 13px;
  font-weight: 680;
}
.tools-heading h4 span {
  margin-left: 5px;
  color: #888;
  font-weight: 500;
}
.tool-search {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 205px;
  height: 34px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #777;
}
.tool-search:focus-within {
  border-color: #555;
  outline: 1px solid #555;
}
.tool-search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #222;
  font-size: 12px;
}
.tool-search input::placeholder {
  color: #aaa;
}
.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid #e4e4e4;
}
.tool-item {
  min-width: 0;
  border-bottom: 1px solid #e8e8e8;
  padding: 11px 10px 11px 0;
}
.tool-item:nth-child(even) {
  padding-left: 15px;
}
.tool-text {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.tool-text strong,
.tool-text span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tool-text strong {
  color: #292929;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 12px;
  font-weight: 600;
}
.tool-text span {
  color: #929292;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 10px;
}
.no-tools {
  border-top: 1px solid #e4e4e4;
  padding: 22px 0;
  color: #888;
  text-align: center;
  font-size: 12px;
}
@media (hover: hover) {
  .enable-switch:hover,
  .card-actions button:hover,
  .tools-toggle:hover {
    color: #222;
  }
  .enable-switch.is-on:hover {
    color: #4e7559;
  }
  .card-actions button:hover {
    background: #f3f3f3;
  }
}
.enable-switch:focus-visible,
.tools-toggle:focus-visible,
.card-actions button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (max-width: 720px) {
  .card-main {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 15px;
    padding: 19px;
  }
  .server-identity {
    flex-basis: 100%;
  }
  .enable-switch {
    padding-left: 0;
  }
  .status-note {
    margin: 0 19px 17px;
  }
  .card-footer {
    padding: 0 10px 0 19px;
  }
  .tools-panel {
    padding: 18px;
  }
  .tool-grid {
    grid-template-columns: 1fr;
  }
  .tool-item:nth-child(even) {
    padding-left: 0;
  }
}
@media (max-width: 430px) {
  .tools-heading {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }
  .tool-search {
    width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .switch-thumb,
  .tools-toggle svg {
    transition: none;
  }
}
@media (any-pointer: coarse) {
  .enable-switch,
  .tools-toggle,
  .card-actions button {
    min-height: 40px;
  }
  .tool-search {
    height: 44px;
  }
}
@media (max-width: 720px), (any-pointer: coarse) {
  .tool-search input {
    font-size: 16px;
  }
}
</style>
