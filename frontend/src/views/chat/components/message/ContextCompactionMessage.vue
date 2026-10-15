<!--上下文压缩历史段-->
<template>
  <div class="compaction-entry" :role="isRunning ? 'status' : undefined">
    <span class="compaction-orb" :class="{ 'is-running': isRunning }" aria-hidden="true" />
    <ShimmerText :active="isRunning">{{ label }}</ShimmerText>
    <span v-if="timerVisible" class="compaction-timer">
      {{ isRunning ? timerText : `耗时 ${timerText}` }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ShimmerText from '@/components/ShimmerText.vue'
import { formatDuration, useLiveTimer } from '@/utils/turnTimerUtil'
import type { CompactionItem } from './messageTurn'

const props = defineProps<{ item: CompactionItem }>()
const isRunning = computed(() => props.item.status === 'running')
const nowTick = useLiveTimer(() => isRunning.value)

// 实时与历史共用状态文案
const label = computed(() => {
  if (isRunning.value) return '正在压缩上下文…'
  if (props.item.status === 'success') return '上下文压缩完成'
  if (props.item.status === 'error') return '上下文压缩失败'
  return '上下文压缩已跳过'
})

const timerVisible = computed(() => isRunning.value || props.item.durationMs !== undefined)
const elapsedMs = computed(() => {
  if (!isRunning.value) return props.item.durationMs ?? 0
  return Math.max(0, nowTick.value - (props.item.startedAt ?? nowTick.value))
})
const timerText = computed(() => formatDuration(elapsedMs.value))
</script>

<style scoped>
.compaction-entry {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 22px;
  color: #797a85;
  --shimmer-base: #797a85;
  --shimmer-highlight: #aeb8d0;
  font-size: 14px;
  line-height: 1.5;
}
.compaction-orb {
  position: relative;
  z-index: 1;
  flex: none;
  width: 24px;
  height: 24px;
  overflow: hidden;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 28%, #f7f8ff 0%, #d9e1f8 26%, transparent 58%),
    radial-gradient(circle at 72% 76%, #667bae 0%, #8e9dcc 46%, #c0cbed 100%);
  animation: compaction-orb-bob 2.8s ease-in-out infinite;
}
.compaction-orb::before,
.compaction-orb::after {
  content: '';
  position: absolute;
  inset: 0;
  background-repeat: repeat-x;
  background-position: 0 -12px;
}
.compaction-orb::before {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 60'><path d='M0 20 C3.3 17.5 6.7 17.5 10 20 C13.3 22.5 16.7 22.5 20 20 L20 60 L0 60 Z' fill='rgba(40,63,119,0.28)'/></svg>");
  background-size: 24px 72px;
  animation: compaction-orb-swell 3.6s linear infinite;
}
.compaction-orb::after {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 60'><path d='M0 20 C3.3 17.5 6.7 17.5 10 20 C13.3 22.5 16.7 22.5 20 20' fill='none' stroke='rgba(255,255,255,0.62)' stroke-width='1.6'/></svg>");
  background-size: 24px 72px;
  animation: compaction-orb-crest 5.2s linear infinite;
}
.compaction-orb.is-running {
  animation-duration: 1.8s;
}
.compaction-orb.is-running::before {
  animation-duration: 2.2s;
}
.compaction-orb.is-running::after {
  animation-duration: 3s;
}
.compaction-timer {
  color: #9397a8;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
@keyframes compaction-orb-bob {
  0%,
  100% {
    transform: translateY(0.9px) scale(1.1, 0.9);
  }
  35% {
    transform: translateY(-0.9px) scale(0.91, 1.1);
  }
  68% {
    transform: translateY(0.3px) scale(1.04, 0.96);
  }
}
@keyframes compaction-orb-swell {
  to {
    background-position: -24px -12px;
  }
}
@keyframes compaction-orb-crest {
  0% {
    background-position: 0 -12px;
  }
  50% {
    background-position: 24px -15px;
  }
  100% {
    background-position: 48px -12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .compaction-orb,
  .compaction-orb::before,
  .compaction-orb::after {
    animation: none;
  }
}
</style>
