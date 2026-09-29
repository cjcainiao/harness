<template>
  <div class="stream-status" :class="{ 'is-active': active }" role="status">
    <DotsMatrix />
    <span class="status-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DotsMatrix from '@/components/DotsMatrix.vue'
import type { StreamPhase } from '../message/messageTurn'

const props = defineProps<{ active: boolean; phase: StreamPhase }>()

// 各阶段提示文案，加文案直接往这里补
const statusTexts: Record<StreamPhase, string> = {
  idle: '',
  waiting: '快进一下…',
  tool: '正在执行工具…',
  streaming: '正在回复…',
}
const text = computed(() => statusTexts[props.phase])
</script>

<style scoped>
.stream-status {
  display: flex;
  align-items: center;
  gap: 9px;
  box-sizing: border-box;
  max-width: 980px;
  margin: 0 auto;
  padding: 0 17px 24px 24px;
  color: #6d757e;
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
  /* 常驻占位，避免输入卡随回复开始和结束上下跳 */
  visibility: hidden;
}
.stream-status.is-active {
  visibility: visible;
}
</style>
