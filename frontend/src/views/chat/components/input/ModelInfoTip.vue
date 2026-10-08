<!--模型配置信息气泡-->
<template>
  <div class="model-info-tip">
    <div class="model-info-title">{{ model.display_name }}</div>
    <p v-if="model.description" class="model-info-desc">{{ model.description }}</p>
    <div class="model-info-rows">
      <div v-for="row in infoRows" :key="row.label" class="model-info-row">
        <span class="model-info-label">{{ row.label }}</span>
        <span class="model-info-value">{{ row.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ModelInfo } from '@/api/config'

const props = defineProps<{ model: ModelInfo }>()

// 只保留有值的字段
const infoRows = computed(() => {
  const model = props.model
  const context = model.context_window
  return [
    { label: '厂商', value: model.provider },
    { label: '接口模型', value: model.model_name },
    { label: '上下文', value: context === null ? '' : formatContext(context) },
    { label: '推理强度', value: model.supports_thinking ? model.reasoning_levels.join(' / ') : '' },
    { label: '视觉', value: model.supports_vision ? '支持' : '不支持' },
  ].filter((row) => row.value)
})

/** 上下文长度按 1024 进制缩写 */
function formatContext(size: number): string {
  if (size < 1024) return `${size}`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}K`
  return `${(size / (1024 * 1024)).toFixed(1)}M`
}
</script>

<style scoped>
.model-info-tip {
  padding: 9px 10px 10px;
  background: #fff;
  border-radius: 9px;
  color: #303133;
}

.model-info-title {
  font-size: 12.5px;
  font-weight: 600;
}

.model-info-desc {
  margin: 3px 0 0;
  color: #6b7280;
  font-size: 11px;
  line-height: 1.5;
}

.model-info-rows {
  margin-top: 7px;
  padding-top: 6px;
  border-top: 1px solid #eef0f3;
}

.model-info-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  font-size: 11px;
  line-height: 1.85;
}

.model-info-label {
  flex-shrink: 0;
  color: #8b9098;
}

.model-info-value {
  overflow: hidden;
  color: #4b5563;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
