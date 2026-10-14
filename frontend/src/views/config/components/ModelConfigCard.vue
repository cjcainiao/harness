<!--模型配置卡片-->
<template>
  <article class="model-card">
    <div class="model-main">
      <div class="model-heading">
        <div class="model-title">
          <div class="title-line">
            <h3>{{ model.display_name || model.model_name }}</h3>
            <span v-if="isDefault" class="default-badge">默认</span>
          </div>
          <p class="model-id">{{ model.model_name }}</p>
        </div>
        <span class="provider-badge">{{ providerLabel }}</span>
      </div>
      <p v-if="model.description" class="description">{{ model.description }}</p>
      <div class="capabilities">
        <span :class="{ supported: model.supports_thinking }">
          <BrainCircuit :size="14" />{{ model.supports_thinking ? '推理' : '无推理' }}
        </span>
        <span :class="{ supported: model.supports_vision }">
          <Eye :size="14" />{{ model.supports_vision ? '视觉' : '无视觉' }}
        </span>
        <span v-if="model.supports_thinking && model.reasoning_levels.length" class="levels">
          {{ model.reasoning_levels.join(' / ') }}
        </span>
      </div>
      <div class="model-facts">
        <div>
          <span>上下文</span>
          <strong>{{ formatTokens(model.context_window) }}</strong>
        </div>
        <div>
          <span>最大输出</span>
          <strong>{{ formatTokens(model.max_tokens) }}</strong>
        </div>
        <div>
          <span>连接地址</span>
          <strong class="endpoint">{{ model.base_url_configured ? '已配置' : '未设置' }}</strong>
        </div>
      </div>
    </div>
    <footer class="card-footer">
      <span class="key-state">
        <span :class="{ configured: model.api_key_configured }" />
        {{ model.api_key_configured ? '密钥已配置' : '未配置密钥' }}
      </span>
      <div class="card-actions">
        <button v-if="!isDefault" type="button" :disabled="busy" @click="$emit('set-default')">
          设为默认
        </button>
        <button type="button" :disabled="busy" @click="$emit('edit')">编辑</button>
        <button class="delete-button" type="button" :disabled="busy" @click="$emit('remove')">
          删除
        </button>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BrainCircuit, Eye } from 'lucide-vue-next'
import type { ModelConfigItem } from '@/api/modelConfig'

const props = defineProps<{ model: ModelConfigItem; isDefault: boolean; busy: boolean }>()
defineEmits<{ edit: []; remove: []; 'set-default': [] }>()

const providerLabel = computed(() => {
  const names: Record<string, string> = { deepseek: 'DeepSeek', alibaba: '阿里云' }
  return names[props.model.provider.toLowerCase()] ?? props.model.provider
})

// 令牌数量格式化
function formatTokens(value: number | null): string {
  if (value === null) return '未设置'
  if (value >= 1024) return `${Number((value / 1024).toFixed(1))}K`
  return value.toLocaleString('zh-CN')
}
</script>

<style scoped>
.model-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.model-main {
  padding: 21px 23px 19px;
}
.model-heading,
.title-line,
.capabilities,
.card-footer,
.card-actions {
  display: flex;
  align-items: center;
}
.model-heading {
  justify-content: space-between;
  gap: 18px;
}
.model-title {
  min-width: 0;
}
.title-line {
  flex-wrap: wrap;
  gap: 9px;
}
.title-line h3 {
  overflow-wrap: anywhere;
  color: #171717;
  font-size: 16px;
  font-weight: 680;
  letter-spacing: -0.015em;
}
.default-badge,
.provider-badge {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}
.default-badge {
  background: #eaf2ea;
  color: #4a7254;
}
.provider-badge {
  background: #f2f2f2;
  color: #666;
}
.model-id {
  margin-top: 5px;
  color: #969696;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 11px;
}
.description {
  margin-top: 16px;
  color: #646464;
  font-size: 12px;
  line-height: 1.6;
}
.capabilities {
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 15px;
}
.capabilities span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid #e6e6e6;
  border-radius: 5px;
  padding: 5px 7px;
  background: #fafafa;
  color: #929292;
  font-size: 11px;
  line-height: 1;
}
.capabilities span.supported {
  border-color: #dce8dd;
  background: #f3f8f3;
  color: #52745a;
}
.capabilities span.levels {
  border-color: transparent;
  background: transparent;
  color: #898989;
}
.model-facts {
  display: grid;
  grid-template-columns: 0.8fr 0.8fr minmax(0, 2fr);
  gap: 14px;
  margin-top: 19px;
  border-top: 1px solid #eee;
  padding-top: 17px;
}
.model-facts > div {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.model-facts span {
  color: #999;
  font-size: 11px;
}
.model-facts strong {
  overflow: hidden;
  color: #404040;
  font-size: 12px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.model-facts .endpoint {
  font-weight: 450;
}
.card-footer {
  justify-content: space-between;
  gap: 12px;
  min-height: 49px;
  border-top: 1px solid #ebebeb;
  padding: 5px 14px 5px 23px;
  background: #fafafa;
}
.key-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #888;
  font-size: 11px;
  white-space: nowrap;
}
.key-state > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #bababa;
}
.key-state > span.configured {
  background: #668a70;
}
.card-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 3px;
}
.card-actions button {
  min-height: 31px;
  border: 0;
  border-radius: 5px;
  padding: 0 9px;
  background: transparent;
  color: #626262;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.card-actions .delete-button {
  color: #c62828;
}
.card-actions button:disabled {
  cursor: wait;
  opacity: 0.5;
}
@media (hover: hover) {
  .card-actions button:hover {
    background: #f3f3f3;
  }
  .card-actions .delete-button:hover {
    background: #f3f3f3;
  }
}
.card-actions button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .model-main {
    padding: 19px;
  }
  .model-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .model-facts > div:last-child {
    grid-column: 1 / -1;
  }
  .card-footer {
    align-items: flex-start;
    gap: 4px;
    padding: 6px 10px 6px 19px;
  }
  .key-state {
    min-width: 0;
    min-height: 31px;
    flex: 1 1 auto;
  }
  .card-actions {
    width: auto;
    flex: 0 0 auto;
    flex-wrap: nowrap;
    justify-content: flex-end;
    gap: 0;
  }
}
@media (any-pointer: coarse) {
  .key-state {
    min-height: 40px;
  }
  .card-actions button {
    min-height: 40px;
  }
}
</style>
